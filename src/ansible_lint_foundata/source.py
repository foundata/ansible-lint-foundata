# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only access to round-trip YAML metadata for source-aware checks."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from ansiblelint.file_utils import Lintable, find_role_dir
from ansiblelint.utils import task_in_list
from ansiblelint.yaml_utils import get_path_to_task
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError
from ruamel.yaml.tokens import CommentToken

from ansible_lint_foundata.policy import builtin_module_name
from ansiblelint.rules import TransformMixin

if TYPE_CHECKING:
    from ansiblelint.utils import Task


@lru_cache(maxsize=16)
def _load_source(content: str) -> object:
    # The content, not a filename, is the key so a fix cannot leave stale metadata.
    parser = YAML(typ="rt")
    parser.preserve_quotes = True
    return parser.load(content)


def source_task(file: Lintable, task: Task) -> CommentedMap | None:
    """Find a task's original mapping, including inline comments."""
    data = _load_source(file.content)
    if not isinstance(data, CommentedMap | CommentedSeq):
        return None
    path = get_path_to_task(file, task.line, data)
    result = TransformMixin.seek(path, data)
    return result if isinstance(result, CommentedMap) else None


def variable_bindings(
    file: Lintable, task: Task
) -> list[tuple[Lintable, CommentedMap]]:
    """Collect literal declarations without simulating Ansible precedence."""
    data = _load_source(file.content)
    if not isinstance(data, CommentedMap | CommentedSeq):
        return []
    result: list[tuple[Lintable, CommentedMap]] = []
    files: set[Path] = set()
    path = get_path_to_task(file, task.line, data)
    for length in range(len(path) + 1):
        parent = TransformMixin.seek(path[:length], data)
        if not isinstance(parent, CommentedMap):
            continue
        variables = parent.get("vars")
        if isinstance(variables, CommentedMap):
            result.append((file, variables))
        vars_files = parent.get("vars_files", [])
        for value in vars_files if isinstance(vars_files, list) else [vars_files]:
            if isinstance(value, str) and not any(
                marker in value for marker in ("{{", "{%")
            ):
                candidate = (file.path.parent / value).resolve()
                if candidate.is_relative_to(file.path.parent.resolve()):
                    files.add(candidate)
    role = role_directory(file)
    if role is not None:
        files.update(
            role / folder / name
            for folder in ("defaults", "vars")
            for name in ("main.yml", "main.yaml")
        )
    for source in sorted(files):
        if not source.is_file():
            continue
        try:
            definition = Lintable(source)
            variables = _load_source(definition.content)
        except (OSError, UnicodeError, YAMLError):
            continue
        if isinstance(variables, CommentedMap):
            result.append((definition, variables))
    return result


def inline_comment(mapping: CommentedMap, key: str) -> str:
    tokens = mapping.ca.items.get(key)
    return tokens[2].value.splitlines()[0] if tokens and tokens[2] else ""


def role_directory(file: Lintable) -> Path | None:
    """Identify conventional collection roles and standalone role roots."""
    role = find_role_dir(file.path.resolve())
    if role is not None:
        return role
    for parent in file.path.resolve().parents:
        if parent.name in {"tasks", "handlers", "vars", "defaults"}:
            root = parent.parent
            if (root / "meta/main.yml").is_file() or (
                root / "meta/main.yaml"
            ).is_file():
                return root
    return None


def role_topic_prefix(file: Lintable) -> str | None:
    """Resolve conventional role[_collection]_ public prefixes when available."""
    root = role_directory(file)
    if root is None:
        return None
    prefix = root.name
    if root.parent.name == "roles":
        collection = root.parent.parent
        galaxy = collection / "galaxy.yml"
        if galaxy.is_file():
            try:
                data = YAML(typ="safe").load(galaxy.read_text(encoding="utf-8"))
            except (OSError, YAMLError):
                return None
            if not isinstance(data, dict) or not isinstance(data.get("name"), str):
                return None
            prefix += "_" + data["name"]
        elif collection.parent.parent.name == "ansible_collections":
            prefix += "_" + collection.name
    return prefix + "_"


@lru_cache(maxsize=16)
def _comment_lines(content: str) -> dict[int, str]:
    """Read scanner comment tokens, never hash characters inside YAML scalars."""
    result: dict[int, str] = {}
    for token in YAML(typ="rt").scan(content):
        pending = list(token.comment or [])
        while pending:
            comment = pending.pop()
            if isinstance(comment, list):
                pending.extend(comment)
            elif isinstance(comment, CommentToken):
                for offset, text in enumerate(comment.value.splitlines()):
                    if text.lstrip().startswith("#"):
                        result[comment.start_mark.line + offset + 1] = text.lstrip()[
                            1:
                        ].strip()
    return result


def adjacent_comments(file: Lintable, line: int) -> str:
    """Return inline and immediately preceding standalone comments for a line."""
    comments = _comment_lines(file.content)
    lines = file.content.splitlines()
    selected = [comments.get(line, "")]
    index = line - 2
    while index >= 0 and lines[index].lstrip().startswith("#"):
        selected.append(comments.get(index + 1, ""))
        index -= 1
    return " ".join(reversed(selected)).strip()


def key_origin(mapping: CommentedMap, key: str) -> CommentedMap | None:
    """Find the defining mapping, respecting YAML merge precedence and cycles."""
    pending = [mapping]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        if any(name == key for name, _ in current.non_merged_items()):
            return current
        for merged in reversed(current.merge):
            # ruamel.yaml before 0.18.15 stores (position, mapping) pairs.
            if isinstance(merged, tuple):
                merged = merged[1]
            if isinstance(merged, CommentedMap):
                pending.append(merged)
    return None


def handler_file_context(file: Lintable) -> bool | None:
    """Resolve literal include/import edges in the linter's ancestry chain.

    File-kind hints can lose the distinction at nested imports. A static
    handler context takes precedence when the same parent also includes the
    file dynamically. Unknown edges leave the upstream hint authoritative.
    """
    current = file
    visited: set[str] = set()
    while current.parent is not None and str(current.path) not in visited:
        visited.add(str(current.path))
        parent = current.parent
        if parent.kind not in {"tasks", "handlers", "playbook"}:
            break
        imports: list[bool] = []
        included = False
        for task in task_in_list(parent.data, kind=parent.kind, file=parent):
            if task.error is not None:
                continue
            action = task["action"]
            module = builtin_module_name(action["__ansible_module__"])
            target = action.get("file", action.get("_raw_params"))
            if module not in {"include_tasks", "import_tasks"} or not isinstance(
                target, str
            ):
                continue
            if (parent.path.parent / target).resolve() == current.path.resolve():
                if module == "import_tasks":
                    imports.append(task.kind == "handlers")
                else:
                    included = True
        if not imports:
            return False if included else None
        if parent.kind == "playbook":
            return any(imports)
        current = parent
    if current is not file and current.parent is None:
        return current.kind == "handlers"
    return None
