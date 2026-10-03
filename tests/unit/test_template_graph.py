"""Check template composition, contexts and conservative input requirements."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ansible_lint_foundata.expressions import template_environment
from ansible_lint_foundata.template_graph import TemplateGraph


def test_include_locals_and_context_free_macros(tmp_path: Path) -> None:
    root = tmp_path / "main.j2"
    root.write_text(
        "{% import 'macros.j2' as helpers %}{% for item in tpl_items %}{% include 'part.j2' %}{% endfor %}",
        encoding="utf-8",
    )
    (tmp_path / "part.j2").write_text(
        "{{ helpers.show(item) }} {{ tpl_optional | default('') }}", encoding="utf-8"
    )
    (tmp_path / "macros.j2").write_text(
        "{% macro show(value) %}{{ value }}{% endmacro %}", encoding="utf-8"
    )
    result = TemplateGraph(tmp_path).analyze(
        root, template_environment(root.read_text())
    )
    assert result.external == {}
    assert result.required == {"tpl_items"}
    assert result.unresolved == set()
    runtime = Environment(loader=FileSystemLoader(tmp_path), undefined=StrictUndefined)
    assert runtime.get_template("main.j2").render(tpl_items=["example"]) == "example "


def test_context_free_import_does_not_inherit_caller_locals(tmp_path: Path) -> None:
    root = tmp_path / "main.j2"
    root.write_text(
        "{% set local = 1 %}{% import 'macros.j2' as helpers %}", encoding="utf-8"
    )
    child = tmp_path / "macros.j2"
    child.write_text(
        "{% macro show() %}{{ local }} {{ tpl_value }}{% endmacro %}", encoding="utf-8"
    )
    result = TemplateGraph(tmp_path).analyze(
        root, template_environment(root.read_text())
    )
    assert result.external == {child: {"local", "tpl_value"}}


def test_static_and_conditional_requirements_and_cycles(tmp_path: Path) -> None:
    root = tmp_path / "main.j2"
    root.write_text(
        "{{ tpl_required }}{% if tpl_optional is defined %}{{ tpl_optional }}{% endif %}{% include 'part.j2' %}",
        encoding="utf-8",
    )
    (tmp_path / "part.j2").write_text(
        "{{ tpl_child }}{% include 'main.j2' %}", encoding="utf-8"
    )
    result = TemplateGraph(tmp_path).analyze(
        root, template_environment(root.read_text())
    )
    assert result.required == {"tpl_required", "tpl_child"}
    assert result.unresolved == {str(root)}


def test_delimiters_are_shared_by_fragments_and_root_header_wins(
    tmp_path: Path,
) -> None:
    root = tmp_path / "main.j2"
    root.write_text(
        "#jinja2:variable_start_string:'[[', variable_end_string:']]'\n{% include 'part.j2' %}",
        encoding="utf-8",
    )
    (tmp_path / "part.j2").write_text("[[ tpl_value ]]", encoding="utf-8")
    env = template_environment(
        root.read_text(), {"variable_start_string": "[%", "variable_end_string": "%]"}
    )
    result = TemplateGraph(tmp_path).analyze(root, env)
    assert result.required == {"tpl_value"}


def test_conditional_expression_branches_are_not_mandatory_inputs(
    tmp_path: Path,
) -> None:
    root = tmp_path / "main.j2"
    root.write_text(
        "{{ tpl_a if tpl_switch else tpl_b }} {{ tpl_enabled and tpl_other }}",
        encoding="utf-8",
    )
    result = TemplateGraph(tmp_path).analyze(
        root, template_environment(root.read_text())
    )
    assert result.required == {"tpl_switch", "tpl_enabled"}


def test_inheritance_shares_root_assignments_with_overridden_blocks(
    tmp_path: Path,
) -> None:
    root = tmp_path / "main.j2"
    root.write_text(
        "{% extends 'base.j2' %}{% set child_value = tpl_value %}{% block content %}{{ base_value }} {{ child_value }}{% endblock %}",
        encoding="utf-8",
    )
    (tmp_path / "base.j2").write_text(
        "{% set base_value = 'base' %}{% block content %}{{ child_value }}{% endblock %}",
        encoding="utf-8",
    )
    result = TemplateGraph(tmp_path).analyze(
        root, template_environment(root.read_text())
    )
    assert result.external == {}
    assert result.required == {"tpl_value"}
    runtime = Environment(loader=FileSystemLoader(tmp_path), undefined=StrictUndefined)
    assert runtime.get_template("main.j2").render(tpl_value="child") == "base child"
