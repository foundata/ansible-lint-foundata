# Ansible Lint (foundata extension)

Additional rules and conservative autofixes for
[foundata's Ansible playbook guidelines](https://foundata.com/en/guidelines/ansible-playbooks/).
This is an optional extension, not a fork or replacement command.

## Table of contents

- [Installation](#installation)
- [Formatting and Safety](#formatting-and-safety)
- [Licensing, copyright](#licensing-copyright)
  - [Trademarks](#trademarks)
- [Author information](#author-information)


## Installation<a id="installation"></a>

Install into the **same environment** as `ansible-lint`. For local development:

```sh
uv sync --locked --no-editable
```

Ansible Lint discovers installed modules under
`ansiblelint.rules.custom.foundata`. No repository-local rule directory, custom
command or `sys.path` modification is required. Editable installs are not the
supported discovery path; see [development](DEVELOPMENT.md).

All rules are opt-in. Enable individual IDs in `.ansible-lint`, including when
using a stock profile:

```yaml
---
profile: "production"
enable_list:
  - "foundata-condition-list"
  - "foundata-handler-listen"
  - "foundata-task-order"
  - "foundata-file-mode"
  - "foundata-debug-verbosity"
  - "foundata-no-end-play"
  - "foundata-task-name"
```

Then run the usual commands:

```sh
ansible-lint
ansible-lint --fix
```

Without this package, the tested Ansible Lint version continues to run its stock
checks even if these IDs remain in `enable_list`. Do not pass missing custom IDs
explicitly to `--fix=...`. Without the configuration, installed foundata rules
remain inactive. Required project CI must verify installation and discovery;
optional local fallback must not silently weaken CI.


## Formatting and Safety<a id="formatting-and-safety"></a>

Ansible Lint owns YAML formatting. This package does not restore blank lines
removed by `--fix`, require a blank line at EOF, or replace its serializer.
Fixes wrap scalar conditions/topics and reorder task keys. They do not rename
handler topics, change permissions, reinterpret process exit codes, or change
play termination behavior. Review every fix.

Generated `changelogs/changelog.yaml` should be excluded from Ansible Lint and
validated separately with `antsibull-changelog lint-changelog-yaml`; validate
fragments with `antsibull-changelog lint`.


## Licensing, copyright<a id="licensing-copyright"></a>

<!--REUSE-IgnoreStart-->
<!-- rumdl-disable MD034 --><!-- should match SPDX-PackageSupplier -->
Copyright (c) 2026, [foundata GmbH](https://foundata.com/)
(https://foundata.com)
<!-- rumdl-enable MD034 -->

This project is licensed under the GNU General Public License v3.0 or later
(SPDX-License-Identifier: `GPL-3.0-or-later`), see
[`LICENSES/GPL-3.0-or-later.txt`](./LICENSES/GPL-3.0-or-later.txt)
for the full text.

The [`REUSE.toml`](./REUSE.toml) file provides detailed licensing and copyright
information in a human- and machine-readable format. This includes parts that
may be subject to different licensing or usage terms, such as third-party
components. The repository conforms to the
[REUSE specification](https://reuse.software/spec/). You can use
[`reuse spdx`](https://reuse.readthedocs.io/en/latest/readme.html#cli) to create
a
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
