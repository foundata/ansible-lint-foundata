# Contributing

Report bugs and suggest rule improvements through the project's
[issue trackers](https://foundata.com/en/projects/ansible-lint-foundata/#issues).
Use one of the
[public repositories](https://foundata.com/en/projects/ansible-lint-foundata/#source)
to submit a pull request (PR) or merge request (MR).

Report suspected security vulnerabilities privately through
[GitHub's security reporting feature](https://github.com/foundata/ansible-lint-foundata/security/advisories/new),
not in a public issue.

## Table of contents

- [Issues](#issues)
- [Submitting changes](#submitting-changes)


## Issues<a id="issues"></a>

Search the issue tracker you use before opening a report. For bugs, include:

- The extension, Ansible Lint and Python versions, and how you installed them.
- A minimal YAML or Jinja example and the relevant `.ansible-lint` and
  `.yamllint` settings.
- The exact command, diagnostic output, rule ID and expected result.
- For autofix problems, the input and resulting diff, including whether a second
  run changes the files again.

Remove credentials, private inventory data and other sensitive information from
examples and logs.

For a new rule or a change to an existing rule, link the relevant
[Ansible guideline](https://foundata.com/en/guidelines/ansible-playbooks/)
section and include examples that should pass and fail. Check the
[rule contract](./docs/rules.md) for existing coverage, exceptions and analysis
limits. Describe any proposed guideline change alongside the linting change.


## Submitting changes<a id="submitting-changes"></a>

1. Set up the [development environment](./DEVELOPMENT.md#getting-started).
   Follow the non-editable installation and reinstall instructions so checks run
   against your changes.
2. Keep each change focused. Add tests for changed behavior and regressions;
   update the rule contract and consumer examples when coverage or fixes change.
3. Run the affected tests and [local checks](./DEVELOPMENT.md#local-checks).
   Follow the [development workflow](./DEVELOPMENT.md#development-workflow) for
   changes that need the full suite.
4. Use the project's [scoped commit format](./DEVELOPMENT.md#commit-scopes).
   Check the [licensing information](./README.md#licensing-copyright) and
   [`REUSE.toml`](./REUSE.toml) when adding or reusing material.
5. Explain the behavior change and the checks you ran in your submission.
   Include full URLs for related issues, when applicable.

Do not add changelog entries before the first public 1.0.0 release.

Working on a branch in your own fork lets you make changes without affecting the
original project until we merge them. For help with forks, branches and
submitting changes, use the documentation for the platform hosting the
repository:

| Platform |  Submission type   | Help |
| -------- | ------------------ | ---- |
| GitHub   | Pull request (PR)  | [Quickstart for pull requests](https://docs.github.com/en/pull-requests/get-started/pull-request-quickstart) |
| GitLab   | Merge request (MR) | [Create merge requests](https://docs.gitlab.com/user/project/merge_requests/creating_merge_requests/) |
| Forgejo  | Pull request (PR)  | [Pull requests and Git flow](https://forgejo.org/docs/latest/user/collaboration/pull-requests-and-git-flow/) |
