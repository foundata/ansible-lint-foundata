# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Require lowercase handler topics in lists."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ansiblelint.runner import Runner
from ansiblelint.utils import task_in_list
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ansible_lint_foundata.fixes import wrap_scalar_list
from ansible_lint_foundata.policy import (
    builtin_module_name,
    handler_topic_message,
)
from ansible_lint_foundata.rules import FoundataRule
from ansible_lint_foundata.source import (
    adjacent_comments,
    handler_file_context,
    role_topic_prefix,
    source_task,
)
from ansiblelint.rules import TransformMixin

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataHandlerListenRule(FoundataRule, TransformMixin):
    """Give handlers explicit lowercase listen topics in list form."""

    id = "foundata-handler-listen"
    description = "Namespace role topics and document shared broadcasts."
    tags = ["opt-in", "idiom"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#handlers"

    @staticmethod
    def _is_handler(task: Task, file: Lintable | None) -> bool:
        if file is not None and file.kind != "playbook":
            context = handler_file_context(file)
            if context is not None:
                return context
        return task.kind == "handlers"

    @override
    def matchtasks(self, file: Lintable) -> list[MatchError]:
        matches = super().matchtasks(file)
        if (
            file.kind not in {"handlers", "tasks", "playbook"}
            or self._collection is None
            or self.options is None
        ):
            return matches
        # Upstream discovery does not descend into files classified as handlers.
        # Reuse its path resolver and exclusions, but never render dynamic paths.
        resolver = Runner(
            rules=self._collection,
            exclude_paths=self.options.exclude_paths,
            project_dir=self.options.project_dir,
        )
        pending = [file]
        visited = {file.path.resolve()}
        while pending:
            current = pending.pop()
            for task in task_in_list(
                current.data, kind=str(current.kind), file=current
            ):
                if task.error is not None or not self._is_handler(task, current):
                    continue
                action = task["action"]
                target = action.get("file", action.get("_raw_params"))
                if (
                    builtin_module_name(action["__ansible_module__"]) != "import_tasks"
                    or not isinstance(target, str)
                    or any(marker in target for marker in ("{{", "{%"))
                ):
                    continue
                for child in resolver.play_children(
                    current,
                    ("import_tasks", target),
                    "handlers",
                    str(current.path.parent),
                ):
                    path = child.path.resolve()
                    if (
                        path in visited
                        or resolver.is_excluded(child)
                        or not path.is_file()
                    ):
                        continue
                    visited.add(path)
                    matches.extend(super().matchtasks(child))
                    pending.append(child)
        return matches

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        if (
            not self._is_handler(task, file)
            or builtin_module_name(task["action"]["__ansible_module__"])
            == "import_tasks"
        ):
            return []
        value = task.raw_task.get("listen")
        messages = []
        if not isinstance(value, list):
            messages.append("Define listen as a nonempty list of lowercase topics.")
        topics = value if isinstance(value, list) else [value]
        prefix = role_topic_prefix(file) if file is not None else None
        original = source_task(file, task) if file is not None else None
        source_topics = original.get("listen") if original is not None else None
        if not topics:
            messages.append("Listen topics must be nonempty, static lowercase strings.")
        for index, topic in enumerate(topics):
            line = task.line
            if isinstance(source_topics, CommentedSeq) and index < len(source_topics):
                line = source_topics.lc.item(index)[0] + 1
            elif original is not None and "listen" in original:
                line = original.lc.key("listen")[0] + 1
            comment = adjacent_comments(file, line) if file is not None else ""
            message = handler_topic_message(topic, prefix, comment)
            if message is not None and message not in messages:
                messages.append(message)
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
        if isinstance(task, CommentedMap) and isinstance(task.get("listen"), str):
            line = task.lc.key("listen")[0] + 1
            if (
                handler_topic_message(
                    task["listen"],
                    role_topic_prefix(lintable),
                    adjacent_comments(lintable, line),
                )
                is None
            ):
                wrap_scalar_list(task, "listen")
                match.fixed = True
