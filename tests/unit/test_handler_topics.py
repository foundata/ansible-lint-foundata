# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Protect handler namespace and migration contracts."""

from pathlib import Path

import pytest
from ansiblelint.file_utils import Lintable

from ansible_lint_foundata.policy import handler_topic_message
from ansible_lint_foundata.source import adjacent_comments, role_topic_prefix


@pytest.mark.parametrize(
    ("topic", "comment", "valid"),
    [
        ("nginx_web_restart_nginx", "", True),
        ("nginx_web_restart", "", False),
        ("restart_nginx", "", False),
        ("web_restart_services", "Shared broadcast for all web services.", True),
        ("Restart Nginx", "Migration alias; remove in 3.0.0.", True),
        ("restart", "Migration alias; remove in 3.0.0.", True),
        ("Restart Nginx", "Migration alias; remove someday.", False),
        ("Restart Nginx", "remove in 3.0.0.", False),
        ("{{ topic }}", "Migration alias; remove in 3.0.0.", False),
        ("", "Migration alias; remove in 3.0.0.", False),
    ],
)
def test_topic_exceptions_require_specific_comments(
    topic: str, comment: str, valid: bool
) -> None:
    assert (handler_topic_message(topic, "nginx_web_", comment) is None) is valid


def test_collection_prefix_and_item_comment_boundaries(tmp_path: Path) -> None:
    target = tmp_path / "roles/nginx/handlers/main.yml"
    target.parent.mkdir(parents=True)
    (tmp_path / "galaxy.yml").write_text("name: web\n", encoding="utf-8")
    content = '---\n- listen:\n    - "Restart Nginx" # Migration alias; remove in 3.0.0.\n    - "Other Topic"\n    # Shared broadcast for this stack.\n    - "web_restart_services"\n'
    file = Lintable(target, kind="handlers", content=content)
    assert role_topic_prefix(file) == "nginx_web_"
    assert "Migration alias" in adjacent_comments(file, 3)
    assert adjacent_comments(file, 4) == ""
    assert "Shared broadcast" in adjacent_comments(file, 6)
