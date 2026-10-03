"""Pure policy checks, independent of Ansible's rule discovery mechanism."""

from __future__ import annotations

import re
from collections.abc import Sequence

from jinja2 import Environment, TemplateSyntaxError, meta, nodes, pass_context
from jinja2.runtime import Context

CONDITION_KEYS = ("when", "changed_when", "failed_when")
STOCK_TASK_BOUNDARIES = ("name", "block", "rescue", "always")
_TASK_KEYS = (
    "name",
    "delegate_to",
    "become",
    "action",
    "args",
    "vars",
    "environment",
    "when",
    "changed_when",
    "failed_when",
    "ignore_errors",
    "run_once",
    "loop",
    "loop_control",
    "with_*",
    "register",
    "no_log",
    "notify",
    "listen",
    "tags",
    "block",
    "rescue",
    "always",
)
_MODE_CLAUSE = re.compile(r"([ugoa]+)=([rwxst]*)")
_OCTAL_COMMENT = re.compile(r"#\s*([0-7]{4})\b")


def builtin_module_name(name: str) -> str | None:
    """Identify built-in actions without stripping third-party namespaces."""
    for prefix in ("ansible.builtin.", "ansible.legacy."):
        if name.startswith(prefix):
            name = name.removeprefix(prefix)
            break
    return name if "." not in name else None


def ordered_task_keys(keys: Sequence[str], action: str) -> list[str]:
    """Extend stock boundaries, preserving unknown slots within the middle group."""

    def rank(key: str) -> int | None:
        if key == action or key == "local_action":
            key = "action"
        elif key.startswith("with_"):
            key = "with_*"
        return _TASK_KEYS.index(key) if key in _TASK_KEYS else None

    middle = [key for key in keys if key not in STOCK_TASK_BOUNDARIES]
    ranks = {key: position for key in middle if (position := rank(key)) is not None}
    known = iter(sorted(ranks, key=ranks.__getitem__))
    return (
        [key for key in keys if key == "name"]
        + [next(known) if key in ranks else key for key in middle]
        + [key for key in STOCK_TASK_BOUNDARIES[1:] if key in keys]
    )


def is_handler_topic(value: object) -> bool:
    """Accept nonempty static lowercase topics without changing their spelling."""
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value == value.lower()
        and "{{" not in value
        and "{%" not in value
    )


def absolute_mode(value: str) -> int | None:
    """Return a fixed permission mode, rejecting state-dependent symbolic forms.

    Each class must be assigned explicitly. Explicit special bits are supported;
    umask-dependent assignments and copies of existing bits are not.
    """
    seen: set[str] = set()
    result = 0
    for clause in value.split(","):
        match = _MODE_CLAUSE.fullmatch(clause)
        if match is None:
            return None
        users, permissions = match.groups()
        if users == "a":
            users = "ugo"
        if "a" in users or len(set(users)) != len(users):
            return None
        seen.update(users)
        for user in users:
            shift = {"u": 6, "g": 3, "o": 0}[user]
            special_bit = {"u": 0o4000, "g": 0o2000, "o": 0o1000}[user]
            result &= ~((7 << shift) | special_bit)
            for permission, bit in (("r", 4), ("w", 2), ("x", 1)):
                if permission in permissions:
                    result |= bit << shift
            if (user in "ug" and "s" in permissions) or (
                user == "o" and "t" in permissions
            ):
                result |= special_bit
    return result if seen == {"u", "g", "o"} else None


def mode_comment_matches(mode: int, comment: str) -> bool:
    """Check the leading octal representation in an inline YAML comment."""
    match = _OCTAL_COMMENT.match(comment)
    return match is not None and int(match.group(1), 8) == mode


def file_mode_message(value: object, comment: str) -> str | None:
    """Describe an invalid literal mode or its missing octal documentation."""
    # Runtime modes are review/test concerns, not statically known values.
    if isinstance(value, str) and ("{{" in value or "{%" in value):
        return None
    number = absolute_mode(value) if isinstance(value, str) else None
    if number is None:
        return "Use a complete absolute symbolic mode, such as u=rw,g=r,o=r."
    if not mode_comment_matches(number, comment):
        return f"Document this mode with a matching inline # {number:04o} comment."
    return None


@pass_context
def _analysis_plugin(context: Context, *args: object, **kwargs: object) -> None:
    """Prevent constant folding from executing filters or tests during analysis."""


def template_names(value: str) -> set[str]:
    """Collect external references using Jinja's lexical scope analysis."""
    environment = Environment(optimized=False)
    try:
        template = environment.parse(value)
        # Meta analysis compiles but never renders. Context-dependent inert
        # plugins accept collection names without loading or running plugins.
        for node in template.find_all(nodes.Filter):
            environment.filters[node.name] = _analysis_plugin
        for test in template.find_all(nodes.Test):
            environment.tests[test.name] = _analysis_plugin
        names = meta.find_undeclared_variables(template)
    except TemplateSyntaxError:
        # Syntax diagnostics belong to Ansible Lint's existing Jinja rule.
        return set()
    if "vars" in names:
        for access in template.find_all(nodes.Getitem):
            if (
                isinstance(access.node, nodes.Name)
                and access.node.name == "vars"
                and isinstance(access.arg, nodes.Const)
                and isinstance(access.arg.value, str)
            ):
                names.add(access.arg.value)
    for call in template.find_all(nodes.Call):
        if (
            isinstance(call.node, nodes.Name)
            and call.node.name in names & {"lookup", "query", "q"}
            and call.args
            and isinstance(call.args[0], nodes.Const)
            and call.args[0].value
            in ("vars", "ansible.builtin.vars", "ansible.legacy.vars")
        ):
            names.update(
                argument.value
                for argument in call.args[1:]
                if isinstance(argument, nodes.Const) and isinstance(argument.value, str)
            )
    return names
