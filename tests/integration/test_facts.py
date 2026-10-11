# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check fact aliases in explicit and implicit expression contexts."""

from pathlib import Path

import pytest

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


def test_task_and_variable_contexts(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-fact-vars")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        '---\n- name: "Debug implicit fact"\n  ansible.builtin.debug:\n    var: ansible_distribution\n'
        '- name: "Retry on fact"\n  ansible.builtin.debug:\n    msg: "ansible_distribution"\n  until: ["ansible_os_family == \'RedHat\'"]\n'
        '- name: "Preserve magic and connection variables"\n  ansible.builtin.debug:\n    msg: "{{ ansible_host }} {{ ansible_version }} {{ ansible_facts[\'distribution\'] }}"\n',
        encoding="utf-8",
    )
    variables = tmp_path / "vars/main.yml"
    variables.parent.mkdir()
    variables.write_text(
        '---\nplatform: "{{ ansible_distribution }}"\n', encoding="utf-8"
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(target), str(variables)))
    assert len(matches) == 3
    assert all(m["check_name"] == "foundata-fact-vars" for m in matches)
