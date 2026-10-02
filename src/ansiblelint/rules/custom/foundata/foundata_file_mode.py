"""Check absolute symbolic permissions and their octal documentation."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ruamel.yaml.comments import CommentedMap

from ansible_lint_foundata.policy import absolute_mode, mode_comment_matches
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
            value = parameters["mode"]
            # Runtime modes are review/test concerns, not statically known values.
            if isinstance(value, str) and ("{{" in value or "{%" in value):
                continue
            number = absolute_mode(value) if isinstance(value, str) else None
            comment_tokens = parameters.ca.items.get("mode")
            comment = (
                comment_tokens[2].value.splitlines()[0]
                if comment_tokens and comment_tokens[2]
                else ""
            )
            if number is None:
                message = "Use a complete absolute symbolic mode, such as u=rw,g=r,o=r."
            elif not mode_comment_matches(number, comment):
                message = (
                    f"Document this mode with a matching inline # {number:04o} comment."
                )
            else:
                continue
            results.append(
                self.create_matcherror(
                    message=message,
                    filename=file,
                    lineno=parameters.lc.key("mode")[0] + 1,
                )
            )
        return results
