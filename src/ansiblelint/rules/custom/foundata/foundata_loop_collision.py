# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check loop binding collisions across literal local includes and roles."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, override

from ansiblelint.runner import Runner

from ansible_lint_foundata.rules import FoundataRule
from ansible_lint_foundata.task_graph import graphs_for_file, loop_variables

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable


class FoundataLoopCollisionRule(FoundataRule):
    """Keep nested loop and index bindings distinct across task files."""

    id = "foundata-loop-collision"
    description = (
        "Trace literal includes without guessing dynamic paths or renaming bindings."
    )
    tags = ["opt-in", "idiom"]
    severity = "HIGH"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#loops"

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
                collisions = loop_variables(task) & entry.outer_loops
                if collisions:
                    matches.append(
                        self.create_matcherror(
                            message=f"Nested loop rebinds outer variables: {', '.join(sorted(collisions))}.",
                            filename=entry.file,
                            lineno=task.line,
                            data=task.raw_task,
                        )
                    )
        return matches
