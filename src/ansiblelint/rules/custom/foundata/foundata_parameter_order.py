"""Advisory order for a fixed set of built-in module interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ruamel.yaml.comments import CommentedMap

from ansible_lint_foundata.policy import builtin_module_name
from ansible_lint_foundata.rules import FoundataRule
from ansible_lint_foundata.source import source_task
from ansible_lint_foundata.style import parameter_order

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataParameterOrderRule(FoundataRule):
    """Group primary and permission parameters before optional parameters."""

    id = "foundata-parameter-order"
    description = "Group known module parameters, leaving nested data untouched."
    tags = ["opt-in", "formatting"]
    severity = "LOW"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#tasks-plays"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        if file is None or (original := source_task(file, task)) is None:
            return []
        module = builtin_module_name(task["action"]["__ansible_module__"])
        results = []
        for key in dict.fromkeys((task.action, "action", "local_action", "args")):
            parameters = original.get(key)
            if isinstance(parameters, CommentedMap) and (
                expected := parameter_order(parameters, module or "")
            ):
                results.append(
                    self.create_matcherror(
                        message=f"Suggested {key} parameter order: {', '.join(expected)}.",
                        filename=file,
                    )
                )
        return results
