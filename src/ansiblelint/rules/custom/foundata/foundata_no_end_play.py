"""Prevent accidentally ending a play for every host."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ansible_lint_foundata.policy import builtin_module_name
from ansible_lint_foundata.rules import FoundataRule

if TYPE_CHECKING:
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataNoEndPlayRule(FoundataRule):
    """Do not terminate all hosts with meta: end_play."""

    id = "foundata-no-end-play"
    description = (
        "Choose host-local termination when appropriate; never rewrite it blindly."
    )
    tags = ["opt-in", "idiom"]
    severity = "HIGH"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#misc"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> bool:
        action = task["action"]
        return bool(
            builtin_module_name(action["__ansible_module__"]) == "meta"
            and action.get("_raw_params") == "end_play"
        )
