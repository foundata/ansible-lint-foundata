# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise verification through the installed CLI."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ansible_lint_foundata import RULE_IDS

pytestmark = pytest.mark.integration


def run_verify(project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("ANSIBLE_", "ANSIBLELINT_"))
    }
    env["ANSIBLE_LINT_NODEPS"] = "1"
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "ansible_lint_foundata.cli",
            "verify",
            "--project-dir",
            str(project),
            *arguments,
        ],
        cwd=project.parent,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )


@pytest.mark.parametrize("all_rules", [False, True])
def test_verifies_adopted_rules_without_changing_project(
    tmp_path: Path, all_rules: bool
) -> None:
    source = Path(__file__).resolve().parents[2] / "examples/consumer"
    for name in (".ansible-lint", ".yamllint"):
        shutil.copyfile(source / name, tmp_path / name)
    if all_rules:
        (tmp_path / ".ansible-lint").write_text(
            json.dumps({"profile": "production", "enable_list": RULE_IDS}),
            encoding="utf-8",
        )
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks/main.yml").write_text("Not valid YAML: [", encoding="utf-8")
    before = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    result = run_verify(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"{18 if all_rules else 16} foundata rules" in result.stdout
    assert before == {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }


def test_explicit_config_and_subset(tmp_path: Path) -> None:
    (tmp_path / "lint.yml").write_text(
        json.dumps({"enable_list": ["foundata-condition-list"]}), encoding="utf-8"
    )
    result = run_verify(tmp_path, "--config-file", "lint.yml")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 foundata rules" in result.stdout


@pytest.mark.parametrize(
    "settings",
    [
        {"skip_list": ["foundata-condition-list"]},
        {"skip_list": ["opt-in"]},
        {"tags": ["yaml"]},
        {"exclude_paths": ["tasks/", "handlers/", "templates/", "playbook.yml"]},
    ],
)
def test_configuration_preventing_execution_fails(
    tmp_path: Path, settings: dict[str, object]
) -> None:
    (tmp_path / ".ansible-lint").write_text(
        json.dumps({"enable_list": ["foundata-condition-list"], **settings}),
        encoding="utf-8",
    )
    result = run_verify(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "error:" in result.stderr


def test_configured_fixes_are_not_applied(tmp_path: Path) -> None:
    (tmp_path / ".ansible-lint").write_text(
        json.dumps(
            {
                "enable_list": ["foundata-condition-list"],
                "write_list": ["all"],
                "sarif_file": str(tmp_path / "report.json"),
            }
        ),
        encoding="utf-8",
    )
    result = run_verify(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "report.json").exists()
