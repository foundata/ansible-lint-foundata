# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Resolve notifications only where the local handler namespace is known."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, override

from ansiblelint.runner import Runner

from ansible_lint_foundata.rules import FoundataRule
from ansible_lint_foundata.task_graph import graphs_for_file, literal

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable


class FoundataNotifyRule(FoundataRule):
    """Notify listen topics; diagnose missing targets only in closed local plays."""

    id = "foundata-notify"
    description = (
        "Resolve literal local targets without guessing dynamic or external handlers."
    )
    tags = ["opt-in", "idiom"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#handlers"

    @override
    def matchtasks(self, file: Lintable) -> list[MatchError]:
        if (
            file.kind not in {"playbook", "tasks", "handlers"}
            or self.options is None
            or self._collection is None
        ):
            return []
        resolver = Runner(
            rules=self._collection,
            exclude_paths=self.options.exclude_paths,
            project_dir=self.options.project_dir,
        )
        matches = []
        for graph in graphs_for_file(
            file, Path(self.options.project_dir or file.path.parent), resolver
        ):
            for entry in graph.entries:
                task = entry.task
                if self.id in task.skip_tags or "skip_ansible_lint" in task.get(
                    "tags", []
                ):
                    continue
                targets = task.raw_task.get("notify", [])
                for raw in targets if isinstance(targets, list) else [targets]:
                    target = literal(raw)
                    if target is None or target in graph.topics:
                        continue
                    if target in graph.handler_names:
                        message = (
                            f"Notify a listen topic instead of handler name {target!r}."
                        )
                    elif graph.closed:
                        message = f"No handler listens to {target!r} in this fully resolved local play."
                    else:
                        continue
                    matches.append(
                        self.create_matcherror(
                            message=message,
                            filename=entry.file,
                            lineno=task.line,
                            data=task.raw_task,
                        )
                    )
        return matches
