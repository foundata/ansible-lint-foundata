"""Require lowercase handler topics in lists."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ansible_lint_foundata.fixes import wrap_scalar_list
from ansible_lint_foundata.policy import builtin_module_name, is_handler_topic
from ansible_lint_foundata.rules import FoundataRule
from ansiblelint.rules import TransformMixin

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataHandlerListenRule(FoundataRule, TransformMixin):
    """Give handlers explicit lowercase listen topics in list form."""

    id = "foundata-handler-listen"
    description = "Legacy uppercase aliases are violations, not exceptions."
    tags = ["opt-in", "idiom"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#handlers"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        if (
            task.kind != "handlers"
            or builtin_module_name(task["action"]["__ansible_module__"])
            == "import_tasks"
        ):
            return []
        value = task.raw_task.get("listen")
        messages = []
        if not isinstance(value, list):
            messages.append("Define listen as a nonempty list of lowercase topics.")
        topics = value if isinstance(value, list) else [value]
        if not topics or any(not is_handler_topic(topic) for topic in topics):
            messages.append("Listen topics must be nonempty, static lowercase strings.")
        return [
            self.create_matcherror(message=message, filename=file, data=task.raw_task)
            for message in messages
        ]

    @override
    def transform(
        self,
        match: MatchError,
        lintable: Lintable,
        data: CommentedMap | CommentedSeq | str,
    ) -> None:
        task = self.seek(match.yaml_path, data)
        if isinstance(task, CommentedMap) and is_handler_topic(task.get("listen")):
            wrap_scalar_list(task, "listen")
            match.fixed = True
