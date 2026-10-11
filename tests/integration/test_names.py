# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Name checks distinguish template locals from Ansible loop inputs."""

import json
from pathlib import Path

import pytest

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Install {% for item in ['fixed'] %}{{ item }}{% endfor %}", False),
        ("Install {% set item = 'fixed' %}{{ item }}", False),
        ("Install {{ vars['item'] }}", True),
        ("Install {{ lookup('ansible.builtin.vars', 'item') }}", True),
        ("Install {{ ansible_loop.index }}", True),
        ("Install {{ item | ansible.builtin.to_nice_json }}", True),
    ],
)
def test_loop_name_references(tmp_path: Path, name: str, expected: bool) -> None:
    configure(tmp_path, "foundata-task-name")
    (tmp_path / "tasks/main.yml").write_text(
        f"---\n- name: {json.dumps(name)}\n"
        '  ansible.builtin.debug:\n    msg: "Example"\n'
        "  loop: []\n  loop_control:\n    extended: true\n",
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", "tasks/main.yml"))
    assert bool(matches) is expected
    assert all(item["check_name"] == "foundata-task-name" for item in matches)
