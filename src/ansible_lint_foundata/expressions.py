# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static Jinja inspection without rendering or loading Ansible plugins."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from typing import TYPE_CHECKING

from jinja2 import Environment, TemplateSyntaxError, nodes

from ansible_lint_foundata.policy import (
    CONDITION_KEYS,
    builtin_module_name,
    template_names,
)

if TYPE_CHECKING:
    from ansiblelint.utils import Task


def strings(value: object, seen: set[int] | None = None) -> Iterator[str]:
    """Walk YAML strings without following recursive aliases indefinitely."""
    seen = set() if seen is None else seen
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict) and id(value) not in seen:
        seen.add(id(value))
        for key, child in value.items():
            yield from strings(key, seen)
            yield from strings(child, seen)
    elif isinstance(value, list) and id(value) not in seen:
        seen.add(id(value))
        for child in value:
            yield from strings(child, seen)


def task_expression_inputs(task: Task) -> Iterator[tuple[str, bool]]:
    """Separate ordinary task templates from implicit expression parameters."""
    for key, value in task.raw_task.items():
        if key.startswith("__") or key in {"block", "rescue", "always"}:
            continue
        for text in strings(value):
            yield text, key in CONDITION_KEYS
    module = builtin_module_name(task["action"]["__ansible_module__"])
    parameter = {"assert": "that", "debug": "var"}.get(module or "")
    if parameter:
        for text in strings(task["action"].get(parameter)):
            yield text, True


def expression_node(value: str) -> nodes.Expr | None:
    """Parse one implicit expression without compiling or evaluating it."""
    try:
        template = Environment(optimized=False).parse("{{ " + value + " }}")
    except TemplateSyntaxError:
        return None
    if len(template.body) == 1 and isinstance(template.body[0], nodes.Output):
        output = template.body[0].nodes
        if len(output) == 1 and isinstance(output[0], nodes.Expr):
            return output[0]
    return None


def variable_reference(value: object) -> tuple[str, ...] | None:
    """Recognize a single unmodified variable or literal mapping access."""
    if not isinstance(value, str):
        return None
    try:
        template = Environment(optimized=False).parse(value)
    except TemplateSyntaxError:
        return None
    if (
        len(template.body) != 1
        or not isinstance(template.body[0], nodes.Output)
        or len(template.body[0].nodes) != 1
    ):
        return None
    node = template.body[0].nodes[0]
    keys: list[str] = []
    while isinstance(node, nodes.Getattr | nodes.Getitem):
        if isinstance(node, nodes.Getattr):
            keys.append(node.attr)
        elif isinstance(node.arg, nodes.Const) and isinstance(node.arg.value, str):
            keys.append(node.arg.value)
        else:
            return None
        node = node.node
    if isinstance(node, nodes.Name):
        return (node.name, *reversed(keys))
    return None


def nonboolean_condition(value: object) -> bool:
    """Reject only known nonboolean results; never infer variable/plugin types."""
    if isinstance(value, bool):
        return False
    if not isinstance(value, str):
        return True
    expression = expression_node(value)
    return expression is not None and _nonboolean_node(expression)


def _nonboolean_node(node: nodes.Expr) -> bool:
    if isinstance(node, nodes.Const):
        return not isinstance(node.value, bool)
    if isinstance(node, nodes.List | nodes.Dict | nodes.Tuple | nodes.Concat):
        return True
    if isinstance(node, nodes.And | nodes.Or):
        return _nonboolean_node(node.left) and _nonboolean_node(node.right)
    if isinstance(node, nodes.CondExpr) and node.expr2 is not None:
        return _nonboolean_node(node.expr1) and _nonboolean_node(node.expr2)
    if isinstance(node, nodes.Neg | nodes.Pos):
        return isinstance(node.node, nodes.Const) and isinstance(
            node.node.value, int | float
        )
    return False


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


def template_environment(
    content: str, overrides: dict[str, object] | None = None
) -> Environment:
    """Honor literal template delimiter headers without executing their values."""
    environment = Environment(optimized=False)
    header = (
        content.splitlines()[0].removeprefix("#jinja2:")
        if content.startswith("#jinja2:")
        else ""
    )
    try:
        expression = ast.parse("{" + header + "}", mode="eval").body
        if not isinstance(expression, ast.Dict):
            raise ValueError("Jinja environment header must be a mapping")
        options: dict[str, object] = dict(overrides or {})
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
