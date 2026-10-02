"""Require explicit condition lists."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from ansiblelint.errors import RuleMatchTransformMeta
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ansible_lint_foundata.fixes import wrap_scalar_list
from ansible_lint_foundata.policy import CONDITION_KEYS
from ansiblelint.rules import AnsibleLintRule, TransformMixin

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


@dataclass(frozen=True)
class ConditionKey(RuleMatchTransformMeta):
    """Identify the exact condition addressed by one diagnostic."""

    key: str


class FoundataConditionListRule(AnsibleLintRule, TransformMixin):
    """Use lists for when, changed_when and failed_when."""

    id = "foundata-condition-list"
    description = "Represent even a single condition as a list item."
    tags = ["opt-in", "formatting"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = (
        "https://foundata.com/en/guidelines/ansible-playbooks/#conditionals-formatting"
    )

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        return [
            self.create_matcherror(
                message=f"Use a list for {key}.",
                filename=file,
                data=task.raw_task,
                transform_meta=ConditionKey(key),
            )
            for key in CONDITION_KEYS
            if key in task.raw_task and not isinstance(task.raw_task[key], list)
        ]

    @override
    def transform(
        self,
        match: MatchError,
        lintable: Lintable,
        data: CommentedMap | CommentedSeq | str,
    ) -> None:
        task = self.seek(match.yaml_path, data)
        if not isinstance(task, CommentedMap) or not isinstance(
            match.transform_meta, ConditionKey
        ):
            return
        key = match.transform_meta.key
        value = task.get(key)
        # Nulls/mappings/numbers are invalid conditions, not safe fix targets.
        if isinstance(value, str | bool):
            wrap_scalar_list(task, key)
            match.fixed = True
