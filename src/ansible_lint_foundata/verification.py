# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify installed rules through Ansible Lint's command-line interface."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ruamel.yaml import YAML

from ansible_lint_foundata import RULE_IDS
from ansible_lint_foundata._probes import PROBES

CONFIG_NAMES = (
    ".ansible-lint",
    ".ansible-lint.yml",
    ".ansible-lint.yaml",
    ".config/ansible-lint.yml",
    ".config/ansible-lint.yaml",
)


def _strings(config: dict[str, object], key: str) -> list[str]:
    value = config.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings")
    return value


def _invoke(project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("ANSIBLE_LINT_IGNORE_FILE", None)
    env["ANSIBLE_LINT_SKIP_SCHEMA_UPDATE"] = "1"
    env["ANSIBLE_LOCAL_TEMP"] = str(project / ".ansible-tmp")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "ansiblelint",
            "--offline",
            "--nocolor",
            "--strict",
            "--project-dir",
            str(project),
            "--config-file",
            str(project / ".ansible-lint"),
            "--ignore-file",
            str(project / ".ansible-lint-ignore"),
            *arguments,
        ],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def verify(project: Path, config_file: Path | None = None) -> set[str]:
    """Return verified rule IDs, or raise when configured rules cannot be verified."""
    project = project.resolve(strict=True)
    if not project.is_dir():
        raise ValueError(f"Not a project directory: {project}")
    source = (
        project / config_file
        if config_file is not None
        else next(
            (project / name for name in CONFIG_NAMES if (project / name).is_file()),
            project / CONFIG_NAMES[0],
        )
    ).resolve(strict=True)
    yaml = YAML(typ="safe")
    config = yaml.load(source)
    if not isinstance(config, dict) or not all(isinstance(key, str) for key in config):
        raise ValueError(f"Expected a YAML mapping in {source}")
    expected = {
        rule for rule in _strings(config, "enable_list") if rule.startswith("foundata-")
    }
    if not expected:
        raise ValueError(f"No foundata rule IDs enabled in {source}")
    if unknown := expected - set(RULE_IDS):
        raise ValueError(f"Unknown foundata rules: {', '.join(sorted(unknown))}")
    if skipped := expected.intersection(_strings(config, "skip_list")):
        raise ValueError(
            f"Enabled rules also in skip_list: {', '.join(sorted(skipped))}"
        )

    # Keep custom rule paths valid after relocating the configuration. Only output
    # settings change: verification must not apply fixes or write project reports.
    if "rulesdir" in config:
        config["rulesdir"] = [
            str((source.parent / Path(os.path.expandvars(path)).expanduser()).resolve())
            for path in _strings(config, "rulesdir")
        ]
    config["write_list"] = []
    config.pop("sarif_file", None)
    config.pop("project_dir", None)

    with tempfile.TemporaryDirectory(prefix="foundata-lint-verify-") as temporary:
        probe = Path(temporary)
        yaml.dump(config, probe / ".ansible-lint")
        (probe / ".ansible-lint-ignore").touch()
        for name, content in PROBES.items():
            path = probe / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        yamllint = next(
            (
                project / name
                for name in (".yamllint", ".yamllint.yaml", ".yamllint.yml")
                if (project / name).is_file()
            ),
            None,
        )
        arguments = ("--yamllint-file", str(yamllint)) if yamllint else ()
        listing = _invoke(probe, *arguments, "--list-rules", "--format", "brief")
        if listing.returncode:
            raise ValueError(
                f"Rule discovery failed:\n{listing.stdout}\n{listing.stderr}"
            )
        available = {
            words[1]
            for line in listing.stdout.splitlines()
            if len(words := line.split()) >= 2 and words[0] == "-"
        }
        if missing := expected - available:
            raise ValueError(f"Rules not discovered: {', '.join(sorted(missing))}")
        result = _invoke(probe, *arguments, "--format", "json")
        if result.returncode != 2 or "Ignored exception" in result.stderr:
            raise ValueError(
                f"Rule probes must report violations (exit 2), got {result.returncode}:\n"
                f"{result.stdout}\n{result.stderr}"
            )
        matches = json.loads(result.stdout)
        if not isinstance(matches, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("check_name"), str)
            for item in matches
        ):
            raise ValueError("Ansible Lint returned malformed diagnostics")
        reported = {
            item["check_name"].split("[", 1)[0]
            for item in matches
            if not item.get("ignored", False)
        }
        if {"internal-error", "load-failure", "syntax-check", "schema"} & reported:
            raise ValueError(
                f"Rule probes could not be linted:\n{result.stdout}\n{result.stderr}"
            )
        if missing := expected - reported:
            raise ValueError(
                f"Rules did not report violations: {', '.join(sorted(missing))}. "
                "Check skip_list, tags, kinds and exclusions."
            )
    return expected
