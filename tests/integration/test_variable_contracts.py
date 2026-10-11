# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check source definitions without pretending to evaluate variable precedence."""

from pathlib import Path

import pytest

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


def test_permission_comments_belong_to_literal_definitions(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-file-mode")
    role = tmp_path / "roles/example"
    (role / "tasks").mkdir(parents=True)
    (role / "defaults").mkdir()
    defaults = role / "defaults/main.yml"
    defaults.write_text(
        '---\nexample_mode: "u=rw,g=r,o=" # 0644\nexample_options:\n  mode: "u=rw,g=r,o=r" # 0644\n',
        encoding="utf-8",
    )
    target = role / "tasks/main.yml"
    target.write_text(
        '---\n- name: "Wrong definition comment"\n  ansible.builtin.file:\n    path: "/tmp/example"\n    mode: "{{ example_mode }}" # 0640\n'
        '- name: "Correct mapping definition"\n  ansible.builtin.file:\n    path: "/tmp/example"\n    mode: "{{ example_options[\'mode\'] }}"\n'
        '- name: "Unknown runtime mode"\n  ansible.builtin.file:\n    path: "/tmp/example"\n    mode: "{{ runtime_mode }}"\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(target)))
    assert len(matches) == 1
    assert "defaults/main.yml:2" in matches[0]["description"]
    assert "0640" in matches[0]["description"]
    defaults.write_text(
        defaults.read_text().replace('g=r,o=" # 0644', 'g=r,o=" # 0640'),
        encoding="utf-8",
    )
    assert diagnostics(run_lint(tmp_path, "-f", "json", str(target))) == []


def test_set_fact_distinguishes_declared_inputs_from_computed_state(
    tmp_path: Path,
) -> None:
    configure(tmp_path, "foundata-set-fact")
    role = tmp_path / "roles/example"
    for folder in ("tasks", "defaults", "meta"):
        (role / folder).mkdir(parents=True)
    (role / "defaults/main.yml").write_text(
        "---\nexample_enabled: false\n", encoding="utf-8"
    )
    (role / "meta/argument_specs.yml").write_text(
        '---\nargument_specs:\n  main:\n    options:\n      example_config:\n        type: "dict"\n',
        encoding="utf-8",
    )
    target = role / "tasks/main.yml"
    target.write_text(
        '---\n- name: "Overwrite inputs"\n  ansible.builtin.set_fact:\n    example_enabled: true\n    example_config: {}\n'
        '- name: "Compute state"\n  ansible.builtin.set_fact:\n    __example_enabled: true\n    __example_config: {}\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(target)))
    assert len(matches) == 2
    assert all(m["check_name"] == "foundata-set-fact" for m in matches)
