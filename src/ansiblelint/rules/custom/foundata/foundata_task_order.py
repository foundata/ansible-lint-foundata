"""Apply the documented task-key ordering."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ansible_lint_foundata.fixes import reorder_task
from ansible_lint_foundata.policy import ordered_task_keys
from ansible_lint_foundata.rules import FoundataRule
from ansiblelint.rules import TransformMixin

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataTaskOrderRule(FoundataRule, TransformMixin):
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
        if keys == expected:
            return []
        return [
            self.create_matcherror(
                message=f"Order task keys as: {', '.join(expected)}.",
                filename=file,
                data=task.raw_task,
            )
        ]

    @override
    def transform(
        self,
        match: MatchError,
        lintable: Lintable,
        data: CommentedMap | CommentedSeq | str,
    ) -> None:
        task = self.seek(match.yaml_path, data)
        if not isinstance(task, CommentedMap) or match.task is None or task.merge:
            return
        reorder_task(task, ordered_task_keys(list(task), match.task.action))
        match.fixed = True
