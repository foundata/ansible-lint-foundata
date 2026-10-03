"""Verify scoped handler names and adjacent migration comments in the CLI."""

from pathlib import Path

import pytest

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


def test_namespace_and_aliases_are_never_renamed(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-handler-listen")
    target = tmp_path / "roles/nginx/handlers/main.yml"
    target.parent.mkdir(parents=True)
    target.write_text(
        '---\n- name: "Restart"\n  ansible.builtin.debug:\n    msg: "Restart"\n  listen:\n'
        '    - "nginx_restart_nginx"\n'
        '    - "Restart Nginx" # Migration alias; remove in 3.0.0.\n'
        '    # Shared broadcast for web services.\n    - "web_restart_services"\n'
        '- name: "Missing object"\n  ansible.builtin.debug:\n    msg: "Restart"\n  listen:\n    - "nginx_restart"\n'
        '- name: "Missing removal version"\n  ansible.builtin.debug:\n    msg: "Restart"\n  listen:\n    - "Old Topic" # Migration alias\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "-f", "json", str(target)))
    assert len(matches) == 2
    assert all(m["check_name"] == "foundata-handler-listen" for m in matches)
    before = target.read_bytes()
    run_lint(tmp_path, "--fix=foundata-handler-listen", str(target))
    assert target.read_bytes() == before
