# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise retry conditions and conservative boolean diagnostics."""

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


def test_until_fix_preserves_expression_and_is_stable(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-condition-list", "foundata-condition-bool")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        '---\n- name: "Wait"\n  ansible.builtin.debug:\n    msg: "Wait"\n'
        "  until: result is ansible.builtin.succeeded # Preserve this expression\n",
        encoding="utf-8",
    )
    assert [
        m["check_name"]
        for m in diagnostics(run_lint(tmp_path, "-f", "json", str(target)))
    ] == ["foundata-condition-list"]
    run_lint(tmp_path, "--fix=foundata-condition-list", str(target))
    first = target.read_bytes()
    assert YAML(typ="safe").load(first)[0]["until"] == [
        "result is ansible.builtin.succeeded"
    ]
    assert b"# Preserve this expression" in first
    assert (
        run_lint(tmp_path, "--fix=foundata-condition-list", str(target)).returncode == 0
    )
    assert target.read_bytes() == first


def test_all_condition_contexts_and_no_inference(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-condition-bool")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        '---\n- name: "Known nonboolean"\n  ansible.builtin.debug:\n    msg: "Example"\n'
        '  when: [1]\n  changed_when: ["[]"]\n  failed_when: ["\'error\'"]\n  until: ["none"]\n'
        '- name: "Unknown types"\n  ansible.builtin.debug:\n    msg: "Example"\n'
        '  when: [enabled]\n  changed_when: ["result.rc != 0"]\n'
        '  failed_when: ["result is ansible.builtin.failed"]\n  until: [true]\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(target)))
    assert len(matches) == 4
    assert {m["check_name"] for m in matches} == {"foundata-condition-bool"}
    before = target.read_bytes()
    assert run_lint(tmp_path, "--fix=all", str(target)).returncode == 2
    assert YAML(typ="safe").load(target.read_bytes()) == YAML(typ="safe").load(before)


def test_assert_checks_boolean_results_in_alternate_argument_syntax(
    tmp_path: Path,
) -> None:
    configure(tmp_path, "foundata-condition-bool")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        """---
- name: "Assertions"
  action:
    module: ansible.builtin.assert
    that:
      - "'ready'"
      - enabled
      - result is defined
""",
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(target)))
    assert [m["check_name"] for m in matches] == ["foundata-condition-bool"]
    assert "assert.that" in matches[0]["description"]
