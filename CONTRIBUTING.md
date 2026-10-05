# Contributing

Development takes place on our internal repository hosting platform. You can
report issues and submit changes through any of our public repositories on
platforms such as GitHub, GitLab or Codeberg. We coordinate the work internally
and follow up on the platform where you contributed.

Choose an
[issue tracker](https://foundata.com/en/projects/ansible-lint-foundata/#issues)
or
[public repository](https://foundata.com/en/projects/ansible-lint-foundata/#source)
on the project page.

Follow the [code of conduct](./CODE_OF_CONDUCT.md) when participating.

Report suspected security vulnerabilities privately using the channels in
[SECURITY.md](./SECURITY.md#reporting), not in a public issue.

## Table of contents

- [Issues](#issues)
- [Discussions](#discussions)
- [Submitting changes](#submitting-changes)


## Issues<a id="issues"></a>

If you spot a problem, have an idea or want to request a feature, use the issue
tracker where this project's repository is hosted, such as GitHub, GitLab or
Codeberg. Search the existing issues there before opening a new one.

You only need to report an issue once, on one platform. If you know of a related
issue on another platform, include its full URL so we can connect the reports.

We don't assign issues automatically. Leave a comment if you'd like to work on
an issue or have already started. You can also ask us to assign it to you.

For bugs, include:

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


## Discussions<a id="discussions"></a>

If you have something to discuss or comment about the project, feel free to send
an email to Andreas Haerter <ah@foundata.com> (no support requests, all
resources are provided "as is").


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

Document notable user-facing changes under `Unreleased` in
[`CHANGELOG.md`](./CHANGELOG.md).

Working on a branch in your own fork lets you make changes without affecting the
original project until we merge them. For help with forks, branches and
submitting changes, use the documentation for the platform hosting the
repository:

| Platform |  Submission type   | Help |
| -------- | ------------------ | ---- |
| GitHub   | Pull request (PR)  | [Quickstart for pull requests](https://docs.github.com/en/pull-requests/get-started/pull-request-quickstart) |
| GitLab   | Merge request (MR) | [Create merge requests](https://docs.gitlab.com/user/project/merge_requests/creating_merge_requests/) |
| Forgejo  | Pull request (PR)  | [Pull requests and Git flow](https://forgejo.org/docs/latest/user/collaboration/pull-requests-and-git-flow/) |
