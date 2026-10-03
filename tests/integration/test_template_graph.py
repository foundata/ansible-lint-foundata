"""Exercise template interfaces at actual module call sites."""

from pathlib import Path

import pytest

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


def test_inherited_fragment_locals_and_required_task_bindings(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-template-inputs")
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "main.j2").write_text(
        "{% set value = tpl_value %}{% include 'part.j2' %}{{ tpl_optional | default('') }}",
        encoding="utf-8",
    )
    (templates / "part.j2").write_text("{{ value }}", encoding="utf-8")
    tasks = tmp_path / "tasks/main.yml"
    tasks.write_text(
        '---\n- name: "Missing binding"\n  ansible.builtin.template:\n    src: "main.j2"\n    dest: "/tmp/example"\n'
        '- name: "Explicit binding"\n  ansible.builtin.template:\n    src: "main.j2"\n    dest: "/tmp/example"\n  vars:\n    tpl_value: "Example"\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(tasks), str(templates)))
    assert [m["check_name"] for m in matches] == ["foundata-template-inputs[missing]"]


def test_dynamic_paths_stay_unresolved_and_delimiter_overrides_are_checked(
    tmp_path: Path,
) -> None:
    configure(tmp_path, "foundata-template-inputs")
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "main.j2").write_text(
        "[[ inventory_hostname ]] [[ tpl_value ]]", encoding="utf-8"
    )
    tasks = tmp_path / "tasks/main.yml"
    tasks.write_text(
        '---\n- name: "Dynamic source"\n  ansible.builtin.template:\n    src: "{{ selected_template }}"\n    dest: "/tmp/example"\n'
        '- name: "Custom delimiters"\n  ansible.builtin.template:\n    src: "main.j2"\n    dest: "/tmp/example"\n    variable_start_string: "[["\n    variable_end_string: "]]"\n  vars:\n    tpl_value: "Example"\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(tasks)))
    assert [m["check_name"] for m in matches] == ["foundata-template-inputs[external]"]
