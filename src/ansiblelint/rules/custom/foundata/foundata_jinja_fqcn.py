"""Extend module FQCN checks to statically named Jinja plugins in tasks."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, override

from ansible_lint_foundata.expressions import plugin_references
from ansible_lint_foundata.policy import builtin_module_name
from ansible_lint_foundata.rules import FoundataRule

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


def _strings(value: object, seen: set[int] | None = None) -> Iterator[str]:
    seen = set() if seen is None else seen
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict) and id(value) not in seen:
        seen.add(id(value))
        for key, child in value.items():
            yield from _strings(key, seen)
            yield from _strings(child, seen)
    elif isinstance(value, list) and id(value) not in seen:
        seen.add(id(value))
        for child in value:
            yield from _strings(child, seen)


class FoundataJinjaFqcnRule(FoundataRule):
    """Use collection-qualified names for Jinja filters, tests and lookups."""

    id = "foundata-jinja-fqcn"
    description = "Check literal plugin references without guessing their provider."
    tags = ["opt-in", "idiom"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#naming"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        inputs: list[tuple[str, bool]] = []
        for key, value in task.raw_task.items():
            if key.startswith("__") or key in {"block", "rescue", "always"}:
                continue
            implicit = key in {"when", "changed_when", "failed_when", "until"}
            inputs.extend((text, implicit) for text in _strings(value))
        if builtin_module_name(task["action"]["__ansible_module__"]) == "assert":
            inputs.extend((text, True) for text in _strings(task["action"].get("that")))
        matches = []
        seen: set[tuple[str, int]] = set()
        for text, implicit in inputs:
            for name, _ in plugin_references(text, implicit=implicit):
                location = (name, task.line)
                if name.count(".") >= 2 or location in seen:
                    continue
                seen.add(location)
                matches.append(
                    self.create_matcherror(
                        message=f"Use the collection-qualified name for plugin {name!r}.",
                        filename=file,
                        lineno=location[1],
                    )
                )
        return matches
