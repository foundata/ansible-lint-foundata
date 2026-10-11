# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Style checks preserve expression and application-data boundaries."""

from ruamel.yaml import YAML

from ansible_lint_foundata.style import parameter_order, unquoted_values


def test_quote_contexts_and_source_styles() -> None:
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    task = yaml.load("""name: "Example"
ansible.builtin.debug:
  var: result.value
  msg: plain
vars:
  data:
    ordinary: unquoted
    quoted: "text"
    block: |
      text
when: [enabled]
until: ["result['x:y'] is defined"]
register: result
loop_control:
  loop_var: example
  index_var: example_index
""")
    assert unquoted_values(task, "debug", "ansible.builtin.debug") == [
        "ansible.builtin.debug.msg",
        "vars.data.ordinary",
    ]


def test_order_does_not_recurse_or_guess_custom_interfaces() -> None:
    yaml = YAML(typ="rt")
    data = yaml.load("""backup: true
src: "source"
dest: "target"
mode: "u=rw,g=r,o=r"
owner: "root"
group: "root"
attributes: "i"
""")
    assert parameter_order(data, "template") == [
        "src",
        "dest",
        "owner",
        "group",
        "mode",
        "attributes",
        "backup",
    ]
    assert parameter_order(data, "set_fact") is None
    assert parameter_order(data, "custom.template") is None
    assert (
        parameter_order(yaml.load('url: "example"\nbody: {z: 1, a: 2}\n'), "uri")
        is None
    )
    assert (
        parameter_order(yaml.load('<<: {backup: true}\nsrc: "source"\n'), "copy")
        is None
    )
