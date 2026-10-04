"""Known-invalid inputs for installed rule verification; never run as playbooks."""

PROBES = {
    "tasks/main.yml": """---
- name: "File"
  register: result
  ansible.builtin.file:
    mode: "0644"
    path: "/tmp/example"
  when: true
  until:
    - "'ready'"

- name: "Debug {{ item }}"
  ansible.builtin.debug:
    msg: "{{ ansible_distribution | default('Example') }}"
  loop: []

- name: "Unquoted string"
  ansible.builtin.debug:
    msg: example
    verbosity: 1

- name: "Overwrite input"
  ansible.builtin.set_fact:
    example_input: true
  vars:
    example_input: false

- name: "Stop caller"
  ansible.builtin.meta: "end_play"

- name: "Command"
  ansible.builtin.command:
    argv:
      - "/usr/bin/example"
      - "{{ example | ansible.builtin.quote }}"
  changed_when:
    - false
""",
    "handlers/main.yml": """---
- name: "Restart example"
  ansible.builtin.debug:
    msg: "Restart"
    verbosity: 1
  listen: "restart example"
""",
    "templates/example.j2": "{{ inventory_hostname }}\n",
    "playbook.yml": """---
- name: "Graph checks"
  hosts: "localhost"
  tasks:
    - name: "Missing notification"
      ansible.builtin.debug:
        msg: "Example"
        verbosity: 1
      notify: "missing_topic"

    - name: "Outer loop"
      ansible.builtin.include_tasks: "tasks/inner.yml"
      loop: [1]
""",
    "tasks/inner.yml": """---
- name: "Inner loop"
  ansible.builtin.debug:
    msg: "Example"
    verbosity: 1
  loop: [2]
""",
}
