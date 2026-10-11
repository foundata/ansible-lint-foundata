# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The extension constrains only keys stock key-order leaves unordered."""

from pathlib import Path

import pytest
from ansiblelint.constants import RC
from ruamel.yaml import YAML

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


def test_stock_only_ordering_violation_is_not_duplicated(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-task-order", profile="production")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        '---\n- check_mode: false\n  name: "Example"\n'
        '  ansible.builtin.debug:\n    msg: "Example"\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", str(target)))
    assert [item["check_name"] for item in matches] == ["key-order[task]"]
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == RC.FIXED_VIOLATIONS, result.stdout + result.stderr
    assert diagnostics(run_lint(tmp_path, "--format", "json", str(target))) == []


def test_stock_fix_does_not_hide_or_fight_the_extension(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-task-order", profile="production")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        '---\n- register: result\n  name: "Example"\n'
        '  ansible.builtin.debug:\n    msg: "Example"\n'
        "  when:\n    - true\n",
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", str(target)))
    assert {item["check_name"] for item in matches} == {
        "key-order[task]",
        "foundata-task-order",
    }
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 2, result.stdout + result.stderr
    first = target.read_bytes()
    assert list(YAML(typ="safe").load(first)[0]) == [
        "name",
        "register",
        "ansible.builtin.debug",
        "when",
    ]
    matches = diagnostics(run_lint(tmp_path, "--format", "json", str(target)))
    assert [item["check_name"] for item in matches] == ["foundata-task-order"]
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 2, result.stdout + result.stderr
    assert target.read_bytes() == first
