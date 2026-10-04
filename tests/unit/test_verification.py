"""Failures must not look like successful rule verification."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from ansible_lint_foundata import verification
from ansible_lint_foundata.cli import main

RULE = "foundata-condition-list"


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (None, "Expected a YAML mapping"),
        ([], "Expected a YAML mapping"),
        ({1: "value"}, "Expected a YAML mapping"),
        ({}, "No foundata rule IDs"),
        ({"enable_list": ["yaml"]}, "No foundata rule IDs"),
        ({"enable_list": RULE}, "enable_list must be a list"),
        ({"enable_list": [1]}, "enable_list must be a list"),
        ({"enable_list": ["foundata-unknown"]}, "Unknown foundata rules"),
        ({"enable_list": [RULE], "skip_list": [RULE]}, "also in skip_list"),
        ({"enable_list": [RULE], "skip_list": RULE}, "skip_list must be a list"),
    ],
)
def test_invalid_configuration(tmp_path: Path, config: object, message: str) -> None:
    YAML().dump(config, tmp_path / ".ansible-lint")
    with pytest.raises(ValueError, match=message):
        verification.verify(tmp_path)


@pytest.mark.parametrize(
    ("status", "output", "stderr", "message"),
    [
        (0, "[]", "", "must report violations"),
        (3, "[]", "", "must report violations"),
        (2, '[{"check_name": "yaml"}]', "", "did not report violations"),
        (2, "{}", "", "malformed diagnostics"),
        (2, "[{}]", "", "malformed diagnostics"),
        (2, "not JSON", "", "Expecting value"),
        (
            2,
            json.dumps([{"check_name": RULE, "ignored": True}]),
            "",
            "did not report violations",
        ),
        (
            2,
            json.dumps([{"check_name": RULE}, {"check_name": "syntax-check[error]"}]),
            "",
            "could not be linted",
        ),
        (
            2,
            json.dumps([{"check_name": RULE}, {"check_name": "schema[tasks]"}]),
            "",
            "could not be linted",
        ),
        (
            2,
            json.dumps([{"check_name": RULE}]),
            "Ignored exception from custom rule",
            "must report violations",
        ),
    ],
)
def test_unsuccessful_probes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    output: str,
    stderr: str,
    message: str,
) -> None:
    YAML().dump({"enable_list": [RULE]}, tmp_path / ".ansible-lint")

    def invoke(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        if "--list-rules" in args:
            return subprocess.CompletedProcess([], 0, f"- {RULE} Description\n", "")
        return subprocess.CompletedProcess([], status, output, stderr)

    monkeypatch.setattr(verification, "_invoke", invoke)
    with pytest.raises(ValueError, match=message):
        verification.verify(tmp_path)


@pytest.mark.parametrize("status", [0, 4])
def test_unsuccessful_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    YAML().dump({"enable_list": [RULE]}, tmp_path / ".ansible-lint")

    def invoke(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        assert "--list-rules" in args
        return subprocess.CompletedProcess([], status, "- yaml YAML\n", "details")

    monkeypatch.setattr(verification, "_invoke", invoke)
    message = "not discovered" if status == 0 else "discovery failed"
    with pytest.raises(ValueError, match=message):
        verification.verify(tmp_path)


@pytest.mark.parametrize("name", verification.CONFIG_NAMES)
def test_relocation_preserves_policy_and_prevents_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    source = tmp_path / name
    source.parent.mkdir(exist_ok=True)
    config = {
        "enable_list": [RULE, "yaml"],
        "profile": "production",
        "exclude_paths": ["generated/"],
        "rulesdir": ["custom"],
        "write_list": ["all"],
        "sarif_file": str(tmp_path / "report.json"),
        "project_dir": str(tmp_path),
    }
    YAML().dump(config, source)
    (tmp_path / ".yamllint").write_text("extends: default\n", encoding="utf-8")
    original = source.read_bytes()
    directories = []

    def invoke(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        directories.append(project)
        assert project != tmp_path
        relocated = YAML(typ="safe").load(project / ".ansible-lint")
        assert relocated == {
            **{
                key: value
                for key, value in config.items()
                if key not in {"sarif_file", "project_dir"}
            },
            "write_list": [],
            "rulesdir": [str(source.parent / "custom")],
        }
        assert (project / ".ansible-lint-ignore").read_bytes() == b""
        assert args[:2] == ("--yamllint-file", str(tmp_path / ".yamllint"))
        if "--list-rules" in args:
            return subprocess.CompletedProcess([], 0, f"- {RULE} Description\n", "")
        assert (project / "tasks/main.yml").is_file()
        return subprocess.CompletedProcess(
            [], 2, json.dumps([{"check_name": RULE}]), ""
        )

    monkeypatch.setattr(verification, "_invoke", invoke)
    assert verification.verify(tmp_path) == {RULE}
    assert source.read_bytes() == original
    assert not (tmp_path / "report.json").exists()
    assert all(not directory.exists() for directory in directories)


def test_subprocess_uses_current_interpreter_and_empty_ignore_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANSIBLE_LINT_IGNORE_FILE", "/unexpected/ignore")
    monkeypatch.setenv("ANSIBLE_COLLECTIONS_PATH", "/expected/collections")
    calls = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert command[:3] == [sys.executable, "-m", "ansiblelint"]
        assert "--offline" in command
        assert "--fix" not in command
        assert command[command.index("--ignore-file") + 1] == str(
            tmp_path / ".ansible-lint-ignore"
        )
        env = kwargs["env"]
        assert isinstance(env, dict)
        assert "ANSIBLE_LINT_IGNORE_FILE" not in env
        assert env["ANSIBLE_COLLECTIONS_PATH"] == "/expected/collections"
        assert kwargs["cwd"] == tmp_path
        assert kwargs["timeout"] == 120
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("ansible_lint_foundata.verification.subprocess.run", run)
    verification._invoke(tmp_path, "--list-rules")
    assert len(calls) == 1


def test_cli_reports_errors_without_tracebacks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["verify", "--project-dir", str(tmp_path)]) == 1
    assert "error:" in capsys.readouterr().err
    (tmp_path / ".ansible-lint").write_text("enable_list: [\n", encoding="utf-8")
    assert main(["verify", "--project-dir", str(tmp_path)]) == 1
    assert "Traceback" not in capsys.readouterr().err
