# Changelog

<!--
SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

Notable, user-facing changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

- Nothing worth mentioning right now.


## [1.1.0] - 2026-10-04

### Added

- Optional `ansible-lint-foundata verify` command to check configured rule
  discovery and execution before linting.


## [1.0.0] - 2026-10-04

### Added

- Initial stable release with 17 opt-in rules for foundata's Ansible playbook
  guidelines, discovered by the stock `ansible-lint` command.
- Checks for conditions, handler topics and notifications, task ordering and
  naming, file permissions, debugging, play termination, Jinja expressions and
  template inputs, command arguments, facts, variable collisions and string
  formatting.
- Conservative list-format fixes for conditions and handler topics that preserve
  values, comments and YAML aliases.
- Tested consumer configurations, rule coverage and exception documentation, and
  support for Python 3.12, 3.13 and 3.14 and Ansible Lint 26.9.0 or later.

[unreleased]: https://github.com/foundata/ansible-lint-foundata/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/foundata/ansible-lint-foundata/releases/tag/v1.1.0
[1.0.0]: https://github.com/foundata/ansible-lint-foundata/releases/tag/v1.0.0
