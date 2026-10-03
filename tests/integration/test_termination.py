"""Check explicit orchestration scope and reusable-role contracts."""

from pathlib import Path

import pytest

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


def test_orchestration_explanations_are_comments_not_scalar_text(
    tmp_path: Path,
) -> None:
    configure(tmp_path, "foundata-no-end-play")
    target = tmp_path / "playbook.yml"
    target.write_text(
        '---\n- name: "Orchestrate"\n  hosts: "localhost"\n  gather_facts: false\n  tasks:\n'
        "    # Stop this play for all hosts when deployment has been cancelled.\n"
        '    - name: "Cancel deployment"\n      ansible.builtin.meta: "end_play"\n'
        '    - name: "Missing explanation # not a comment"\n      ansible.builtin.meta: "end_host"\n',
        encoding="utf-8",
    )
    standalone = tmp_path / "tasks/main.yml"
    standalone.write_text(
        '---\n- name: "Role-only operation"\n  ansible.builtin.meta: "end_role"\n',
        encoding="utf-8",
    )
    matches = diagnostics(
        run_lint(tmp_path, "-f", "json", str(target), str(standalone))
    )
    assert len(matches) == 2
    assert all(m["check_name"] == "foundata-no-end-play" for m in matches)


def test_role_termination_and_local_contract_exception(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-no-end-play")
    role = tmp_path / "roles/example"
    tasks = role / "tasks/main.yml"
    tasks.parent.mkdir(parents=True)
    tasks.write_text(
        '---\n- name: "Stop host"\n  ansible.builtin.meta: "end_host"\n'
        "# This role is a deployment cancellation guard; its caller contract ends the play.\n"
        '- name: "Cancel deployment" # noqa: foundata-no-end-play\n  ansible.builtin.meta: "end_play"\n'
        '- name: "Finish this role"\n  ansible.builtin.meta: "end_role"\n',
        encoding="utf-8",
    )
    handlers = role / "handlers/main.yml"
    handlers.parent.mkdir()
    handlers.write_text(
        '---\n- name: "Invalid handler exit"\n  ansible.builtin.meta: "end_role"\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(tasks), str(handlers)))
    assert len(matches) == 2
    assert all(m["check_name"] == "foundata-no-end-play" for m in matches)
