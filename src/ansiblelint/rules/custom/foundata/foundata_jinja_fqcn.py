"""Extend module FQCN checks to statically named Jinja plugins in tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ansible_lint_foundata.expressions import plugin_references, task_expression_inputs
from ansible_lint_foundata.rules import FoundataRule

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


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
        matches = []
        seen: set[tuple[str, int]] = set()
        for text, implicit in task_expression_inputs(task):
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
