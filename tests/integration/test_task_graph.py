"""Protect closed-play resolution and caller-dependent include contexts."""

from pathlib import Path

import pytest

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


def test_notifications_are_play_scoped_and_dynamic_edges_stay_open(
    tmp_path: Path,
) -> None:
    configure(tmp_path, "foundata-notify")
    target = tmp_path / "playbook.yml"
    target.write_text(
        """---
- name: "Closed play"
  hosts: "localhost"
  tasks:
    - name: "Trigger missing"
      ansible.builtin.debug:
        msg: "Example"
      notify: "missing_topic"
    - name: "Trigger by name"
      ansible.builtin.debug:
        msg: "Example"
      notify: "Restart service"
    - name: "Trigger by topic"
      ansible.builtin.debug:
        msg: "Example"
      notify: "restart_service"
  handlers:
    - name: "Restart service"
      ansible.builtin.debug:
        msg: "Restart"
      listen: "restart_service"
- name: "Separate play"
  hosts: "localhost"
  tasks:
    - name: "No handler in this play"
      ansible.builtin.debug:
        msg: "Example"
      notify: "restart_service"
- name: "Open play"
  hosts: "localhost"
  tasks:
    - name: "Load runtime handlers"
      ansible.builtin.include_role:
        name: "{{ selected_role }}"
    - name: "External target"
      ansible.builtin.debug:
        msg: "Example"
      notify: "external_topic"
""",
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(target)))
    assert len(matches) == 3
    assert all(m["check_name"] == "foundata-notify" for m in matches)


def test_nested_imported_handlers_and_external_role_topics(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-notify")
    role = tmp_path / "roles/example"
    (role / "tasks").mkdir(parents=True)
    (role / "handlers").mkdir()
    tasks = role / "tasks/main.yml"
    tasks.write_text(
        '---\n- name: "Notify"\n  ansible.builtin.debug:\n    msg: "Example"\n  notify: ["Restart", "external_topic", "example_restart_service"]\n',
        encoding="utf-8",
    )
    (role / "handlers/main.yml").write_text(
        '---\n- name: "Import handlers"\n  ansible.builtin.import_tasks: "extra.yml"\n',
        encoding="utf-8",
    )
    (role / "handlers/extra.yml").write_text(
        '---\n- name: "Restart"\n  ansible.builtin.debug:\n    msg: "Restart"\n  listen: "example_restart_service"\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(tasks)))
    assert len(matches) == 1
    assert "handler name" in matches[0]["description"]


def test_loop_collisions_follow_each_parent_and_honor_suppressions(
    tmp_path: Path,
) -> None:
    configure(tmp_path, "foundata-loop-collision")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        """---
- name: "Safe parent"
  ansible.builtin.include_tasks: "child.yml"
  loop: [1]
  loop_control:
    loop_var: outer
- name: "Colliding parent"
  ansible.builtin.include_tasks: "child.yml"
  loop: [1]
  loop_control:
    loop_var: inner
- name: "Dynamic include"
  ansible.builtin.include_tasks: "{{ selected_file }}"
  loop: [1]
""",
        encoding="utf-8",
    )
    child = tmp_path / "tasks/child.yml"
    child.write_text(
        '---\n- name: "Inner loop"\n  ansible.builtin.debug:\n    msg: "Example"\n  loop: [2]\n  loop_control:\n    loop_var: inner\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(target)))
    assert len(matches) == 1
    assert "inner" in matches[0]["description"]
    child.write_text(
        child.read_text().replace(
            'name: "Inner loop"', 'name: "Inner loop" # noqa: foundata-loop-collision'
        ),
        encoding="utf-8",
    )
    assert diagnostics(run_lint(tmp_path, "-f", "json", str(target))) == []
