"""Read-only access to round-trip YAML metadata for source-aware checks."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from ansiblelint.utils import task_in_list
from ansiblelint.yaml_utils import get_path_to_task
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ansible_lint_foundata.policy import builtin_module_name
from ansiblelint.rules import TransformMixin

if TYPE_CHECKING:
    from ansiblelint.file_utils import Lintable
    from ansiblelint.utils import Task


@lru_cache(maxsize=16)
def _load_source(content: str) -> object:
    # The content, not a filename, is the key so a fix cannot leave stale metadata.
    return YAML(typ="rt").load(content)


def source_task(file: Lintable, task: Task) -> CommentedMap | None:
    """Find a task's original mapping, including inline comments."""
    data = _load_source(file.content)
    if not isinstance(data, CommentedMap | CommentedSeq):
        return None
    path = get_path_to_task(file, task.line, data)
    result = TransformMixin.seek(path, data)
    return result if isinstance(result, CommentedMap) else None


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
