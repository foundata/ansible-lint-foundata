"""Check the explicit input interface of Jinja template files."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ansiblelint.skip_utils import get_rule_skips_from_line
from jinja2 import TemplateSyntaxError

from ansible_lint_foundata.expressions import template_environment
from ansible_lint_foundata.policy import template_names
from ansible_lint_foundata.rules import FoundataRule

if TYPE_CHECKING:
    from ansiblelint.errors import MatchError
    from ansiblelint.file_utils import Lintable


class FoundataTemplateInputsRule(FoundataRule):
    """Pass external template data through explicit tpl_ inputs."""

    id = "foundata-template-inputs"
    description = "Distinguish template-local bindings from ambient Ansible data."
    tags = ["opt-in", "idiom"]
    severity = "MEDIUM"
    version_changed = "1.0.0"
    link = "https://foundata.com/en/guidelines/ansible-playbooks/#templates"

    @override
    def matchlines(self, file: Lintable) -> list[MatchError]:
        if str(file.kind) != "jinja2":
            return []
        first_line = file.content.split("\n", 1)[0]
        if self.id in get_rule_skips_from_line(first_line, lintable=file):
            return []
        try:
            environment = template_environment(file.content)
            content = (
                file.content.partition("\n")[2]
                if file.content.startswith("#jinja2:")
                else file.content
            )
            names = template_names(content, environment=environment, strict=True)
        except (TemplateSyntaxError, ValueError) as error:
            return [
                self.create_matcherror(
                    message=f"Cannot analyze this template's input interface: {error}",
                    filename=file,
                    tag=f"{self.id}[unresolved]",
                )
            ]
        external = sorted(name for name in names if not name.startswith("tpl_"))
        if external:
            return [
                self.create_matcherror(
                    message=f"Pass these external inputs through task-local tpl_ variables: {', '.join(external)}.",
                    filename=file,
                )
            ]
        return []
