"""Pure policy checks, independent of Ansible's rule discovery mechanism."""

from __future__ import annotations

import re
from collections.abc import Sequence

from jinja2 import Environment, TemplateSyntaxError, nodes

CONDITION_KEYS = ("when", "changed_when", "failed_when")
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


def ordered_task_keys(keys: Sequence[str], action: str) -> list[str]:
    """Order documented keys, leaving unspecified keys in their original slots."""

    def rank(key: str) -> int | None:
        if key == action or key == "local_action":
            key = "action"
        elif key.startswith("with_"):
            key = "with_*"
        return _TASK_KEYS.index(key) if key in _TASK_KEYS else None

    ranks = {key: position for key in keys if (position := rank(key)) is not None}
    known = iter(sorted(ranks, key=ranks.__getitem__))
    return [next(known) if key in ranks else key for key in keys]


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


def template_names(value: str) -> set[str]:
    """Collect Jinja name references without evaluating the template or plugins."""
    try:
        template = Environment().parse(value)
    except TemplateSyntaxError:
        # Syntax diagnostics belong to Ansible Lint's existing Jinja rule.
        return set()
    return {node.name for node in template.find_all(nodes.Name) if node.ctx == "load"}
