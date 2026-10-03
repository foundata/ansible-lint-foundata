"""Static Jinja inspection without rendering or loading Ansible plugins."""

from __future__ import annotations

import ast
from collections.abc import Iterator

from jinja2 import Environment, TemplateSyntaxError, nodes

from ansible_lint_foundata.policy import template_names


def plugin_references(value: str, *, implicit: bool = False) -> list[tuple[str, int]]:
    """Find literal plugin names, including higher-order filter arguments."""
    if not implicit and not any(marker in value for marker in ("{{", "{%")):
        return []
    try:
        template = Environment().parse("{{ " + value + " }}" if implicit else value)
    except TemplateSyntaxError:
        return []
    return list(
        _plugin_references(
            template, template_names("{{ " + value + " }}" if implicit else value)
        )
    )


def _plugin_references(
    template: nodes.Template, external_names: set[str]
) -> Iterator[tuple[str, int]]:
    for node in template.find_all((nodes.Filter, nodes.Test)):
        yield node.name, node.lineno
        if isinstance(node, nodes.Filter):
            name = node.name.removeprefix("ansible.builtin.")
            position = {
                "map": 0,
                "select": 0,
                "reject": 0,
                "selectattr": 1,
                "rejectattr": 1,
            }.get(name)
            if position is not None and len(node.args) > position:
                argument = node.args[position]
                if isinstance(argument, nodes.Const) and isinstance(
                    argument.value, str
                ):
                    if argument.value not in {"==", "!=", ">", ">=", "<", "<="}:
                        yield argument.value, argument.lineno
    for call in template.find_all(nodes.Call):
        if (
            isinstance(call.node, nodes.Name)
            and call.node.name in external_names & {"lookup", "query", "q"}
            and call.args
            and isinstance(call.args[0], nodes.Const)
            and isinstance(call.args[0].value, str)
        ):
            yield call.args[0].value, call.lineno


def has_quote_filter(value: str) -> bool:
    """Identify shell quoting in a templated argv element."""
    return any(
        name in {"quote", "ansible.builtin.quote", "ansible.legacy.quote"}
        for name, _ in plugin_references(value)
    )


def template_environment(content: str) -> Environment:
    """Honor literal template delimiter headers without executing their values."""
    environment = Environment(optimized=False)
    if not content.startswith("#jinja2:"):
        return environment
    header = content.splitlines()[0].removeprefix("#jinja2:")
    try:
        expression = ast.parse("{" + header + "}", mode="eval").body
        if not isinstance(expression, ast.Dict):
            raise ValueError("Jinja environment header must be a mapping")
        options: dict[str, object] = {}
        for key, literal in zip(expression.keys, expression.values, strict=True):
            if not isinstance(key, ast.Name):
                raise ValueError("Jinja environment keys must be identifiers")
            options[key.id] = ast.literal_eval(literal)
    except (SyntaxError, ValueError) as error:
        raise ValueError("Invalid Jinja environment header") from error
    string_options = {
        "block_start_string",
        "block_end_string",
        "variable_start_string",
        "variable_end_string",
        "comment_start_string",
        "comment_end_string",
        "line_statement_prefix",
        "line_comment_prefix",
        "newline_sequence",
    }
    for name, value in options.items():
        if name in string_options and isinstance(value, str) and value:
            setattr(environment, name, value)
        elif name in {
            "trim_blocks",
            "lstrip_blocks",
            "keep_trailing_newline",
        } and isinstance(value, bool):
            setattr(environment, name, value)
        else:
            raise ValueError(f"Unsupported Jinja environment override: {name}")
    if (
        len(
            {
                environment.block_start_string,
                environment.variable_start_string,
                environment.comment_start_string,
            }
        )
        != 3
    ):
        raise ValueError("Jinja start delimiters must be distinct")
    if environment.newline_sequence not in {"\n", "\r", "\r\n"}:
        raise ValueError("Invalid Jinja newline sequence")
    return environment
