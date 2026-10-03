"""Characterize static analysis without loading any Ansible collections."""

import pytest

from ansible_lint_foundata.expressions import (
    has_quote_filter,
    nonboolean_condition,
    plugin_references,
    template_environment,
)
from ansible_lint_foundata.policy import template_names


@pytest.mark.parametrize(
    ("value", "invalid"),
    [
        (True, False),
        (False, False),
        (0, True),
        (None, True),
        ({}, True),
        ("true", False),
        ("false", False),
        ("'false'", True),
        ("1", True),
        ("none", True),
        ("[true]", True),
        ("{}", True),
        ("(1, 2)", True),
        ("-1", True),
        ("'a' ~ value", True),
        ("1 or 'x'", True),
        ("'a' if enabled else []", True),
        ("true if enabled else 0", False),
        ("value", False),
        ("value | ansible.builtin.bool", False),
        ("value is ansible.builtin.defined", False),
        ("not value", False),
        ("value == 'x'", False),
        ("value or 'x'", False),
        ("broken (", False),
        ("{{ value }}", False),
        ("lookup('pipe', 'never execute')", False),
    ],
)
def test_provably_nonboolean_conditions(value: object, invalid: bool) -> None:
    assert nonboolean_condition(value) is invalid


@pytest.mark.parametrize(
    ("value", "implicit", "expected"),
    [
        ("{{ value | default('x') }}", False, {"default"}),
        ("value is defined", True, {"defined"}),
        ("value is defined", False, set()),
        ("{{ range(3) }}", False, set()),
        ("{{ lookup('env', 'HOME') }}", False, {"env"}),
        ("{{ query('ansible.builtin.env', 'HOME') }}", False, {"ansible.builtin.env"}),
        (
            "{{ values | ansible.builtin.map('quote') }}",
            False,
            {"ansible.builtin.map", "quote"},
        ),
        (
            "{{ values | ansible.builtin.selectattr('name', 'equalto', 'x') }}",
            False,
            {"ansible.builtin.selectattr", "equalto"},
        ),
        (
            "{{ values | ansible.builtin.select('==', 3) }}",
            False,
            {"ansible.builtin.select"},
        ),
        (
            "{{ values | other.collection.map('literal') }}",
            False,
            {"other.collection.map"},
        ),
        (
            "{% macro lookup(value) %}{{ value }}{% endmacro %}{{ lookup('literal') }}",
            False,
            set(),
        ),
        ("{{ lookup(plugin_name, 'key') }}", False, set()),
        ("{{ broken", False, set()),
    ],
)
def test_literal_plugin_references(
    value: str, implicit: bool, expected: set[str]
) -> None:
    assert {name for name, _ in plugin_references(value, implicit=implicit)} == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("{{ value | ansible.builtin.quote }}", True),
        ("{{ values | ansible.builtin.map('ansible.builtin.quote') }}", True),
        ("{{ value | other.collection.quote }}", False),
        ("'a literal argument'", False),
        ("{{ value }}", False),
    ],
)
def test_argv_quoting_is_a_filter_not_a_substring(value: str, expected: bool) -> None:
    assert has_quote_filter(value) is expected


def test_template_delimiter_headers() -> None:
    value = (
        "#jinja2:variable_start_string:'[%', variable_end_string:'%]'\n[% external %]\n"
    )
    environment = template_environment(value)
    assert template_names(value, environment=environment) == {"external"}


def test_unsupported_environment_is_not_silently_accepted() -> None:
    with pytest.raises(ValueError, match="Unsupported Jinja"):
        template_environment("#jinja2:unknown: True\n{{ external }}\n")
