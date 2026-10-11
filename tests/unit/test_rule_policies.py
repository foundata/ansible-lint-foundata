# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Protect policy decisions at the installed rule callback boundary."""

from __future__ import annotations

from pathlib import Path

import pytest
from ansiblelint.file_utils import Lintable
from ansiblelint.utils import Task
from ruamel.yaml import YAML

from ansiblelint.rules.custom.foundata.foundata_file_mode import FoundataFileModeRule
from ansiblelint.rules.custom.foundata.foundata_handler_listen import (
    FoundataHandlerListenRule,
)

_LIST_MESSAGE = "Define listen as a nonempty list of lowercase topics."
_TOPIC_MESSAGE = "Listen topics must be nonempty, static lowercase strings."
_MODE_MESSAGE = "Use a complete absolute symbolic mode, such as u=rw,g=r,o=r."
_COMMENT_MESSAGE = "Document this mode with a matching inline # 0644 comment."


@pytest.mark.parametrize(
    ("listen", "messages", "fixed"),
    [
        pytest.param('"restart example"', [_LIST_MESSAGE], True, id="scalar"),
        pytest.param('" restart example "', [_LIST_MESSAGE], True, id="padded-scalar"),
        pytest.param(
            '"Restart Example"',
            [_LIST_MESSAGE, _TOPIC_MESSAGE],
            False,
            id="uppercase-scalar",
        ),
        pytest.param('""', [_LIST_MESSAGE, _TOPIC_MESSAGE], False, id="empty-scalar"),
        pytest.param('"  "', [_LIST_MESSAGE, _TOPIC_MESSAGE], False, id="whitespace"),
        pytest.param("null", [_LIST_MESSAGE, _TOPIC_MESSAGE], False, id="null"),
        pytest.param("123", [_LIST_MESSAGE, _TOPIC_MESSAGE], False, id="number"),
        pytest.param(None, [_LIST_MESSAGE, _TOPIC_MESSAGE], False, id="missing"),
        pytest.param(
            '"{{ topic }}"',
            [_LIST_MESSAGE, _TOPIC_MESSAGE],
            False,
            id="expression",
        ),
        pytest.param(
            '"{% if enabled %}restart example{% endif %}"',
            [_LIST_MESSAGE, _TOPIC_MESSAGE],
            False,
            id="statement",
        ),
        pytest.param("[]", [_TOPIC_MESSAGE], False, id="empty-list"),
        pytest.param(
            '["restart example", "Restart Example"]',
            [_TOPIC_MESSAGE],
            False,
            id="uppercase-list-item",
        ),
        pytest.param(
            '["restart example", 123]',
            [_TOPIC_MESSAGE],
            False,
            id="non-string-list-item",
        ),
        pytest.param(
            '["restart example", "reload example"]', [], False, id="valid-list"
        ),
    ],
)
def test_handler_diagnostics_and_fix_eligibility(
    tmp_path: Path, listen: str | None, messages: list[str], fixed: bool
) -> None:
    source = '- name: "Restart"\n  ansible.builtin.debug:\n    msg: "Restart"\n'
    if listen is not None:
        source += f"  listen: {listen}\n"
    lintable = Lintable(tmp_path / "handlers/main.yml", content=source, kind="handlers")
    task = Task(lintable.data[0], filename=lintable.name, kind="handlers")
    rule = FoundataHandlerListenRule()

    matches = rule.matchtask(task, lintable)

    assert [match.message for match in matches] == messages
    data = YAML(typ="rt").load(source)
    expected = YAML(typ="safe").load(source)
    if fixed:
        expected[0]["listen"] = [expected[0]["listen"]]
    for match in matches:
        match.yaml_path = [0]
        rule.transform(match, lintable, data)
        assert match.fixed is fixed
    assert data == expected


@pytest.mark.parametrize("placement", ["module", "args", "action", "local_action"])
@pytest.mark.parametrize(
    ("mode", "message"),
    [
        pytest.param('"u=rw,g=r,o=r" # 0644', None, id="matching-comment"),
        pytest.param('"u=rw,g=r,o=r" # 0644: public', None, id="comment-explanation"),
        pytest.param('"u=rw,g=r,o=r"', _COMMENT_MESSAGE, id="missing-comment"),
        pytest.param('"u=rw,g=r,o=r" # 0600', _COMMENT_MESSAGE, id="wrong-comment"),
        pytest.param(
            '"u=rw,g=r,o=r"\n# 0644', _COMMENT_MESSAGE, id="following-line-comment"
        ),
        pytest.param('"u+rw" # 0600', _MODE_MESSAGE, id="relative"),
        pytest.param('"preserve" # 0644', _MODE_MESSAGE, id="preserve"),
        pytest.param('"0644"', _MODE_MESSAGE, id="octal-string"),
        pytest.param("420", _MODE_MESSAGE, id="integer"),
        pytest.param("null", _MODE_MESSAGE, id="null"),
        pytest.param('"{{ example_mode }}" # 0600', None, id="expression"),
        pytest.param(
            '"{% if private %}u=rw,g=,o={% else %}u=rw,g=r,o=r{% endif %}"',
            None,
            id="statement",
        ),
    ],
)
def test_file_mode_diagnostics_and_source_locations(
    tmp_path: Path, placement: str, mode: str, message: str | None
) -> None:
    source = '- name: "File"\n'
    if placement in ("action", "local_action"):
        source += f"  {placement}:\n    module: ansible.builtin.file\n"
    else:
        source += '  ansible.builtin.file:\n    path: "/tmp/example"\n'
    if placement == "args":
        source += "  args:\n"
    mode_line = len(source.splitlines()) + 1
    source += f"    mode: {mode}\n"
    lintable = Lintable(tmp_path / "tasks/main.yml", content=source, kind="tasks")
    task = Task(lintable.data[0], filename=lintable.name)

    matches = FoundataFileModeRule().matchtask(task, lintable)

    assert [(match.message, match.lineno) for match in matches] == (
        [(message, mode_line)] if message is not None else []
    )
