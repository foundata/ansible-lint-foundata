# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Apply the documented task-key ordering."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ansible_lint_foundata.policy import STOCK_TASK_BOUNDARIES, ordered_task_keys
from ansible_lint_foundata.rules import FoundataRule

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataTaskOrderRule(FoundataRule):
    """Order task keys by execution context, conditions and results."""

    id = "foundata-task-order"
    description = "Extend stock key-order with foundata's documented task keys."
    tags = ["opt-in", "formatting"]
    severity = "LOW"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#tasks-plays"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        keys = [
            key
            for key in task.raw_task
            if not key.startswith("__") and key != "skipped_rules"
        ]
        expected = ordered_task_keys(keys, task.action)
        if [key for key in keys if key not in STOCK_TASK_BOUNDARIES] == [
            key for key in expected if key not in STOCK_TASK_BOUNDARIES
        ]:
            return []
        return [
            self.create_matcherror(
                message=f"Order task keys as: {', '.join(expected)}.",
                filename=file,
                data=task.raw_task,
            )
        ]
