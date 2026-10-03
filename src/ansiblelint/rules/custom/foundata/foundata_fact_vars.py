"""Keep facts usable with INJECT_FACTS_AS_VARS disabled."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from ansible_lint_foundata.expressions import strings, task_expression_inputs
from ansible_lint_foundata.facts import injected_fact_references
from ansible_lint_foundata.rules import FoundataRule

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataFactVarsRule(FoundataRule):
    """Read known gathered facts through ansible_facts."""

    id = "foundata-fact-vars"
    description = (
        "Check known injected aliases without banning magic or connection variables."
    )
    tags = ["opt-in", "idiom"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#facts"

    def _matches(
        self, names: set[str], file: Lintable | None, line: int
    ) -> list[MatchError]:
        return [
            self.create_matcherror(
                message=f"Read {name} through ansible_facts['{name.removeprefix('ansible_')}'] (under the same hostvars entry when applicable).",
                filename=file,
                lineno=line,
            )
            for name in sorted(names)
        ]

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        names: set[str] = set()
        for value, implicit in task_expression_inputs(task):
            names.update(injected_fact_references(value, implicit=implicit))
        return self._matches(names, file, task.line)

    @override
    def matchplay(self, file: Lintable, data: dict[str, Any]) -> list[MatchError]:
        values = (
            data
            if str(file.kind) == "vars"
            else data.get("vars", {})
            if file.kind == "playbook"
            else {}
        )
        names: set[str] = set()
        for value in strings(values):
            names.update(injected_fact_references(value))
        return self._matches(names, file, int(data.get("__line__", 1)))
