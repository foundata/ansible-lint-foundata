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
- [Configuration](#configuration)
- [Running checks](#running-checks)
- [Formatting and safety](#formatting-safety)
- [Continuous integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Licensing, copyright](#licensing-copyright)
  - [Trademarks](#trademarks)
- [Author information](#author-information)


## Installation<a id="installation"></a>

Requires Python 3.12 or later and Ansible Lint 26.9.0 or later. Install the
extension into the **same environment** as `ansible-lint`.

From your Ansible project, create a lint environment and install the extension
from PyPI:

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python ansible-lint-foundata
. .venv/bin/activate
```

If you already have a lint environment, use its Python path in the install
command and activate that environment instead. To install from source or test a
release artifact, replace the package name with a checkout or wheel path.
Runtime dependencies, including Ansible Lint, are installed with the extension.

Use a regular, non-editable installation. Ansible Lint discovers the installed
rules automatically; you do not need a local rule directory or `sys.path`
changes. For work on the extension itself, use the
[development setup](./DEVELOPMENT.md#getting-started).


## Configuration<a id="configuration"></a>

All foundata rules are opt-in, including under stock profiles. Add their IDs to
`enable_list` in your Ansible project's `.ansible-lint`. This example enables
the condition-list rule alongside the stock production profile:

```yaml
---
profile: "production"
strict: true
enable_list:
  - "foundata-condition-list"
```

For the broader guideline baseline, adapt both tested consumer files:

- [`.ansible-lint`](./examples/consumer/.ansible-lint) enables the adopted
  foundata rules and stock `jinja-template-extension` and `loop-var-prefix`
  checks.
- [`.yamllint`](./examples/consumer/.yamllint) accepts formatter output,
  requires document starts and lowercase booleans, and prefers double quotes
  without forcing them on local identifiers or implicit expressions.

The loop-variable pattern requires a private role prefix and purpose suffix. If
the role's public prefix includes its collection, add that component to
`loop_var_prefix`; the baseline cannot infer it.

Review the [rule contract](./docs/rules.md#implemented-rules) before adopting
the baseline. It enforces its SHOULD-level checks as errors; document that
choice in your project. `foundata-string-quotes` and `foundata-parameter-order`
require separate adoption and are not enabled in the consumer example.


## Running checks<a id="running-checks"></a>

Run the installed command from your Ansible project:

```sh
ansible-lint --list-rules --format brief
ansible-lint
```

The listing confirms discovery, not whether a rule is enabled. The lint run uses
your configuration and reports findings with links to the relevant guideline
sections.

Generated `changelogs/changelog.yaml` should be excluded from Ansible Lint and
validated separately with `antsibull-changelog lint-changelog-yaml`; validate
fragments with `antsibull-changelog lint`.


## Formatting and safety<a id="formatting-safety"></a>

To apply available fixes, run:

```sh
ansible-lint --fix
git diff
ansible-lint
```

Ansible Lint owns YAML formatting. This package does not restore blank lines
removed by `--fix`, require a blank line at EOF, or replace its serializer.
Fixes wrap scalar conditions and handler topics in lists. Extended task ordering
is diagnostic-only; stock `key-order` owns its autofix. The extension does not
rename handler topics, change permissions, reinterpret process exit codes, or
change play termination behavior. Review every fix.

Ansible Lint 26.9.0 returns exit code `8` when all reported violations were
fixed. Run the final check even after that exit code; it should return zero once
no violations remain.

See the [rule contract](./docs/rules.md) for exact coverage, allowed exceptions,
and remaining review requirements.


## Continuous integration<a id="continuous-integration"></a>

CI that requires these checks must install the extension and verify both
discovery and execution before linting, in the same environment:

```sh
ansible-lint-foundata verify --project-dir . && ansible-lint --strict
```

`verify` checks the explicitly enabled foundata rule IDs against bundled invalid
examples. It runs offline without modifying project files or executing
playbooks. A failed check exits nonzero. This verifies rule activation, not
project coverage. Use `--config-file PATH` for a nonstandard config path
relative to the project.

Without this package, the tested Ansible Lint version continues to run stock
checks even if custom IDs remain in `enable_list`. That fallback is for optional
local use. Do not pass missing custom IDs explicitly to `--fix=...`.


## Troubleshooting<a id="troubleshooting"></a>

- If no `foundata-*` rules appear in the listing, check that the extension and
  the command are installed in the same environment. Reinstall the extension
  without editable mode.
- If a listed rule does not report an expected violation, check `enable_list`,
  `skip_list`, local `noqa` comments, and the rule's
  [analysis boundaries](./docs/rules.md#boundaries). Runtime values and
  unresolved references may be outside its scope.
- If a finding remains after `--fix`, check the rule's
  [autofix support](./docs/rules.md#implemented-rules). Most rules require a
  reviewed manual change; extended task ordering is one example.


## Development<a id="development"></a>

See [DEVELOPMENT.md](./DEVELOPMENT.md) for the contributor environment, test
suite, package layout, and release procedure.


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

[![REUSE status](https://api.reuse.software/badge/github.com/foundata/ansible-lint-foundata)](https://api.reuse.software/info/github.com/foundata/ansible-lint-foundata)


### Trademarks<a id="trademarks"></a>

Third-party trademarks used in this repository:

- Ansible® and Red Hat® are trademarks of Red Hat, LLC, registered in the United
  States and other countries.

Their use here is purely descriptive and does not imply any affiliation with or
endorsement by the trademark holders.

Own and licensed trademarks used in this repository:

- foundata® is a trademark of [IPAM GmbH](https://ipam-services.com/),
  registered in Germany and the European Union, licensed to
  [foundata GmbH](https://foundata.com/).


## Author information<a id="author-information"></a>

This [project](https://foundata.com/en/projects/) was created and is maintained
by [foundata](https://foundata.com/).
