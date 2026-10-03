"""Permission diagnostics must survive YAML indirection and argument syntax."""

from pathlib import Path

import pytest

from tests.integration.test_cli import configure, diagnostics, run_lint

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("definition", "expected_lines"),
    [
        ('"0644"', {5, 11}),
        ('"u=rw,g=r,o=r" # 0644', {11}),
        ('"u=rw,g=r,o=r" # 0600', {5, 11}),
    ],
)
def test_merged_modes_use_the_definition_and_do_not_drop_later_findings(
    tmp_path: Path, definition: str, expected_lines: set[int]
) -> None:
    configure(tmp_path, "foundata-file-mode", profile="production")
    (tmp_path / "tasks/main.yml").write_text(
        f"""---
- name: "Merged file"
  ansible.builtin.file:
    <<: &parameters
      mode: {definition}
    path: "/tmp/one"

- name: "Direct file"
  ansible.builtin.file:
    path: "/tmp/two"
    mode: "u+rw"
""",
        encoding="utf-8",
    )
    result = run_lint(tmp_path, "--strict", "--format", "json", "tasks/main.yml")
    matches = diagnostics(result)
    assert result.returncode == 2
    assert {item["check_name"] for item in matches} == {"foundata-file-mode"}
    assert {item["location"]["lines"]["begin"] for item in matches} == expected_lines


def test_nested_merge_precedence_and_local_override(tmp_path: Path) -> None:
    configure(tmp_path, "foundata-file-mode")
    (tmp_path / "tasks/main.yml").write_text(
        """---
- name: "Merged file"
  ansible.builtin.file:
    <<: &parameters
      <<: &base
        mode: "u=rw,g=r,o=r" # 0644
      path: "/tmp/one"

- name: "Overridden file"
  ansible.builtin.file:
    <<: [*parameters, {mode: "0777"}]
    mode: "u=rw,g=,o=" # 0600

- name: "First merge wins"
  ansible.builtin.file:
    <<: [*base, {mode: "0777"}]
    path: "/tmp/two"
""",
        encoding="utf-8",
    )
    assert diagnostics(run_lint(tmp_path, "--format", "json", "tasks/main.yml")) == []


@pytest.mark.parametrize("namespace", ["ansible.builtin", "ansible.legacy"])
def test_builtin_module_namespaces_have_the_same_coverage(
    tmp_path: Path, namespace: str
) -> None:
    configure(
        tmp_path,
        "foundata-file-mode",
        "foundata-debug-verbosity",
        "foundata-no-end-play",
    )
    (tmp_path / "tasks/main.yml").write_text(
        f"""---
- name: "File"
  {namespace}.file:
    path: "/tmp/example"
    mode: "0644"
- name: "Debug"
  {namespace}.debug:
    msg: "Example"
- name: "Stop"
  {namespace}.meta: "end_play"
""",
        encoding="utf-8",
    )
    matches = diagnostics(run_lint(tmp_path, "--format", "json", "tasks/main.yml"))
    assert {item["check_name"] for item in matches} == {
        "foundata-file-mode",
        "foundata-debug-verbosity",
        "foundata-no-end-play",
    }
