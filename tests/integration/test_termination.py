# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check explicit orchestration scope and reusable-role contracts."""

from pathlib import Path

import pytest
from ansiblelint.file_utils import Lintable

from ansible_lint_foundata.source import role_directory
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


@pytest.mark.parametrize(
    "module", ["ansible.builtin.meta", "ansible.legacy.meta", "meta"]
)
@pytest.mark.parametrize(
    "parameters", ['"flush_handlers"', '\n    _raw_params: "flush_handlers"']
)
def test_role_flush_handlers_syntax(
    tmp_path: Path, module: str, parameters: str
) -> None:
    configure(tmp_path, "foundata-no-flush-handlers")
    target = tmp_path / "roles/example/tasks/main.yml"
    target.parent.mkdir(parents=True)
    target.write_text(
        f'---\n- name: "Flush handlers"\n  {module}: {parameters}\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(target)))
    assert [m["check_name"] for m in matches] == ["foundata-no-flush-handlers"]
    assert matches[0]["description"] == (
        "flush_handlers in a role runs every notified handler of the calling play. "
        "Run the action as a task instead; use a task-local noqa: "
        "foundata-no-flush-handlers for a reviewed exception."
    )
    assert matches[0]["location"]["positions"]["begin"]["line"] == 2


@pytest.mark.parametrize("include", ["include_tasks", "import_tasks"])
def test_role_flush_handlers_nested_included_and_handler_tasks(
    tmp_path: Path, include: str
) -> None:
    configure(tmp_path, "foundata-no-flush-handlers")
    role = tmp_path / "roles/example"
    tasks = role / "tasks/main.yml"
    tasks.parent.mkdir(parents=True)
    tasks.write_text(
        '---\n- name: "Nested flush"\n  block:\n'
        '    - name: "Flush handlers"\n      ansible.builtin.meta: "flush_handlers"\n'
        '- name: "Include tasks"\n'
        f'  ansible.builtin.{include}: "nested/flush.yml"\n'
        '- name: "Reviewed exception" # noqa: foundata-no-flush-handlers\n'
        '  ansible.builtin.meta: "flush_handlers"\n',
        encoding="utf-8",
    )
    included = role / "tasks/nested/flush.yml"
    included.parent.mkdir()
    handlers = role / "handlers/main.yml"
    handlers.parent.mkdir()
    for target in (included, handlers):
        target.write_text(
            '---\n- name: "Flush handlers"\n  ansible.builtin.meta: "flush_handlers"\n',
            encoding="utf-8",
        )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(tasks), str(handlers)))
    assert len(matches) == 3
    assert all(m["check_name"] == "foundata-no-flush-handlers" for m in matches)
    assert {
        (m["location"]["path"], m["location"]["positions"]["begin"]["line"])
        for m in matches
    } == {
        (str(tasks.relative_to(tmp_path)), 4),
        (str(included.relative_to(tmp_path)), 2),
        (str(handlers.relative_to(tmp_path)), 2),
    }


def test_flush_handlers_scope_excludes_playbooks_and_molecule(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-no-flush-handlers")
    role = tmp_path / "roles/example"
    (role / "tasks").mkdir(parents=True)
    filenames = (
        "tasks/main.yml",
        "extensions/molecule/default/tasks/main.yml",
        "extensions/molecule/default/roles/example/tasks/main.yml",
        "roles/example/molecule/default/tasks/main.yml",
    )
    for filename in filenames:
        target = tmp_path / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            '---\n- name: "Flush handlers"\n  ansible.builtin.meta: "flush_handlers"\n',
            encoding="utf-8",
        )
    assert role_directory(Lintable(tmp_path / filenames[-1])) == role
    playbooks = ("playbook.yml", "roles/example/molecule/default/verify.yml")
    for filename in playbooks:
        (tmp_path / filename).write_text(
            '---\n- name: "Verify"\n  hosts: "localhost"\n  gather_facts: false\n'
            '  tasks:\n    - name: "Flush handlers"\n'
            '      ansible.builtin.meta: "flush_handlers"\n'
            '  handlers:\n    - name: "Flush from handler"\n'
            '      ansible.builtin.meta: "flush_handlers"\n',
            encoding="utf-8",
        )
    assert diagnostics(run_lint(tmp_path, "-f", "json", *filenames, *playbooks)) == []


def test_role_flush_handlers_ignores_other_operations(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-no-flush-handlers")
    target = tmp_path / "roles/example/tasks/main.yml"
    target.parent.mkdir(parents=True)
    target.write_text(
        "---\n"
        + "".join(
            f'- name: "Other operation"\n  ansible.builtin.meta: "{operation}"\n'
            for operation in (
                "end_play",
                "end_host",
                "end_role",
                "noop",
                "refresh_inventory",
            )
        )
        + '- name: "Other module"\n  ansible.builtin.debug:\n    msg: "flush_handlers"\n',
        encoding="utf-8",
    )
    assert diagnostics(run_lint(tmp_path, "-f", "json", str(target))) == []


@pytest.mark.parametrize("enabled", [False, True])
def test_flush_handlers_is_opt_in_under_production(
    tmp_path: Path, enabled: bool
) -> None:
    configure(
        tmp_path,
        *(["foundata-no-flush-handlers"] if enabled else []),
        profile="production",
    )
    target = tmp_path / "roles/example/tasks/main.yml"
    target.parent.mkdir(parents=True)
    target.write_text(
        '---\n- name: "Flush handlers"\n  ansible.builtin.meta: "flush_handlers"\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(target)))
    assert [m["check_name"] for m in matches] == (
        ["foundata-no-flush-handlers"] if enabled else []
    )


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
