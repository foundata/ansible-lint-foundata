# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise optional style rules through installed discovery and stock fixes."""

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


def test_style_rules_are_read_only_and_respect_context(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-string-quotes", "foundata-parameter-order")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        """---
- name: "Inspect"
  ansible.builtin.debug:
    verbosity: 1
    msg: plain
  when: [enabled]
  register: result
- name: "Expression"
  ansible.builtin.debug:
    var: result.value
- name: "Assert"
  ansible.builtin.assert:
    that: [result is defined]
- name: "Mapping action"
  action:
    module: ansible.builtin.debug
    var: result.value
""",
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(target)))
    assert sorted(m["check_name"] for m in matches) == [
        "foundata-parameter-order",
        "foundata-string-quotes",
    ]
    before = YAML(typ="safe").load(target.read_bytes())
    run_lint(tmp_path, "--fix=all", str(target))
    first = target.read_bytes()
    assert YAML(typ="safe").load(first) == before
    run_lint(tmp_path, "--fix=all", str(target))
    assert target.read_bytes() == first


def test_style_suppression_is_local(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-string-quotes")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        """---
- name: "Suppressed" # noqa: foundata-string-quotes
  ansible.builtin.debug:
    msg: plain
- name: "Reported"
  ansible.builtin.debug:
    msg: plain
""",
        encoding="utf-8",
    )
    assert len(diagnostics(run_lint(tmp_path, "-f", "json", str(target)))) == 1
