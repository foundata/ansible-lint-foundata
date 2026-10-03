"""Read-only style checks on original YAML mappings."""

from __future__ import annotations

from collections.abc import Iterator

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import ScalarString

from ansible_lint_foundata.policy import CONDITION_KEYS

PRIMARY_PARAMETERS = {
    "file": ("path", "state"),
    "template": ("src", "dest"),
    "copy": ("src", "content", "dest"),
    "debug": ("msg", "var"),
    "command": ("argv", "cmd"),
    "shell": ("cmd",),
    "service": ("name", "state"),
    "systemd": ("name", "state"),
    "systemd_service": ("name", "state"),
    "package": ("name", "state"),
    "apt": ("name", "state"),
    "dnf": ("name", "state"),
    "uri": ("url", "method", "body"),
    "get_url": ("url", "dest"),
}


def parameter_order(parameters: CommentedMap, module: str) -> list[str] | None:
    """Keep primary parameters stable, then permissions, then optional names."""
    if module not in PRIMARY_PARAMETERS or parameters.merge:
        return None
    keys = [key for key in parameters if isinstance(key, str) and key != "module"]
    primary = [key for key in keys if key in PRIMARY_PARAMETERS[module]]
    permissions = [key for key in ("owner", "group", "mode") if key in keys]
    optional = sorted(set(keys) - set(primary) - set(permissions))
    expected = primary + permissions + optional
    return expected if keys != expected else None


def unquoted_values(task: CommentedMap, module: str, action: str) -> list[str]:
    """Find plain values while leaving expressions and binding names alone."""
    excluded: set[tuple[str, ...]] = {
        (key,) for key in {*CONDITION_KEYS, "register", "block", "rescue", "always"}
    }
    excluded.update({("loop_control", "loop_var"), ("loop_control", "index_var")})
    for key in {action, "action", "local_action", "args"}:
        if key in {"action", "local_action"}:
            excluded.add((key, "module"))
        if module == "debug":
            excluded.add((key, "var"))
        if module == "assert":
            excluded.add((key, "that"))
    seen: set[int] = set()

    def walk(value: object, path: tuple[str, ...]) -> Iterator[str]:
        if path in excluded:
            return
        if isinstance(value, str):
            if value and not isinstance(value, ScalarString):
                yield ".".join(path)
        elif isinstance(value, dict | list):
            if id(value) in seen:
                return
            seen.add(id(value))
            items = value.items() if isinstance(value, dict) else enumerate(value)
            for key, child in items:
                yield from walk(child, (*path, str(key)))

    return list(walk(task, ()))
