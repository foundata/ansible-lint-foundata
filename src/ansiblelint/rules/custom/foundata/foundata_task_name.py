"""Check the contexts in which dynamic names are prohibited."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from ansible_lint_foundata.policy import template_names
from ansible_lint_foundata.rules import FoundataRule

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataTaskNameRule(FoundataRule):
    """Keep play names static and loop variables out of task names."""

    id = "foundata-task-name"
    description = "Dynamic play names and loop-item task names are not reliable labels."
    tags = ["opt-in", "idiom"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#tasks-plays"

    @override
    def matchplay(self, file: Lintable, data: dict[str, Any]) -> list[MatchError]:
        name = data.get("name")
        if (
            file.kind == "playbook"
            and isinstance(name, str)
            and ("{{" in name or "{%" in name)
        ):
            return [
                self.create_matcherror(
                    message="Keep play names static.",
                    filename=file,
                    data=data,
                )
            ]
        return []

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> bool:
        if "loop" not in task.raw_task and not any(
            key.startswith("with_") for key in task.raw_task
        ):
            return False
        loop_control = task.raw_task.get("loop_control", {})
        if not isinstance(loop_control, dict):
            return False
        if not isinstance(task.name, str):
            return False
        names = template_names(task.name)
        return any(
            isinstance(variable, str) and variable in names
            for variable in (
                loop_control.get("loop_var", "item"),
                loop_control.get("index_var"),
            )
        )
