"""Shared integration behavior for the concrete discovery classes."""

from typing import override

from ansiblelint.rules import AnsibleLintRule


class FoundataRule(AnsibleLintRule):
    """Link diagnostics to the guideline rather than stock rule documentation."""

    @property
    @override
    def url(self) -> str:
        return self.link
