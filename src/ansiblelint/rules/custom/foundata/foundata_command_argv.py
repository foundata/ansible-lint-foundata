# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject shell quoting that becomes literal data in command argv."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ansible_lint_foundata.expressions import has_quote_filter
from ansible_lint_foundata.policy import builtin_module_name
from ansible_lint_foundata.rules import FoundataRule

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataCommandArgvRule(FoundataRule):
    """Do not apply shell-quoting filters to command argv arguments."""

    id = "foundata-command-argv"
    description = (
        "The quote filter changes argv data; it does not protect its boundaries."
    )
    tags = ["opt-in", "command-shell"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#external-commands"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        action = task["action"]
        if builtin_module_name(action["__ansible_module__"]) != "command":
            return []
        argv = action.get("argv")
        values = argv if isinstance(argv, list) else [argv]
        if any(isinstance(value, str) and has_quote_filter(value) for value in values):
            return [
                self.create_matcherror(
                    message="Pass argv values without shell-quoting filters.",
                    filename=file,
                    data=task.raw_task,
                )
            ]
        return []
