# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep role handler execution under the calling play's control."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ansible_lint_foundata.policy import builtin_module_name
from ansible_lint_foundata.rules import FoundataRule
from ansible_lint_foundata.source import role_directory

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataNoFlushHandlersRule(FoundataRule):
    """Reject flushing the calling play's handlers from role content."""

    id = "foundata-no-flush-handlers"
    description = "Keep role actions from flushing every notified handler of the play."
    tags = ["opt-in", "idiom"]
    severity = "HIGH"
    version_changed = "1.2.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#handlers"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        action = task["action"]
        if (
            builtin_module_name(action["__ansible_module__"]) != "meta"
            or action.get("_raw_params") != "flush_handlers"
            or file is None
            or file.kind == "playbook"
        ):
            return []
        role = role_directory(file)
        if role is None:
            return []
        path = file.path.resolve()
        if path.relative_to(role).parts[0] not in {"tasks", "handlers"} or any(
            parent.name == "molecule" and parent.parent.name == "extensions"
            for parent in path.parents
        ):
            return []
        message = "flush_handlers in a role runs every notified handler of the calling play. Run the action as a task instead; use a task-local noqa: foundata-no-flush-handlers for a reviewed exception."
        return [
            self.create_matcherror(message=message, filename=file, data=task.raw_task)
        ]
