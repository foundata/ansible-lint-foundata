"""Check the explicit input interface of Jinja template files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, override

from ansiblelint.file_utils import Lintable
from ansiblelint.runner import Runner
from ansiblelint.skip_utils import get_rule_skips_from_line
from jinja2 import TemplateSyntaxError

from ansible_lint_foundata.expressions import template_environment
from ansible_lint_foundata.policy import builtin_module_name
from ansible_lint_foundata.rules import FoundataRule
from ansible_lint_foundata.source import role_directory
from ansible_lint_foundata.task_graph import literal
from ansible_lint_foundata.template_graph import (
    TemplateGraph,
    template_entry_points,
    template_root,
)

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.utils import Task


class FoundataTemplateInputsRule(FoundataRule):
    """Pass external template data through explicit tpl_ inputs."""

    id = "foundata-template-inputs"
    description = "Distinguish template-local bindings from ambient Ansible data."
    tags = ["opt-in", "idiom"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#templates"

    def _allowed(self, path: Path) -> bool:
        lintable = Lintable(path)
        if self.options is not None and self._collection is not None:
            resolver = Runner(
                rules=self._collection,
                exclude_paths=self.options.exclude_paths,
                project_dir=self.options.project_dir,
            )
            if resolver.is_excluded(lintable):
                return False
        try:
            first_line = path.read_text(encoding="utf-8").split("\n", 1)[0]
        except (OSError, UnicodeError):
            return False
        return self.id not in get_rule_skips_from_line(first_line, lintable=lintable)

    @override
    def matchlines(self, file: Lintable) -> list[MatchError]:
        if str(file.kind) != "jinja2":
            return []
        first_line = file.content.split("\n", 1)[0]
        if self.id in get_rule_skips_from_line(first_line, lintable=file):
            return []
        external: dict[Path, set[str]] = {}
        try:
            for entry in template_entry_points(file.path, self._allowed):
                environment = template_environment(entry.read_text(encoding="utf-8"))
                result = TemplateGraph(template_root(entry), self._allowed).analyze(
                    entry, environment
                )
                for path, names in result.external.items():
                    if entry == file.path.resolve() or path == file.path.resolve():
                        external.setdefault(path, set()).update(names)
        except (TemplateSyntaxError, ValueError) as error:
            return [
                self.create_matcherror(
                    message=f"Cannot analyze this template's input interface: {error}",
                    filename=file,
                    tag=f"{self.id}[unresolved]",
                )
            ]
        return [
            self.create_matcherror(
                message=f"Pass external inputs through task-local tpl_ variables, or explicit macro arguments for context-free imports: {', '.join(sorted(names))}.",
                filename=Lintable(path),
            )
            for path, names in external.items()
        ]

    @override
    def matchtask(self, task: Task, file: Lintable | None = None) -> list[MatchError]:
        if (
            file is None
            or builtin_module_name(task["action"]["__ansible_module__"]) != "template"
        ):
            return []
        action = task["action"]
        source = literal(action.get("src"))
        if source is None:
            return []
        project = (
            Path(self.options.project_dir)
            if self.options and self.options.project_dir
            else file.path.parent
        )
        role = role_directory(file)
        roots = ([role / "templates"] if role else []) + [
            file.path.parent / "templates",
            file.path.parent,
            project / "templates",
        ]
        path = next(
            (
                root / source
                for root in roots
                if (root / source).is_file()
                and (root / source).resolve().is_relative_to(project.resolve())
            ),
            None,
        )
        if path is None or not self._allowed(path):
            return []
        options = {
            name: action[name]
            for name in (
                "variable_start_string",
                "variable_end_string",
                "block_start_string",
                "block_end_string",
                "comment_start_string",
                "comment_end_string",
                "trim_blocks",
                "lstrip_blocks",
            )
            if name in action
        }
        if any(
            isinstance(value, str) and literal(value) is None
            for value in options.values()
        ):
            return []
        try:
            environment = template_environment(
                path.read_text(encoding="utf-8"), options
            )
            result = TemplateGraph(template_root(path), self._allowed).analyze(
                path, environment
            )
        except (OSError, UnicodeError, TemplateSyntaxError, ValueError) as error:
            return [
                self.create_matcherror(
                    message=f"Cannot analyze template inputs: {error}",
                    filename=file,
                    data=task.raw_task,
                    tag=f"{self.id}[unresolved]",
                )
            ]
        variables = task.raw_task.get("vars", {})
        supplied = set(variables) if isinstance(variables, dict) else set()
        missing = result.required - supplied
        matches = []
        if missing:
            matches.append(
                self.create_matcherror(
                    message=f"Bind these statically required template inputs in task vars: {', '.join(sorted(missing))}.",
                    filename=file,
                    data=task.raw_task,
                    tag=f"{self.id}[missing]",
                )
            )
        if options and result.external:
            names = sorted(set().union(*result.external.values()))
            matches.append(
                self.create_matcherror(
                    message=f"Template delimiter overrides expose ambient inputs: {', '.join(names)}.",
                    filename=file,
                    data=task.raw_task,
                    tag=f"{self.id}[external]",
                )
            )
        return matches
