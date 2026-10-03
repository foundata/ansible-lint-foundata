"""Known aliases must not become a blanket ansible_ prefix ban."""

import pytest

from ansible_lint_foundata.facts import injected_fact_references


@pytest.mark.parametrize(
    ("value", "implicit", "expected"),
    [
        ("{{ ansible_distribution }}", False, {"ansible_distribution"}),
        ("ansible_os_family == 'RedHat'", True, {"ansible_os_family"}),
        ("ansible_distribution", False, set()),
        ("'ansible_distribution'", True, set()),
        ("{{ ansible_host }} {{ ansible_user }} {{ ansible_version }}", False, set()),
        ("{{ ansible_facts['distribution'] }}", False, set()),
        ("{{ config['ansible_distribution'] }}", False, set()),
        ("{{ vars['ansible_distribution'] }}", False, {"ansible_distribution"}),
        (
            "{{ lookup('ansible.builtin.vars', 'ansible_os_family') }}",
            False,
            {"ansible_os_family"},
        ),
        (
            "{{ hostvars[inventory_hostname]['ansible_distribution'] }}",
            False,
            {"ansible_distribution"},
        ),
        ("{{ hostvars.target.ansible_distribution }}", False, {"ansible_distribution"}),
        (
            "{% for ansible_distribution in values %}{{ ansible_distribution }}{% endfor %}",
            False,
            set(),
        ),
        (
            "{% set hostvars = data %}{{ hostvars.target.ansible_distribution }}",
            False,
            set(),
        ),
        ("{{ broken", False, set()),
    ],
)
def test_alias_references(value: str, implicit: bool, expected: set[str]) -> None:
    assert injected_fact_references(value, implicit=implicit) == expected
