"""Require explicit review of caller termination from reusable content."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ansible_lint_foundata.policy import builtin_module_name
from ansible_lint_foundata.rules import FoundataRule
from ansible_lint_foundata.source import (
    adjacent_comments,
    handler_file_context,
    role_directory,
)

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataNoEndPlayRule(FoundataRule):
    """Scope end_play, end_host and end_role to their intended callers."""

    id = "foundata-no-end-play"
    description = (
        "Review role caller-termination contracts and explain orchestration scope."
    )
    tags = ["opt-in", "idiom"]
    severity = "HIGH"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#misc"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        action = task["action"]
        operation = action.get("_raw_params")
        if builtin_module_name(
            action["__ansible_module__"]
        ) != "meta" or operation not in {"end_play", "end_host", "end_role"}:
            return []
        role = role_directory(file) if file is not None else None
        handler = task.kind == "handlers" or (
            file is not None and handler_file_context(file) is True
        )
        if operation == "end_role":
            if role is not None and not handler:
                return []
            message = "Use end_role only inside a role and outside handlers; ansible-core 2.18 or later is required."
        elif (
            file is not None
            and file.kind == "playbook"
            and role is None
            and not handler
        ):
            if adjacent_comments(file, task.line):
                return []
            message = f"Explain the purpose and affected scope of orchestration {operation} in an adjacent comment."
        else:
            message = f"{operation} terminates the caller's play, not just the role. Document the caller-termination contract and use a task-local noqa: {self.id} for a reviewed exception."
        return [
            self.create_matcherror(message=message, filename=file, data=task.raw_task)
        ]
