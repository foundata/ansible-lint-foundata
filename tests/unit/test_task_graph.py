"""Bound graph traversal independently of stock recursive file discovery."""

import os
import sys
from pathlib import Path

import pytest
from ansiblelint.app import App
from ansiblelint.config import Options
from ansiblelint.file_utils import Lintable
from ansiblelint.runner import Runner

from ansible_lint_foundata.task_graph import TaskGraph
from ansiblelint.rules import RulesCollection


def resolver(
    root: Path, monkeypatch: pytest.MonkeyPatch, excluded: list[str] | None = None
) -> Runner:
    for name in tuple(os.environ):
        if name.startswith(("ANSIBLE_", "ANSIBLELINT_")):
            monkeypatch.delenv(name)
    monkeypatch.setenv(
        "PATH", str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    )
    config = root / "ansible.cfg"
    config.write_text("[defaults]\n", encoding="utf-8")
    monkeypatch.setenv("ANSIBLE_CONFIG", str(config))
    return Runner(
        rules=RulesCollection(App(Options(project_dir=str(root), offline=True))),
        project_dir=str(root),
        exclude_paths=excluded or [],
    )


def test_cycle_is_bounded_and_not_a_closed_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = tmp_path / "a.yml"
    second = tmp_path / "b.yml"
    first.write_text('- ansible.builtin.import_tasks: "b.yml"\n', encoding="utf-8")
    second.write_text('- ansible.builtin.import_tasks: "a.yml"\n', encoding="utf-8")
    graph = TaskGraph(tmp_path, resolver(tmp_path, monkeypatch))
    graph.add_file(Lintable(first, kind="tasks"))
    assert len(graph.entries) == 2
    assert not graph.closed


def test_excluded_or_outside_files_remain_unresolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "external.yml"
    outside.write_text('- ansible.builtin.debug: {msg: "Example"}\n', encoding="utf-8")
    excluded = project / "ignored.yml"
    excluded.write_text(outside.read_text(), encoding="utf-8")
    graph = TaskGraph(
        project,
        resolver(project, monkeypatch, [str(excluded)]),
    )
    graph.add_file(Lintable(outside, kind="tasks"))
    graph.add_file(Lintable(excluded, kind="tasks"))
    assert not graph.closed
    assert graph.entries == []
