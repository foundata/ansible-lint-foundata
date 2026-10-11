# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded, read-only traversal of literal local role and task references."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ansiblelint.file_utils import Lintable
from ansiblelint.utils import Task, task_in_list
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from ansible_lint_foundata.policy import builtin_module_name
from ansible_lint_foundata.source import role_directory

if TYPE_CHECKING:
    from ansiblelint.runner import Runner


def literal(value: object) -> str | None:
    """Return an untemplated reference, not a best-effort expansion."""
    return (
        value
        if isinstance(value, str)
        and value
        and not any(marker in value for marker in ("{{", "{%"))
        else None
    )


@dataclass(frozen=True)
class TaskEntry:
    file: Lintable
    task: Task
    outer_loops: frozenset[str] = frozenset()


def loop_variables(task: Task) -> frozenset[str]:
    """Return statically named loop bindings, including an explicit index."""
    if "loop" not in task.raw_task and not any(
        key.startswith("with_") for key in task.raw_task
    ):
        return frozenset()
    control = task.raw_task.get("loop_control", {})
    if not isinstance(control, dict):
        return frozenset()
    names = [control.get("loop_var", "item"), control.get("index_var")]
    return frozenset(name for value in names if (name := literal(value)) is not None)


@dataclass
class TaskGraph:
    """A per-entry-point graph; unresolved edges prevent missing-target claims."""

    root: Path
    resolver: Runner
    closed: bool = True
    entries: list[TaskEntry] = field(default_factory=list)
    topics: set[str] = field(default_factory=set)
    handler_names: set[str] = field(default_factory=set)
    _visited: set[tuple[Path, str, frozenset[str]]] = field(default_factory=set)
    _roles: set[tuple[Path, frozenset[str], str | None, str | None]] = field(
        default_factory=set
    )

    def allowed(self, file: Lintable) -> bool:
        path = file.path.resolve()
        if (
            not path.is_relative_to(self.root.resolve())
            or self.resolver.is_excluded(file)
            or not path.is_file()
        ):
            self.closed = False
            return False
        return True

    def add_file(
        self,
        file: Lintable,
        loops: frozenset[str] = frozenset(),
        active: frozenset[Path] = frozenset(),
    ) -> None:
        path = file.path.resolve()
        key = (path, str(file.kind), loops)
        if path in active or len(self._visited) >= 128 or len(self.entries) >= 5000:
            self.closed = False
            return
        if key in self._visited or not self.allowed(file):
            return
        self._visited.add(key)
        self.add_tasks(file, file.data, str(file.kind), loops, active | {path})

    def add_tasks(
        self,
        file: Lintable,
        data: object,
        kind: str,
        loops: frozenset[str],
        active: frozenset[Path],
    ) -> None:
        if not isinstance(data, list):
            self.closed = False
            return
        for task in task_in_list(data, kind=kind, file=file):
            if task.error is not None or len(self.entries) >= 5000:
                self.closed = False
                return
            self.entries.append(TaskEntry(file, task, loops))
            action = task["action"]
            module = builtin_module_name(action["__ansible_module__"])
            if task.kind == "handlers" and module != "import_tasks":
                name = literal(task.raw_task.get("name"))
                if name:
                    self.handler_names.add(name)
                    role = role_directory(file)
                    if role:
                        self.handler_names.add(f"{role.name} : {name}")
                else:
                    self.closed = False
                topics = task.raw_task.get("listen", [])
                for topic in topics if isinstance(topics, list) else [topics]:
                    if (value := literal(topic)) is not None:
                        self.topics.add(value)
                    else:
                        self.closed = False
            nested_loops = loops | loop_variables(task)
            if module in {"include_tasks", "import_tasks"}:
                target = literal(action.get("file", action.get("_raw_params")))
                if target is None:
                    self.closed = False
                    continue
                child_kind: Literal["handlers", "tasks"] = (
                    "handlers"
                    if task.kind == "handlers" and module == "import_tasks"
                    else "tasks"
                )
                children = self.resolver.play_children(
                    file, ("import_tasks", target), child_kind, str(file.path.parent)
                )
                if not children:
                    self.closed = False
                for child in children:
                    self.add_file(child, nested_loops, active)
            elif module in {"include_role", "import_role"}:
                self.add_role(file, action, nested_loops, active)

    def add_role(
        self,
        parent: Lintable,
        value: object,
        loops: frozenset[str],
        active: frozenset[Path],
    ) -> None:
        settings = {"name": value} if isinstance(value, str) else value
        if not isinstance(settings, dict):
            self.closed = False
            return
        name = literal(settings.get("role", settings.get("name")))
        if name is None:
            self.closed = False
            return
        parts = name.split(".")
        candidates = [self.root / "roles" / name, parent.path.parent / "roles" / name]
        if len(parts) == 3:
            namespace, collection, role = parts
            candidates.insert(
                0,
                self.root
                / "collections/ansible_collections"
                / namespace
                / collection
                / "roles"
                / role,
            )
        root = next(
            (
                path.resolve()
                for path in candidates
                if path.is_dir() and path.resolve().is_relative_to(self.root.resolve())
            ),
            None,
        )
        if root is None:
            self.closed = False
            return
        self.add_role_root(parent, root, settings, loops, active)

    def add_role_root(
        self,
        parent: Lintable,
        root: Path,
        settings: dict[str, object],
        loops: frozenset[str],
        active: frozenset[Path],
    ) -> None:
        if root in active:
            self.closed = False
            return
        key = (
            root,
            loops,
            literal(settings.get("tasks_from", "main")),
            literal(settings.get("handlers_from", "main")),
        )
        if key in self._roles:
            return
        if len(self._roles) >= 128:
            self.closed = False
            return
        self._roles.add(key)
        active = active | {root}
        for kind in ("handlers", "tasks"):
            stem = literal(settings.get(f"{kind}_from", "main"))
            if stem is None:
                self.closed = False
                continue
            choices = [
                root / kind / (stem + suffix) for suffix in (".yml", ".yaml", "")
            ]
            path = next(
                (candidate for candidate in choices if candidate.is_file()), None
            )
            if path is not None:
                self.add_file(Lintable(path, kind=kind, parent=parent), loops, active)
            elif stem != "main":
                self.closed = False
        for name in ("main.yml", "main.yaml"):
            metadata = root / "meta" / name
            if not metadata.is_file():
                continue
            if not self.allowed(Lintable(metadata, kind="meta")):
                return
            try:
                data = YAML(typ="safe").load(metadata.read_text(encoding="utf-8"))
            except (OSError, YAMLError):
                self.closed = False
                return
            dependencies = (
                data.get("dependencies", []) if isinstance(data, dict) else []
            )
            if not isinstance(dependencies, list):
                self.closed = False
                return
            for dependency in dependencies:
                self.add_role(parent, dependency, loops, active)


def graphs_for_file(file: Lintable, root: Path, resolver: Runner) -> list[TaskGraph]:
    """Keep play handler namespaces separate and role callers explicitly open."""
    if file.kind == "playbook" and isinstance(file.data, list):
        graphs = []
        for play in file.data:
            if not isinstance(play, dict):
                continue
            graph = TaskGraph(root, resolver)
            for role in play.get("roles", []):
                graph.add_role(file, role, frozenset(), frozenset())
            graph.add_tasks(
                file, [play], "playbook", frozenset(), frozenset({file.path.resolve()})
            )
            graphs.append(graph)
        return graphs
    graph = TaskGraph(root, resolver, closed=False)
    role = role_directory(file)
    if role is not None:
        graph.add_role_root(file, role, {}, frozenset(), frozenset())
    graph.add_file(file)
    return [graph]
