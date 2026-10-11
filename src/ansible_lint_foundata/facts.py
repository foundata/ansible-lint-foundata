# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Known built-in injected facts, independent of runtime gathering."""

from jinja2 import Environment, TemplateSyntaxError, nodes

from ansible_lint_foundata.policy import external_name_nodes, template_names

# Intentionally explicit: ansible_* also contains connection and magic variables.
FACT_KEYS = frozenset(
    {
        "all_ipv4_addresses",
        "all_ipv6_addresses",
        "architecture",
        "bios_date",
        "bios_vendor",
        "bios_version",
        "date_time",
        "default_ipv4",
        "default_ipv6",
        "devices",
        "distribution",
        "distribution_major_version",
        "distribution_release",
        "distribution_version",
        "dns",
        "domain",
        "env",
        "fips",
        "fqdn",
        "hostname",
        "interfaces",
        "kernel",
        "kernel_version",
        "local",
        "lsb",
        "machine",
        "memfree_mb",
        "memory_mb",
        "memtotal_mb",
        "mounts",
        "nodename",
        "os_family",
        "pkg_mgr",
        "processor",
        "processor_cores",
        "processor_count",
        "processor_vcpus",
        "python",
        "python_version",
        "selinux",
        "service_mgr",
        "swapfree_mb",
        "swaptotal_mb",
        "system",
        "system_vendor",
        "uptime_seconds",
        "user_dir",
        "user_gecos",
        "user_gid",
        "user_id",
        "user_shell",
        "user_uid",
        "virtualization_role",
        "virtualization_type",
    }
)
FACT_ALIASES = frozenset("ansible_" + name for name in FACT_KEYS)


def injected_fact_references(value: str, *, implicit: bool = False) -> set[str]:
    """Find direct, vars-lookup and hostvars fact aliases, respecting Jinja scope."""
    source = "{{ " + value + " }}" if implicit else value
    names = template_names(source)
    found = names & FACT_ALIASES
    if "hostvars" not in names:
        return found
    try:
        environment = Environment(optimized=False)
        template = environment.parse(source)
        external = external_name_nodes(template, environment)
    except TemplateSyntaxError:
        return found
    for node in template.find_all((nodes.Getattr, nodes.Getitem)):
        if not isinstance(node, nodes.Getattr | nodes.Getitem):
            continue
        container = node.node
        if (
            not isinstance(container, nodes.Getitem | nodes.Getattr)
            or not isinstance(container.node, nodes.Name)
            or container.node.name != "hostvars"
            or id(container.node) not in external
        ):
            continue
        key = (
            node.attr
            if isinstance(node, nodes.Getattr)
            else node.arg.value
            if isinstance(node.arg, nodes.Const)
            else None
        )
        if isinstance(key, str) and key in FACT_ALIASES:
            found.add(key)
    return found
