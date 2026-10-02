"""Require an explicit verbosity threshold for debug output."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ansiblelint.rules import AnsibleLintRule

if TYPE_CHECKING:
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataDebugVerbosityRule(AnsibleLintRule):
    """Set verbosity explicitly on debug tasks."""

    id = "foundata-debug-verbosity"
    description = "Choose a debug verbosity threshold explicitly."
    tags = ["opt-in", "idiom"]
    severity = "LOW"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#misc"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> bool:
        action = task["action"]
        return action["__ansible_module__"] == "debug" and "verbosity" not in action
