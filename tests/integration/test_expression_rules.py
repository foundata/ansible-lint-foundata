# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed diagnostics for the bounded expression and template rules."""

from pathlib import Path

import pytest

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


def test_task_plugin_checks_include_implicit_conditions(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-jinja-fqcn")
    (tmp_path / "tasks/main.yml").write_text(
        """---
- name: "Example"
  ansible.builtin.assert:
    that:
      - example is defined
  vars:
    example: "{{ lookup('env', 'HOME') | default('') }}"
  when:
    - other is ansible.builtin.defined
""",
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", "tasks/main.yml"))
    assert len(matches) == 3
    assert all(item["check_name"] == "foundata-jinja-fqcn" for item in matches)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("{{ inventory_hostname }}\n", "foundata-template-inputs"),
        ("{{ tpl_content | ansible.builtin.to_nice_json }}\n", None),
        ("{% for item in tpl_items %}{{ item }}{% endfor %}\n", None),
        (
            "{% macro render(item) %}{{ item }}{% endmacro %}{{ render(tpl_item) }}\n",
            None,
        ),
        (
            "#jinja2:variable_start_string:'[%', variable_end_string:'%]'\n[% inventory_hostname %]\n",
            "foundata-template-inputs",
        ),
        (
            "#jinja2:block_start_string:'<%', block_end_string:'%>'\n<% for item in tpl_items %>{{ item }}<% endfor %>\n",
            None,
        ),
        (
            "#jinja2:variable_start_string:'{%'\n{% inventory_hostname }}\n",
            "foundata-template-inputs[unresolved]",
        ),
        ("{{ invalid", "foundata-template-inputs[unresolved]"),
        (
            "{% block duplicate %}{% endblock %}{% block duplicate %}{% endblock %}",
            "foundata-template-inputs[unresolved]",
        ),
        (
            "{# noqa: foundata-template-inputs -- External application template #}\n{{ application }}\n",
            None,
        ),
    ],
)
def test_template_input_interface(
    tmp_path: Path, content: str, expected: str | None
) -> None:
    configure(tmp_path, "foundata-template-inputs")
    target = tmp_path / "example.j2"
    target.write_text(content, encoding="utf-8")
    matches = diagnostics(run_lint(tmp_path, "--format", "json", str(target)))
    assert [item["check_name"] for item in matches] == ([expected] if expected else [])


@pytest.mark.parametrize("quoted", [True, False])
def test_argv_filters_are_checked_without_changing_arguments(
    tmp_path: Path, quoted: bool
) -> None:
    configure(tmp_path, "foundata-command-argv")
    argument = "{{ value | ansible.builtin.quote }}" if quoted else "{{ value }}"
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        '---\n- name: "Example"\n  ansible.legacy.command:\n'
        f'    argv: ["/usr/bin/example", "{argument}"]\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", str(target)))
    assert bool(matches) is quoted
    assert all(item["check_name"] == "foundata-command-argv" for item in matches)
