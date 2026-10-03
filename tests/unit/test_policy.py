from __future__ import annotations

import pytest

from ansible_lint_foundata.policy import (
    absolute_mode,
    builtin_module_name,
    mode_comment_matches,
    ordered_task_keys,
    template_names,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("file", "file"),
        ("ansible.builtin.file", "file"),
        ("ansible.legacy.file", "file"),
        ("other.collection.file", None),
        ("ansible.builtin.other.file", None),
    ],
)
def test_builtin_namespaces_do_not_capture_other_collections(
    name: str, expected: str | None
) -> None:
    assert builtin_module_name(name) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("u=rw,g=r,o=r", 0o644),
        ("u=rwx,g=rx,o=", 0o750),
        ("a=rw", 0o666),
        ("ug=rw,o=", 0o660),
        ("u=,g=,o=", 0),
        ("u=rwxs,g=rx,o=rx", 0o4755),
        ("u=rwx,g=rxs,o=rx", 0o2755),
        ("u=rwx,g=rwx,o=rwxt", 0o1777),
        ("o=rx,g=rx,u=rwx", 0o755),
        ("a=rwxst", 0o7777),
        ("a=rw,u=r", 0o466),
        ("u=rw,g=r,o=r,u=x", 0o144),
        ("u=rw,g=r,o=s", 0o640),
        ("u=rwt,g=r,o=r", 0o644),
    ],
)
def test_absolute_modes_have_one_octal_value(text: str, expected: int) -> None:
    assert absolute_mode(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "0644",
        "preserve",
        "u+rw",
        "g-w",
        "u=rw",
        "=rw",
        "a=rX",
        "u=g,g=r,o=r",
        "au=r,g=r,o=r",
        "uu=rw,g=r,o=r",
        "",
        "u=rw,g=r,o=r,",
        "u=rw,g=r, o=r",
        "a=rwx+t",
    ],
)
def test_relative_ambiguous_or_incomplete_modes_are_rejected(text: str) -> None:
    assert absolute_mode(text) is None


@pytest.mark.parametrize(
    ("comment", "expected"),
    [
        ("# 0644", True),
        ("# 0644: public configuration", True),
        ("# 0600", False),
        ("# 644", False),
        ("# 06444", False),
        ("# See 0644", False),
        ("", False),
    ],
)
def test_octal_comment_must_start_with_the_matching_value(
    comment: str, expected: bool
) -> None:
    assert mode_comment_matches(0o644, comment) is expected


def test_all_ordinary_permission_combinations() -> None:
    for mode in range(0o1000):
        parts = []
        for user, shift in (("u", 6), ("g", 3), ("o", 0)):
            permissions = "".join(
                char
                for char, bit in (("r", 4), ("w", 2), ("x", 1))
                if (mode >> shift) & bit
            )
            parts.append(f"{user}={permissions}")
        assert absolute_mode(",".join(parts)) == mode


def test_task_order_leaves_undocumented_keys_in_their_slots() -> None:
    keys = ["name", "register", "check_mode", "when", "ansible.builtin.command", "tags"]
    expected = [
        "name",
        "ansible.builtin.command",
        "check_mode",
        "when",
        "register",
        "tags",
    ]
    assert ordered_task_keys(keys, "ansible.builtin.command") == expected
    assert ordered_task_keys(expected, "ansible.builtin.command") == expected


def test_task_order_keeps_block_keywords_last() -> None:
    assert ordered_task_keys(["block", "when", "name"], "block/always/rescue") == [
        "name",
        "when",
        "block",
    ]


def test_task_order_handles_old_loop_syntax_and_local_actions() -> None:
    assert ordered_task_keys(
        ["with_items", "local_action", "name", "loop_control"], "command"
    ) == [
        "name",
        "local_action",
        "loop_control",
        "with_items",
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Install {{ item['name'] }}", {"item"}),
        ("Install {{ package | ansible.builtin.default('item') }}", {"package"}),
        ("Install item", set()),
        ("Install {{", set()),
        ("{% if enabled %}Deploy {{ target }}{% endif %}", {"enabled", "target"}),
    ],
)
def test_template_names_parse_expressions_not_substrings(
    text: str, expected: set[str]
) -> None:
    assert template_names(text) == expected
