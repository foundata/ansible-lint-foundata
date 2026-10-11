# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check string value quoting without rewriting YAML."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ansible_lint_foundata.policy import builtin_module_name
from ansible_lint_foundata.rules import FoundataRule
from ansible_lint_foundata.source import source_task
from ansible_lint_foundata.style import unquoted_values

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataStringQuotesRule(FoundataRule):
    """Quote ordinary task string values, excluding expressions and identifiers."""

    id = "foundata-string-quotes"
    description = "Quote ordinary string values without changing their meaning."
    tags = ["opt-in", "formatting"]
    severity = "LOW"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#quoting"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        if file is None or (original := source_task(file, task)) is None:
            return []
        module = builtin_module_name(task["action"]["__ansible_module__"])
        paths = unquoted_values(original, module or "", task.action)
        return [
            self.create_matcherror(
                message=f"Quote string value: {path}.", filename=file
            )
            for path in paths
        ]
