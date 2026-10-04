# Ansible Lint (foundata extension)

Additional rules and conservative autofixes for
[foundata's Ansible playbook guidelines](https://foundata.com/en/guidelines/ansible-playbooks/).
This optional extension uses the stock
[Ansible Lint](https://docs.ansible.com/projects/lint/) command.

<!-- rumdl-disable MD033 -->
<!-- HTML for consistent rendering across limited platform parsers -->
<div align="center" id="project-readme-header">
<br>
<br>

**⭐ Found this useful? Support open-source and star this project:**

[![GitHub repository](https://img.shields.io/github/stars/foundata/ansible-lint-foundata.svg)](https://github.com/foundata/ansible-lint-foundata)

<br>
</div>
<!-- rumdl-enable MD033 -->

## Table of contents

- [Installation](#installation)
- [Formatting and safety](#formatting-safety)
- [Licensing, copyright](#licensing-copyright)
  - [Trademarks](#trademarks)
- [Author information](#author-information)


## Installation<a id="installation"></a>

Install into the **same environment** as `ansible-lint`. For local development:

```sh
uv sync --locked --no-editable
```

Ansible Lint discovers installed modules under
`ansiblelint.rules.custom.foundata`; no repository-local rule directory or
`sys.path` changes are needed. Use a non-editable installation as described in
[development](DEVELOPMENT.md).

All rules are opt-in. Enable individual IDs in `.ansible-lint`, including when
using a stock profile:

```yaml
---
profile: "production"
strict: true
enable_list:
  - "foundata-condition-list"
  - "foundata-condition-bool"
  - "foundata-fact-vars"
  - "foundata-notify"
  - "foundata-loop-collision"
  - "foundata-set-fact"
  - "foundata-handler-listen"
  - "foundata-task-order"
  - "foundata-file-mode"
  - "foundata-debug-verbosity"
  - "foundata-no-end-play"
  - "foundata-task-name"
  - "foundata-jinja-fqcn"
  - "foundata-template-inputs"
  - "foundata-command-argv"
```

Run:

```sh
ansible-lint
ansible-lint --fix
```

Without this package, the tested Ansible Lint version continues to run its stock
checks even if these IDs remain in `enable_list`. Do not pass missing custom IDs
explicitly to `--fix=...`. Installed foundata rules remain inactive unless
enabled in the configuration. Fallback without the package is for optional
local use; CI that requires the extension must verify its installation.

Document which SHOULD-level recommendations the project enforces as errors.
In the lint environment, check every enabled custom rule ID with
`ansible-lint --list-rules --format brief` using the project's configuration.
Fail CI if any are absent. Listing checks discovery; use known-invalid
fixtures to verify that the enabled rules also report violations.

The tested consumer configurations in
[`examples/consumer/.ansible-lint`](examples/consumer/.ansible-lint) and
[`examples/consumer/.yamllint`](examples/consumer/.yamllint) enable stock
`jinja-template-extension` and `loop-var-prefix` alongside the foundata rules.
The loop check requires a private role prefix and purpose suffix. Where a role's
public prefix includes its collection, add that component to `loop_var_prefix`;
the baseline cannot infer it.

The YAML configuration accepts formatter output, enforces document starts and
lowercase booleans, and prefers double quotes without forcing quotes on local
identifiers or implicit expressions. Optional `foundata-string-quotes` and
`foundata-parameter-order` checks require separate adoption; they are not
enabled in the example. The example enforces its SHOULD-level checks as errors.


## Formatting and safety<a id="formatting-safety"></a>

Ansible Lint owns YAML formatting. This package does not restore blank lines
removed by `--fix`, require a blank line at EOF, or replace its serializer.
Fixes wrap scalar conditions and handler topics in lists. Extended task ordering
is diagnostic-only; stock `key-order` owns its autofix. The extension does not
rename handler topics, change permissions, reinterpret process exit codes, or
change play termination behavior. Review every fix.

See the [rule contract](docs/rules.md) for exact coverage and remaining review
requirements.

Generated `changelogs/changelog.yaml` should be excluded from Ansible Lint and
validated separately with `antsibull-changelog lint-changelog-yaml`; validate
fragments with `antsibull-changelog lint`.


## Licensing, copyright<a id="licensing-copyright"></a>

[![REUSE status](https://api.reuse.software/badge/github.com/foundata/ansible-lint-foundata)](https://api.reuse.software/info/github.com/foundata/ansible-lint-foundata)

<!--REUSE-IgnoreStart-->
<!-- rumdl-disable MD034 --><!-- should match SPDX-PackageSupplier -->
Copyright (c) 2026, [foundata GmbH](https://foundata.com/)
(https://foundata.com)
<!-- rumdl-enable MD034 -->

This project is licensed under the GNU General Public License v3.0 or later
(SPDX-License-Identifier: `GPL-3.0-or-later`), see
[`LICENSES/GPL-3.0-or-later.txt`](./LICENSES/GPL-3.0-or-later.txt)
for the full text.

[`REUSE.toml`](./REUSE.toml) records licensing and copyright information in a
human- and machine-readable format, including any different terms for
third-party components. The repository follows the
[REUSE specification](https://reuse.software/spec/). Use
[`reuse spdx`](https://reuse.readthedocs.io/en/latest/readme.html#cli) to create
an
[SPDX software bill of materials (SBOM)](https://en.wikipedia.org/wiki/Software_Package_Data_Exchange).
<!--REUSE-IgnoreEnd-->


### Trademarks<a id="trademarks"></a>

Own and licensed trademarks used in this repository:

- foundata® is a trademark of [IPAM GmbH](https://ipam-services.com/),
  registered in Germany, the European Union, licensed to
  [foundata GmbH](https://foundata.com/).


## Author information<a id="author-information"></a>

This [project](https://foundata.com/en/projects/) was created and is maintained
by [foundata](https://foundata.com/).
