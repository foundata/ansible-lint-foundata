"""Exercise the published configuration, not an independently copied equivalent."""

import shutil
from pathlib import Path

import pytest
from ansiblelint.constants import RC

from ansible_lint_foundata import RULE_IDS
from tests.integration.test_cli import diagnostics, run_lint

pytestmark = pytest.mark.integration


def install_config(root: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "examples/consumer"
    for name in (".ansible-lint", ".yamllint"):
        shutil.copyfile(source / name, root / name)


def test_consumer_configuration_executes_all_adopted_custom_rules(
    tmp_path: Path,
) -> None:
    install_config(tmp_path)
    (tmp_path / "tasks").mkdir()
    (tmp_path / "handlers").mkdir()
    (tmp_path / "templates").mkdir()
    (tmp_path / "tasks/main.yml").write_text(
        """---
- name: "File"
  register: result
  ansible.builtin.file:
    path: "/tmp/example"
    mode: "0644"
  when: true

- name: "Debug {{ item }}"
  ansible.builtin.debug:
    msg: "{{ example | default('Example') }}"
  loop: []

- name: "Stop"
  ansible.builtin.meta: "end_play"

- name: "Command"
  ansible.builtin.command:
    argv:
      - "/usr/bin/example"
      - "{{ example | ansible.builtin.quote }}"
  changed_when:
    - false
""",
        encoding="utf-8",
    )
    (tmp_path / "handlers/main.yml").write_text(
        """---
- name: "Restart example"
  ansible.builtin.debug:
    msg: "Restart"
    verbosity: 1
  listen: "restart example"
""",
        encoding="utf-8",
    )
    (tmp_path / "templates/example.j2").write_text(
        "{{ inventory_hostname }}\n", encoding="utf-8"
    )
    result = run_lint(
        tmp_path,
        "--format",
        "json",
        "tasks/main.yml",
        "handlers/main.yml",
        "templates/example.j2",
    )
    custom = {
        item["check_name"]
        for item in diagnostics(result)
        if item["check_name"].startswith("foundata-")
    }
    assert custom == set(RULE_IDS)
    assert result.returncode == 2


def test_consumer_config_enables_stock_template_and_role_loop_checks(
    tmp_path: Path,
) -> None:
    install_config(tmp_path)
    tasks = tmp_path / "roles/example/tasks"
    tasks.mkdir(parents=True)
    templates = tasks.parent / "templates"
    templates.mkdir()
    (templates / "example.conf").write_text("Static content\n", encoding="utf-8")
    (tasks / "main.yml").write_text(
        """---
- name: "Configure example"
  ansible.builtin.template:
    src: "example.conf"
    dest: "/tmp/example"
    mode: "u=rw,g=r,o=r" # 0644
  loop: []
""",
        encoding="utf-8",
    )
    matches = diagnostics(
        run_lint(tmp_path, "--format", "json", str(tasks / "main.yml"))
    )
    assert {item["check_name"] for item in matches} == {
        "jinja-template-extension",
        "loop-var-prefix[missing]",
    }


def test_consumer_yaml_configuration_accepts_formatter_output(tmp_path: Path) -> None:
    install_config(tmp_path)
    (tmp_path / "tasks").mkdir()
    target = tmp_path / "tasks/main.yml"
    target.write_text(
        """---
- name: "Example"
  ansible.builtin.debug:
    msg: 'Example'
    verbosity: 1
  when: true # Keep this condition

# Next task
- name: "Another example"
  ansible.builtin.debug:
    msg: 'Contains "quotes"'
    verbosity: 1
""",
        encoding="utf-8",
    )
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == RC.FIXED_VIOLATIONS, result.stdout + result.stderr
    first = target.read_bytes()
    assert diagnostics(run_lint(tmp_path, "--format", "json", str(target))) == []
    result = run_lint(tmp_path, "--fix", str(target))
    assert result.returncode == 0, result.stdout + result.stderr
    assert target.read_bytes() == first
