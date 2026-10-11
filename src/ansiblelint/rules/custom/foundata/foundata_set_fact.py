# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep declared inputs separate from computed host facts."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from ansible_lint_foundata.policy import builtin_module_name
from ansible_lint_foundata.rules import FoundataRule
from ansible_lint_foundata.source import role_directory, variable_bindings

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


class FoundataSetFactRule(FoundataRule):
    """Do not overwrite declared inputs/defaults with set_fact."""

    id = "foundata-set-fact"
    description = "Use a distinct variable for computed state instead of overwriting declared inputs."
    tags = ["opt-in", "idiom"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#misc"

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        action = task["action"]
        if (
            file is None
            or builtin_module_name(action["__ansible_module__"]) != "set_fact"
        ):
            return []
        declared: set[str] = set()
        for _, variables in variable_bindings(file, task):
            declared.update(name for name in variables if isinstance(name, str))
        role = role_directory(file)
        if role:
            for suffix in (".yml", ".yaml"):
                source = role / "meta" / ("argument_specs" + suffix)
                if not source.is_file():
                    continue
                try:
                    data = YAML(typ="safe").load(source.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, YAMLError):
                    continue
                specifications = (
                    data.get("argument_specs", {}) if isinstance(data, dict) else {}
                )
                if isinstance(specifications, dict):
                    for specification in specifications.values():
                        if isinstance(specification, dict) and isinstance(
                            specification.get("options"), dict
                        ):
                            declared.update(specification["options"])
        overwritten = declared & (
            set(action)
            - {"cacheable", "__ansible_module__", "__ansible_module_original__"}
        )
        return [
            self.create_matcherror(
                message=f"set_fact overwrites declared input {name!r}; use a distinct computed variable.",
                filename=file,
                data=task.raw_task,
            )
            for name in sorted(overwritten)
        ]
