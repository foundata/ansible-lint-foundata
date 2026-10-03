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


@pytest.mark.parametrize("directory", ["tasks", "handlers"])
def test_dynamic_include_itself_still_requires_a_topic(
    tmp_path: Path, directory: str
) -> None:
    configure(tmp_path, "foundata-handler-listen")
    (tmp_path / "handlers").mkdir()
    (tmp_path / directory / "restart.yml").write_text(
        '- name: "Restart example"\n  ansible.builtin.debug:\n    msg: "Restart"\n',
        encoding="utf-8",
    )
    (tmp_path / "handlers/main.yml").write_text(
        '- name: "Restart sequence"\n'
        f'  ansible.builtin.include_tasks: "../{directory}/restart.yml"\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", "handlers/main.yml"))
    assert len(matches) == 2
    assert all(
        item["location"]["path"].endswith("handlers/main.yml") for item in matches
    )


@pytest.mark.parametrize("also_static", [False, True])
@pytest.mark.parametrize("nested", [False, True])
def test_inline_dynamic_handler_body_and_static_import_contexts(
    tmp_path: Path,
    also_static: bool,
    nested: bool,
) -> None:
    configure(tmp_path, "foundata-handler-listen", profile="production")
    (tmp_path / "handlers").mkdir()
    (tmp_path / "handlers/restart.yml").write_text(
        '---\n- name: "Restart example"\n'
        '  ansible.builtin.debug:\n    msg: "Restart"\n',
        encoding="utf-8",
    )
    if nested:
        (tmp_path / "handlers/sequence.yml").write_text(
            '---\n- name: "Import sequence"\n'
            '  ansible.builtin.import_tasks: "restart.yml"\n',
            encoding="utf-8",
        )
    source = "handlers/sequence.yml" if nested else "handlers/restart.yml"
    static_import = (
        '    - name: "Import standalone handlers"\n'
        f'      ansible.builtin.import_tasks: "{source}"\n'
        if also_static
        else ""
    )
    (tmp_path / "playbook.yml").write_text(
        '---\n- name: "Example"\n  hosts: "localhost"\n'
        "  gather_facts: false\n  tasks: []\n"
        '  handlers:\n    - name: "Restart sequence"\n'
        f'      ansible.builtin.include_tasks: "{source}"\n'
        '      listen:\n        - "restart example"\n' + static_import,
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", "playbook.yml"))
    assert len(matches) == (2 if also_static else 0)
    assert all(
        item["location"]["path"].endswith("handlers/restart.yml") for item in matches
    )
