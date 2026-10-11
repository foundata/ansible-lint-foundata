# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Analyze literal Jinja composition with lexical include contexts, never render."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, TemplateSyntaxError, meta, nodes

from ansible_lint_foundata.expressions import template_environment
from ansible_lint_foundata.policy import template_names


def template_root(path: Path) -> Path:
    return next(
        (parent for parent in path.parents if parent.name == "templates"), path.parent
    )


def bindings(node: nodes.Node) -> set[str]:
    if isinstance(node, nodes.Name):
        return {node.name}
    return {
        name.name
        for name in node.find_all(nodes.Name)
        if name.ctx in {"store", "param"}
    }


def literal_targets(node: nodes.Expr) -> list[str]:
    if isinstance(node, nodes.Const) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, nodes.List) and all(
        isinstance(item, nodes.Const) and isinstance(item.value, str)
        for item in node.items
    ):
        return [item.value for item in node.items if isinstance(item, nodes.Const)]
    return []


@dataclass
class TemplateInterface:
    external: dict[Path, set[str]] = field(default_factory=dict)
    required: set[str] = field(default_factory=set)
    unresolved: set[str] = field(default_factory=set)


class TemplateGraph:
    """Track input requirements only on unconditional, statically known paths."""

    def __init__(
        self, root: Path, allowed: Callable[[Path], bool] | None = None
    ) -> None:
        self.root = root.resolve()
        self.allowed = allowed or (lambda _: True)
        self.result = TemplateInterface()
        self.visits = 0
        self._block_bindings: dict[Path, set[str]] = {}

    def analyze(
        self,
        path: Path,
        environment: Environment,
        inherited: frozenset[str] = frozenset(),
        active: frozenset[Path] = frozenset(),
        *,
        context: bool = True,
        required: bool = True,
    ) -> TemplateInterface:
        path = path.resolve()
        if (
            path in active
            or self.visits >= 128
            or not path.is_relative_to(self.root)
            or not self.allowed(path)
        ):
            self.result.unresolved.add(str(path))
            return self.result
        self.visits += 1
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            self.result.unresolved.add(str(path))
            return self.result
        # Ansible strips the root header, not headers in loader-provided fragments.
        if not active and content.startswith("#jinja2:"):
            content = content.partition("\n")[2]
        environment = environment.overlay()
        environment.globals = {**Environment().globals, **dict.fromkeys(inherited)}
        template = environment.parse(content)
        self._block_bindings[path] = self._exports(template.body)
        parent_names = self._parent_exports(template, environment, active | {path})
        environment.globals.update(dict.fromkeys(parent_names))
        names = template_names(content, environment=environment, strict=True)
        outside_reads: set[str] = set()
        for node in template.body:
            if not isinstance(node, nodes.Block):
                outside_reads.update(self._loads(node))
        names -= self._block_bindings[path] - outside_reads
        external = {
            name for name in names if not context or not name.startswith("tpl_")
        }
        if external:
            self.result.external.setdefault(path, set()).update(external)
        optional: set[str] = set()
        for node in template.find_all((nodes.Filter, nodes.Test)):
            if (
                isinstance(node, nodes.Filter)
                and node.name
                in {"default", "d", "ansible.builtin.default", "ansible.builtin.d"}
            ) or (
                isinstance(node, nodes.Test)
                and node.name
                in {
                    "defined",
                    "undefined",
                    "ansible.builtin.defined",
                    "ansible.builtin.undefined",
                }
            ):
                if node.node is not None:
                    optional.update(self._loads(node.node))
        self._walk(
            template.body,
            path,
            environment,
            set(inherited) | set(environment.globals),
            names - optional,
            active | {path},
            context,
            required,
        )
        return self.result

    @staticmethod
    def _exports(body: Sequence[nodes.Node]) -> set[str]:
        result: set[str] = set()
        for node in body:
            if isinstance(node, nodes.Assign | nodes.AssignBlock):
                result.update(bindings(node.target))
            elif isinstance(node, nodes.Macro):
                result.add(node.name)
            elif isinstance(node, nodes.Import):
                result.add(node.target)
            elif isinstance(node, nodes.FromImport):
                result.update(
                    name[1] if isinstance(name, tuple) else name for name in node.names
                )
        return result

    def _parent_exports(
        self, template: nodes.Template, env: Environment, active: frozenset[Path]
    ) -> set[str]:
        result: set[str] = set()
        if len(active) >= 128:
            return result
        for node in template.find_all(nodes.Extends):
            if not isinstance(node.template, nodes.Const) or not isinstance(
                node.template.value, str
            ):
                # A runtime parent may provide block locals of unknown provenance.
                for block in template.find_all(nodes.Block):
                    result.update(self._loads(block))
                continue
            parent = (self.root / node.template.value).resolve()
            if (
                parent in active
                or not parent.is_relative_to(self.root)
                or not self.allowed(parent)
            ):
                continue
            try:
                parsed = env.parse(parent.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, TemplateSyntaxError):
                continue
            result.update(self._exports(parsed.body))
            result.update(self._parent_exports(parsed, env, active | {parent}))
        return result

    @staticmethod
    def _loads(node: nodes.Node) -> set[str]:
        return (
            {node.name}
            if isinstance(node, nodes.Name) and node.ctx == "load"
            else set()
        ) | {child.name for child in node.find_all(nodes.Name) if child.ctx == "load"}

    def _require(
        self, node: nodes.Node, external: set[str], scope: set[str], enabled: bool
    ) -> None:
        if enabled:
            self.result.required.update(
                name
                for name in self._required_loads(node) & external - scope
                if name.startswith("tpl_")
            )

    def _required_loads(self, node: nodes.Node) -> set[str]:
        if isinstance(node, nodes.CondExpr):
            return self._required_loads(node.test)
        if isinstance(node, nodes.And | nodes.Or):
            return self._required_loads(node.left)
        names = (
            {node.name}
            if isinstance(node, nodes.Name) and node.ctx == "load"
            else set()
        )
        for child in node.iter_child_nodes():
            names.update(self._required_loads(child))
        return names

    def _walk(
        self,
        body: Sequence[nodes.Node],
        path: Path,
        env: Environment,
        scope: set[str],
        external: set[str],
        active: frozenset[Path],
        context: bool,
        required: bool,
    ) -> None:
        for node in body:
            if isinstance(
                node, nodes.Include | nodes.Import | nodes.FromImport | nodes.Extends
            ):
                targets = literal_targets(node.template)
                target = next(
                    (
                        self.root / name
                        for name in targets
                        if (self.root / name).is_file()
                    ),
                    None,
                )
                if target is None:
                    self.result.unresolved.add(f"{path}:{node.lineno}")
                else:
                    with_context = isinstance(node, nodes.Extends) or node.with_context
                    include_scope = (
                        scope | self._exports(body)
                        if isinstance(node, nodes.Extends)
                        else scope
                    )
                    self.analyze(
                        target,
                        env,
                        frozenset(include_scope) if with_context else frozenset(),
                        active,
                        context=context and with_context,
                        required=required and with_context,
                    )
                if isinstance(node, nodes.Import):
                    scope.add(node.target)
                elif isinstance(node, nodes.FromImport):
                    scope.update(
                        name[1] if isinstance(name, tuple) else name
                        for name in node.names
                    )
            elif isinstance(node, nodes.For):
                self._require(node.iter, external, scope, required)
                self._walk(
                    node.body,
                    path,
                    env,
                    scope | bindings(node.target) | {"loop"},
                    external,
                    active,
                    context,
                    False,
                )
                self._walk(
                    node.else_, path, env, set(scope), external, active, context, False
                )
            elif isinstance(node, nodes.Macro):
                scope.add(node.name)
                self._walk(
                    node.body,
                    path,
                    env,
                    scope
                    | {arg.name for arg in node.args}
                    | {"caller", "varargs", "kwargs"},
                    external,
                    active,
                    context,
                    False,
                )
            elif isinstance(node, nodes.If):
                self._require(node.test, external, scope, required)
                for branch in (node.body, node.elif_, node.else_):
                    self._walk(
                        branch, path, env, set(scope), external, active, context, False
                    )
            elif isinstance(node, nodes.With):
                for value in node.values:
                    self._require(value, external, scope, required)
                local = set().union(*(bindings(target) for target in node.targets))
                self._walk(
                    node.body,
                    path,
                    env,
                    scope | local,
                    external,
                    active,
                    context,
                    required,
                )
            elif isinstance(node, nodes.Assign):
                self._require(node.node, external, scope, required)
                scope.update(bindings(node.target))
            elif isinstance(node, nodes.AssignBlock):
                self._walk(
                    node.body,
                    path,
                    env,
                    set(scope),
                    external,
                    active,
                    context,
                    required,
                )
                scope.update(bindings(node.target))
            elif isinstance(node, nodes.Block):
                # Overrides and super() determine which block executes at runtime.
                self._walk(
                    node.body,
                    path,
                    env,
                    scope | self._block_bindings[path] | {"super", "self"},
                    external,
                    active,
                    context,
                    False,
                )
            else:
                self._require(node, external, scope, required)


def template_entry_points(path: Path, allowed: Callable[[Path], bool]) -> list[Path]:
    """Resolve bounded literal parent chains, retaining each caller's context."""
    root = template_root(path)
    parents: dict[Path, set[Path]] = {}
    for index, parent in enumerate(root.rglob("*.j2")):
        if index >= 128:
            break
        if not allowed(parent):
            continue
        try:
            content = parent.read_text(encoding="utf-8")
            env = template_environment(content)
            template = env.parse(
                content.partition("\n")[2]
                if content.startswith("#jinja2:")
                else content
            )
            references = meta.find_referenced_templates(template)
            if references is not None:
                for name in references:
                    if name is not None:
                        parents.setdefault((root / name).resolve(), set()).add(
                            parent.resolve()
                        )
        except (OSError, UnicodeError, TemplateSyntaxError, ValueError):
            continue
    pending = [path.resolve()]
    visited: set[Path] = set()
    roots: set[Path] = set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        if current in parents:
            pending.extend(parents[current])
        else:
            roots.add(current)
    return sorted(roots or {path.resolve()})
