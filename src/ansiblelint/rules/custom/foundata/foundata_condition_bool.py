# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject condition results known to be nonboolean without evaluating Jinja."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ansible_lint_foundata.expressions import nonboolean_condition
from ansible_lint_foundata.policy import CONDITION_KEYS, builtin_module_name
from ansible_lint_foundata.rules import FoundataRule

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataConditionBoolRule(FoundataRule):
    """Use expressions that return actual booleans in conditions."""

    id = "foundata-condition-bool"
    description = "Reject provably nonboolean conditions; runtime types remain unknown."
    tags = ["opt-in", "idiom"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#conditionals"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        matches = []
        values = {
            key: task.raw_task[key] for key in CONDITION_KEYS if key in task.raw_task
        }
        action = task["action"]
        if (
            builtin_module_name(action["__ansible_module__"]) == "assert"
            and "that" in action
        ):
            values["assert.that"] = action["that"]
        for key, value in values.items():
            conditions = value if isinstance(value, list) else [value]
            for index, condition in enumerate(conditions, start=1):
                if nonboolean_condition(condition):
                    matches.append(
                        self.create_matcherror(
                            message=f"{key} item {index} is provably nonboolean; use an explicit predicate.",
                            filename=file,
                            data=task.raw_task,
                        )
                    )
        return matches
