"""Static handler imports are containers, not independently notifiable handlers."""

from pathlib import Path

import pytest

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("valid_topic", [False, True])
def test_static_handler_import_checks_the_imported_handlers_only(
    tmp_path: Path, valid_topic: bool
) -> None:
    configure(tmp_path, "foundata-handler-listen", profile="production")
    (tmp_path / "handlers").mkdir()
    topic = "restart example" if valid_topic else "Restart Example"
    (tmp_path / "handlers/main.yml").write_text(
        '- name: "Restart example"\n'
        '  ansible.builtin.debug:\n    msg: "Restart"\n'
        f'  listen:\n    - "{topic}"\n',
        encoding="utf-8",
    )
    (tmp_path / "playbook.yml").write_text(
        '---\n- name: "Example"\n  hosts: "localhost"\n'
        "  gather_facts: false\n"
        '  handlers:\n    - name: "Import handlers"\n'
        '      ansible.builtin.import_tasks: "handlers/main.yml"\n'
        "  tasks: []\n",
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", "playbook.yml"))
    custom = [
        item for item in matches if item["check_name"] == "foundata-handler-listen"
    ]
    assert len(custom) == (0 if valid_topic else 1)
    assert all(
        item["location"]["path"].endswith("handlers/main.yml") for item in custom
    )


def test_dynamic_include_itself_still_requires_a_topic(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-handler-listen")
    (tmp_path / "handlers").mkdir()
    (tmp_path / "tasks/restart.yml").write_text(
        '- name: "Restart example"\n  ansible.builtin.debug:\n    msg: "Restart"\n',
        encoding="utf-8",
    )
    (tmp_path / "handlers/main.yml").write_text(
        '- name: "Restart sequence"\n'
        '  ansible.builtin.include_tasks: "../tasks/restart.yml"\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", "handlers/main.yml"))
    assert len(matches) == 2
    assert all(
        item["location"]["path"].endswith("handlers/main.yml") for item in matches
    )
