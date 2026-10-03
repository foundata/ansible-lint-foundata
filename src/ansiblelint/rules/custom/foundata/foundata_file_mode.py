"""Check absolute symbolic permissions and their octal documentation."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ruamel.yaml.comments import CommentedMap

from ansible_lint_foundata.policy import file_mode_message
from ansible_lint_foundata.source import source_task
from ansiblelint.rules import AnsibleLintRule

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task

# Only modules whose mode parameter is a filesystem permission, not e.g. an
# application-specific operating mode. Extend this list with regression fixtures.
_MODULES = {
    "assemble",
    "blockinfile",
    "copy",
    "file",
    "get_url",
    "lineinfile",
    "replace",
    "template",
    "unarchive",
    "uri",
}


class FoundataFileModeRule(AnsibleLintRule):
    """Use complete symbolic modes with a matching inline octal comment."""

    id = "foundata-file-mode"
    description = "Reject relative modes and mismatched or missing octal comments."
    tags = ["opt-in", "idiom"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#misc"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        module = task["action"]["__ansible_module__"]
        if not file or module not in _MODULES:
            return []
        original = source_task(file, task)
        if original is None:
            return []
        results = []
        for key in (task.action, "args"):
            parameters = original.get(key)
            if not isinstance(parameters, CommentedMap) or "mode" not in parameters:
                continue
            comment_tokens = parameters.ca.items.get("mode")
            comment = (
                comment_tokens[2].value.splitlines()[0]
                if comment_tokens and comment_tokens[2]
                else ""
            )
            message = file_mode_message(parameters["mode"], comment)
            if message is None:
                continue
            results.append(
                self.create_matcherror(
                    message=message,
                    filename=file,
                    lineno=parameters.lc.key("mode")[0] + 1,
                )
            )
        return results
