from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from ansiblelint.constants import RC
from ruamel.yaml import YAML

from ansible_lint_foundata import RULE_IDS

pytestmark = pytest.mark.integration


def run_lint(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    config = root / "ansible.cfg"
    config.write_text("[defaults]\nlocalhost_warning = false\n", encoding="utf-8")
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("ANSIBLE_", "ANSIBLELINT_"))
    }
    env.update(
        {
            "ANSIBLE_CONFIG": str(config),
            "ANSIBLE_LOCAL_TEMP": str(root / ".ansible-tmp"),
            "ANSIBLE_COLLECTIONS_PATH": str(root / "collections"),
            "ANSIBLE_ROLES_PATH": str(root / "roles"),
            "ANSIBLE_COLLECTIONS_SCAN_SYS_PATH": "true",
            "ANSIBLE_LINT_NODEPS": "1",
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "ansiblelint", "--offline", *arguments],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def configure(root: Path, *rule_ids: str, profile: str = "min") -> None:
    (root / "tasks").mkdir(exist_ok=True)
    (root / ".ansible-lint").write_text(
        json.dumps(
            {
                "profile": profile,
                "enable_list": list(rule_ids),
            }
        ),
        encoding="utf-8",
    )


def diagnostics(result: subprocess.CompletedProcess[str]) -> list[dict[str, Any]]:
    assert result.returncode in (0, 2), result.stdout + result.stderr
    parsed: list[dict[str, Any]] = json.loads(result.stdout)
    assert all("internal-error" not in item["check_name"] for item in parsed), parsed
    assert "Ignored exception" not in result.stderr, result.stderr
    return parsed


def test_installed_discovery_includes_every_rule_and_stock_rules(
    tmp_path: Path,
) -> None:
    result = run_lint(tmp_path, "--list-rules", "--format", "brief")
    assert result.returncode == 0, result.stderr
    for rule_id in (*RULE_IDS, "yaml", "fqcn"):
        assert f"- {rule_id} " in result.stdout


@pytest.mark.parametrize(
    ("profile", "configure_rules"),
    [("min", False), ("production", False), ("production", True)],
)
def test_opt_in_and_production_profile(
    tmp_path: Path, profile: str, configure_rules: bool
) -> None:
    (tmp_path / "tasks").mkdir(exist_ok=True)
    if configure_rules:
        configure(tmp_path, "foundata-condition-list", profile=profile)
    elif profile == "production":
        configure(tmp_path, profile=profile)
    (tmp_path / "tasks/main.yml").write_text(
        '---\n- name: "Example"\n  ansible.builtin.debug:\n    msg: "Example"\n  when: true\n',
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", "tasks/main.yml"))
    custom = [item for item in matches if item["check_name"].startswith("foundata-")]
    assert bool(custom) is configure_rules


@pytest.mark.parametrize(
    ("rule_id", "filename", "source", "count"),
    [
        (
            "foundata-condition-list",
            "tasks/main.yml",
            '- name: "Example"\n  ansible.builtin.debug:\n    msg: "Hi"\n  when: true\n  changed_when: false\n',
            2,
        ),
        (
            "foundata-condition-list",
            "tasks/main.yml",
            '- name: "Example"\n  ansible.builtin.debug:\n    msg: "Hi"\n  when:\n    - true\n',
            0,
        ),
        (
            "foundata-handler-listen",
            "handlers/main.yml",
            '- name: "Restart"\n  ansible.builtin.debug:\n    msg: "Restart"\n  listen:\n    - "Restart MyApp"\n',
            1,
        ),
        (
            "foundata-handler-listen",
            "handlers/main.yml",
            '- name: "Restart"\n  ansible.builtin.debug:\n    msg: "Restart"\n  listen:\n    - "restart myapp"\n',
            0,
        ),
        (
            "foundata-handler-listen",
            "playbook.yml",
            '- name: "Example"\n  hosts: "localhost"\n  handlers:\n    - name: "Restart"\n      ansible.builtin.debug:\n        msg: "Restart"\n      listen: "restart myapp"\n',
            1,
        ),
        (
            "foundata-file-mode",
            "tasks/main.yml",
            '- name: "File"\n  ansible.builtin.file:\n    path: "/tmp/example"\n    mode: "u=rw,g=r,o=r" # 0644\n',
            0,
        ),
        (
            "foundata-file-mode",
            "tasks/main.yml",
            '- name: "File"\n  ansible.builtin.file:\n    path: "/tmp/example"\n    mode: "u=rw,g=r,o=r" # 0600\n',
            1,
        ),
        (
            "foundata-file-mode",
            "tasks/main.yml",
            '- name: "File"\n  ansible.builtin.file:\n    path: "/tmp/example"\n    mode: "u+rw" # 0600\n',
            1,
        ),
        (
            "foundata-file-mode",
            "tasks/main.yml",
            '- name: "File"\n  ansible.builtin.file:\n    path: "/tmp/example"\n  args:\n    mode: "0644"\n',
            1,
        ),
        (
            "foundata-file-mode",
            "tasks/main.yml",
            '- name: "File"\n  ansible.builtin.file:\n    path: "/tmp/example"\n    mode: "{{ example_mode }}"\n',
            0,
        ),
        (
            "foundata-debug-verbosity",
            "tasks/main.yml",
            '- name: "Example"\n  ansible.builtin.debug:\n    msg: "Hi"\n',
            1,
        ),
        (
            "foundata-debug-verbosity",
            "tasks/main.yml",
            '- name: "Example"\n  debug:\n    msg: "Hi"\n    verbosity: 0\n',
            0,
        ),
        (
            "foundata-no-end-play",
            "tasks/main.yml",
            '- name: "Stop"\n  ansible.builtin.meta: "end_play"\n',
            1,
        ),
        (
            "foundata-no-end-play",
            "tasks/main.yml",
            '- name: "Stop"\n  ansible.builtin.meta: "end_host"\n',
            0,
        ),
        (
            "foundata-task-name",
            "tasks/main.yml",
            '- name: "Install {{ package }}"\n  ansible.builtin.debug:\n    msg: "Hi"\n  loop: []\n  loop_control:\n    loop_var: "package"\n',
            1,
        ),
        (
            "foundata-task-name",
            "tasks/main.yml",
            '- name: "Install {{ package }}"\n  ansible.builtin.debug:\n    msg: "Hi"\n  loop: []\n',
            0,
        ),
        (
            "foundata-task-name",
            "playbook.yml",
            '- name: "Deploy {{ target }}"\n  hosts: "localhost"\n  tasks: []\n',
            1,
        ),
        (
            "foundata-task-order",
            "tasks/main.yml",
            '- name: "Example"\n  register: result\n  ansible.builtin.debug:\n    msg: "Hi"\n  when:\n    - true\n',
            1,
        ),
    ],
    ids=[
        "scalar-conditions",
        "list-condition",
        "legacy-alias",
        "lowercase-topic",
        "inline-handler",
        "absolute-mode",
        "wrong-comment",
        "relative-mode",
        "args-mode",
        "dynamic-mode",
        "missing-verbosity",
        "explicit-verbosity",
        "end-play",
        "end-host",
        "loop-name",
        "non-loop-name",
        "play-name",
        "task-order",
    ],
)
def test_rule_findings(
    tmp_path: Path, rule_id: str, filename: str, source: str, count: int
) -> None:
    configure(tmp_path, rule_id)
    target = tmp_path / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("---\n" + source, encoding="utf-8")
    matches = diagnostics(run_lint(tmp_path, "--format", "json", filename))
    assert len([item for item in matches if item["check_name"] == rule_id]) == count, (
        matches
    )
    for item in matches:
        if item["check_name"] == rule_id:
            assert item["url"].startswith(
                "https://foundata.com/en/guidelines/ansible-playbooks/#"
            )


def test_sarif_links_to_the_guideline(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-debug-verbosity")
    (tmp_path / "tasks/main.yml").write_text(
        '- name: "Example"\n  ansible.builtin.debug:\n    msg: "Example"\n',
        encoding="utf-8",
    )
    result = run_lint(tmp_path, "--format", "sarif", "tasks/main.yml")
    assert result.returncode == 2, result.stdout + result.stderr
    rules = json.loads(result.stdout)["runs"][0]["tool"]["driver"]["rules"]
    assert rules[0]["helpUri"] == (
        "https://foundata.com/en/guidelines/ansible-playbooks/#misc"
    )


def test_fixes_preserve_values_comments_and_reach_a_fixed_point(tmp_path: Path) -> None:
    configure(
        tmp_path,
        "foundata-condition-list",
        "foundata-task-order",
        "foundata-handler-listen",
    )
    target = tmp_path / "handlers" / "main.yml"
    target.parent.mkdir()
    target.write_text(
        """---
- name: "Example"
  listen: "restart example" # Public topic
  register: result # Keep this comment
  ansible.builtin.debug:
    msg: "A quoted # value"
  when: >-
    first is defined or
    second is defined
  changed_when: false # Read only
""",
        encoding="utf-8",
    )
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 2, result.stdout + result.stderr
    first = target.read_text(encoding="utf-8")
    task = YAML(typ="safe").load(first)[0]
    assert task["listen"] == ["restart example"]
    assert task["when"] == ["first is defined or second is defined"]
    assert task["changed_when"] == [False]
    assert task["ansible.builtin.debug"]["msg"] == "A quoted # value"
    for comment in ("Public topic", "Keep this comment", "Read only"):
        assert comment in first
    assert list(task) == [
        "name",
        "listen",
        "register",
        "ansible.builtin.debug",
        "when",
        "changed_when",
    ]
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 2, result.stdout + result.stderr
    assert target.read_text(encoding="utf-8") == first


def test_noqa_and_skip_list_keep_standard_suppression_behavior(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-condition-list")
    (tmp_path / "tasks/main.yml").write_text(
        """---
- name: "Example" # noqa: foundata-condition-list
  ansible.builtin.debug:
    msg: "Hi"
  when: true
""",
        encoding="utf-8",
    )
    assert diagnostics(run_lint(tmp_path, "--format", "json", "tasks/main.yml")) == []
    (tmp_path / "tasks/main.yml").write_text(
        """---
- name: "Example"
  ansible.builtin.debug:
    msg: "Hi"
  when: true
""",
        encoding="utf-8",
    )
    assert (
        diagnostics(
            run_lint(
                tmp_path,
                "--skip-list",
                "foundata-condition-list",
                "--format",
                "json",
                "tasks/main.yml",
            )
        )
        == []
    )


@pytest.mark.parametrize("suppress_preserve", [False, True])
def test_artifact_mode_exception_is_task_local(
    tmp_path: Path, suppress_preserve: bool
) -> None:
    configure(tmp_path, "foundata-file-mode")
    suppression = " # noqa: foundata-file-mode" if suppress_preserve else ""
    (tmp_path / "tasks/main.yml").write_text(
        f"""---
# Keep the release artifact's executable bits for packaging.
- name: "Stage release artifact"{suppression}
  ansible.builtin.copy:
    src: "release/"
    dest: "/srv/build/staging/"
    mode: "preserve"

- name: "Set configuration permissions"
  ansible.builtin.file:
    path: "/etc/example.conf"
    mode: "u+rw" # 0600
""",
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", "tasks/main.yml"))
    assert all(item["check_name"] == "foundata-file-mode" for item in matches)
    lines = {item["location"]["lines"]["begin"] for item in matches}
    assert lines == ({12} if suppress_preserve else {7, 12})


def test_nested_tasks_and_mode_source_location(tmp_path: Path) -> None:
    configure(
        tmp_path,
        "foundata-condition-list",
        "foundata-file-mode",
        "foundata-no-end-play",
    )
    (tmp_path / "tasks" / "main.yml").write_text(
        """---
- name: "Outer"
  when: true
  block:
    - name: "File"
      ansible.builtin.file:
        path: "/tmp/example"
        mode: "u=rw,g=r,o=r" # 0600
  rescue:
    - name: "Stop"
      ansible.builtin.meta: "end_play"
""",
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", "tasks/main.yml"))
    assert {item["check_name"] for item in matches} == {
        "foundata-condition-list",
        "foundata-file-mode",
        "foundata-no-end-play",
    }
    mode = next(item for item in matches if item["check_name"] == "foundata-file-mode")
    assert mode["location"]["lines"]["begin"] == 8


def test_unsafe_fixes_do_not_rename_topics_or_change_permissions(
    tmp_path: Path,
) -> None:
    configure(tmp_path, "foundata-handler-listen", "foundata-file-mode")
    target = tmp_path / "handlers" / "main.yml"
    target.parent.mkdir()
    target.write_text(
        """---
- name: "Protect file"
  ansible.builtin.file:
    path: "/tmp/example"
    mode: "u+rw" # 0644
  listen:
    - "Restart MyApp"
""",
        encoding="utf-8",
    )
    before = YAML(typ="safe").load(target.read_text(encoding="utf-8"))
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 2, result.stdout + result.stderr
    assert YAML(typ="safe").load(target.read_text(encoding="utf-8")) == before


def test_stock_rules_and_custom_fixes_coexist_under_production(tmp_path: Path) -> None:
    configure(tmp_path, *RULE_IDS, profile="production")
    target = tmp_path / "tasks" / "main.yml"
    target.write_text(
        """---
- name: "Example"
  ansible.builtin.debug:
    msg: "Example"
    verbosity: 1
  changed_when: false
  register: result
""",
        encoding="utf-8",
    )
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == RC.FIXED_VIOLATIONS, result.stdout + result.stderr
    assert diagnostics(run_lint(tmp_path, "--format", "json", str(target))) == []
    before = target.read_bytes()
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 0, result.stdout + result.stderr
    assert target.read_bytes() == before


def test_loop_index_is_not_allowed_in_a_task_name(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-task-name")
    (tmp_path / "tasks" / "main.yml").write_text(
        """---
- name: "Process entry {{ position }}"
  ansible.builtin.debug:
    msg: "Entry"
  loop: []
  loop_control:
    index_var: "position"
""",
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", "tasks/main.yml"))
    assert [item["check_name"] for item in matches] == ["foundata-task-name"]


@pytest.mark.parametrize("condition", ["true", "\n    - true"])
def test_order_diagnostics_preserve_the_next_tasks_heading(
    tmp_path: Path, condition: str
) -> None:
    configure(tmp_path, "foundata-task-order", "foundata-condition-list")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        '---\n- name: "First"\n'
        "  register: result # Registration comment\n"
        '  ansible.builtin.debug:\n    msg: "First"\n'
        f"  when: {condition} # Condition comment\n\n"
        "# Heading for second task\n"
        '- name: "Second"\n'
        '  ansible.builtin.debug:\n    msg: "Second"\n',
        encoding="utf-8",
    )
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 2, result.stdout + result.stderr
    fixed = target.read_text(encoding="utf-8")
    assert fixed.index("register: result") < fixed.index("# Condition comment")
    assert fixed.index("register: result") < fixed.index("# Heading for second task")
    assert '# Heading for second task\n- name: "Second"' in fixed
    assert "# Registration comment" in fixed
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 2, result.stdout + result.stderr
    assert target.read_text(encoding="utf-8") == fixed


def test_order_diagnostics_do_not_move_an_aliased_lists_comments(
    tmp_path: Path,
) -> None:
    configure(tmp_path, "foundata-task-order")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        '---\n- name: "First"\n'
        '  ansible.builtin.debug:\n    msg: "First"\n'
        "  when: &conditions\n    - true # Anchor comment\n\n"
        "# Heading for second task\n"
        '- name: "Second"\n'
        "  register: result\n"
        '  ansible.builtin.debug:\n    msg: "Second"\n'
        "  when: *conditions\n",
        encoding="utf-8",
    )
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 2, result.stdout + result.stderr
    fixed = target.read_text(encoding="utf-8")
    assert fixed.index("# Anchor comment") < fixed.index("# Heading for second task")
    assert fixed.index("# Heading for second task") < fixed.index('name: "Second"')
    data = YAML(typ="safe").load(fixed)
    assert data[0]["when"] == data[1]["when"] == [True]
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 2, result.stdout + result.stderr
    assert target.read_text(encoding="utf-8") == fixed


def test_conditions_with_aliases_keep_scalar_uses_unchanged(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-condition-list")
    target = tmp_path / "tasks" / "main.yml"
    target.write_text(
        """---
- name: "Example"
  ansible.builtin.debug:
    msg: &message "An anchored scalar"
  vars:
    example_message: *message
  when: &condition "enabled"

- name: "Another"
  ansible.builtin.debug:
    msg: *message
  when: *condition
""",
        encoding="utf-8",
    )
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == RC.FIXED_VIOLATIONS, result.stdout + result.stderr
    data = YAML(typ="safe").load(target.read_text(encoding="utf-8"))
    assert data[0]["vars"]["example_message"] == "An anchored scalar"
    assert data[1]["ansible.builtin.debug"]["msg"] == "An anchored scalar"
    assert data[0]["when"] == data[1]["when"] == ["enabled"]
    first = target.read_bytes()
    result = run_lint(tmp_path, "--fix", str(target))
    assert target.read_bytes() == first
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("boolean", ["true", "false"])
def test_anchored_boolean_conditions_keep_their_type_and_scalar_aliases(
    tmp_path: Path, boolean: str
) -> None:
    configure(tmp_path, "foundata-condition-list")
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        '---\n- name: "Example"\n'
        '  ansible.builtin.debug:\n    msg: "Example"\n'
        f"  vars:\n    enabled: &enabled {boolean}\n"
        "    alias: *enabled\n  when: *enabled\n  changed_when: *enabled\n",
        encoding="utf-8",
    )
    result = run_lint(tmp_path, "--fix=foundata-condition-list", str(target))
    assert result.returncode == RC.FIXED_VIOLATIONS, result.stdout + result.stderr
    first = target.read_bytes()
    task = YAML(typ="safe").load(first)[0]
    expected = boolean == "true"
    assert task["vars"]["enabled"] is expected
    assert task["vars"]["alias"] is expected
    assert task["when"][0] is expected
    assert task["changed_when"][0] is expected
    assert (
        run_lint(tmp_path, "--fix=foundata-condition-list", str(target)).returncode == 0
    )
    assert target.read_bytes() == first


def test_task_order_does_not_rewrite_merge_keys(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-task-order")
    target = tmp_path / "tasks" / "main.yml"
    target.write_text(
        """---
- &base
  name: "Base"
  ansible.builtin.debug:
    msg: "Example"

- <<: *base
  name: "Merged"
  register: result
  when:
    - true
""",
        encoding="utf-8",
    )
    before = YAML(typ="safe").load(target.read_text(encoding="utf-8"))
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 2, result.stdout + result.stderr
    assert YAML(typ="safe").load(target.read_text(encoding="utf-8")) == before
