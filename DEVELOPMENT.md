# Development

For contributors and maintainers of `ansible-lint-foundata`. User installation
and configuration are covered in the [README](./README.md); detection boundaries
and expected fixes are defined in the [rule contract](./docs/rules.md).

## Table of contents

- [Prerequisites](#prerequisites)
- [Getting started](#getting-started)
- [Project structure](#project-structure)
- [Development standards](#development-standards)
  - [Code formatting and linting](#code-linting)
  - [Commit messages and scopes](#commit-scopes)
- [Testing](#testing)
  - [Running tests](#running-tests)
  - [Writing tests](#writing-tests)
  - [Compatibility tests](#compatibility-tests)
  - [Distribution checks](#distribution-checks)
- [Development workflow](#development-workflow)
- [Releases](#releases)
- [Troubleshooting](#troubleshooting)


## Prerequisites<a id="prerequisites"></a>

- Python 3.12 or later. Release checks cover Python 3.12, 3.13 and 3.14.
- Git and [`uv`](https://docs.astral.sh/uv/getting-started/installation/).
- `tar` for release artifact checks.
- Bash for the commands below. Package installation and distribution
  checks may need network access.

The development dependency group includes Ruff, mypy, pytest, pytest-cov, REUSE,
rumdl and `releasing`. Ansible Lint 26.9.0 is the supported minimum for rule
discovery, profiles and transforms; lower it only after the full compatibility
suite passes.


## Getting started<a id="getting-started"></a>

Clone a repository from the
[available sources](https://foundata.com/en/projects/ansible-lint-foundata/#source),
or use an existing checkout. For example, using GitHub:

```sh
git clone https://github.com/foundata/ansible-lint-foundata.git
cd ansible-lint-foundata
```

Install the locked development environment and check rule discovery:

```sh
uv sync --locked --no-editable --reinstall-package ansible-lint-foundata
uv run --no-sync ansible-lint --offline --list-rules --format brief
uv run --no-sync pytest
```

The listing should contain every ID in `RULE_IDS` in
[`src/ansible_lint_foundata/__init__.py`](./src/ansible_lint_foundata/__init__.py),
alongside stock rules such as `yaml` and `fqcn`.

Repeat the sync command after source changes. Ansible Lint discovers rule
directories under its installed package; an editable installation alone does not
put the discovery adapter there. `--no-sync` keeps later commands from replacing
the regular installation with an editable one. Do not modify `sys.path` or
replace Ansible Lint's package files to work around discovery.


## Project structure<a id="project-structure"></a>

|                   Path                   | Purpose |
| ---------------------------------------- | ------- |
| `src/ansible_lint_foundata/`             | Policy helpers, parsing, graph analysis and fixes |
| `src/ansiblelint/rules/custom/foundata/` | Rule classes discovered by Ansible Lint |
| `tests/unit/`                            | Helper and policy tests |
| `tests/integration/`                     | Installed CLI, configuration and autofix tests |
| `examples/consumer/`                     | Tested Ansible Lint and YAML configurations |
| `scripts/check_distribution.py`          | Packaging, installed discovery and uninstall checks |
| `docs/rules.md`                          | Rule behavior, analysis limits and release acceptance |
| `pyproject.toml`, `uv.lock`              | Package metadata, tool configuration and locked development dependencies |

The wheel contains both source packages, but no parent
`ansiblelint/__init__.py`. Each uniquely named discovery module defines its
concrete rule class because the upstream loader verifies the class's source
directory. Put reusable policy logic in `ansible_lint_foundata`.


## Development standards<a id="development-standards"></a>

Follow foundata's [Python guide](https://foundata.com/en/guidelines/python/).
The project's [`pyproject.toml`](./pyproject.toml) configures Ruff for Python
3.12 and 88-character lines, strict mypy checks, and pytest with importlib mode,
strict configuration and warnings as errors.

Runtime dependencies use minimum versions without speculative upper bounds.
[`uv.lock`](./uv.lock) pins the development environment; it does not constrain
downstream installations. Review dependency updates separately and test both the
locked environment and supported lower bounds.

### Code formatting and linting<a id="code-linting"></a>

Apply formatting, then review the changes:

```sh
uv run --no-sync ruff format .
uv run --no-sync rumdl fmt --config .rumdl.toml --deny-config-warnings .
```

Markdown follows the
[Markdown guide](https://foundata.com/en/guidelines/markdown/) through
[`.rumdl.toml`](./.rumdl.toml). Naming the configuration explicitly prevents
another discovered configuration from changing the checks.

<a id="local-checks"></a>

Run the non-writing checks before committing:

```sh
uv run --no-sync ruff format --check .
uv run --no-sync ruff check .
uv run --no-sync mypy src tests scripts
uv run --no-sync rumdl check --config .rumdl.toml --deny-config-warnings .
uv run --no-sync reuse lint
git diff --check
```

Run the [tests](#running-tests) and [distribution checks](#distribution-checks)
as well before a release.

### Commit messages and scopes<a id="commit-scopes"></a>

Use one-line subjects in the form `<scope>: <description>`, following foundata's
[commit guide](https://foundata.com/en/guidelines/git-commits/). Use the
affected area as the scope, including for documentation changes. Do not use bare
change types such as `docs`, `fix` or `chore`, or add attribution trailers.

|                      Scope                       | Area |
| ------------------------------------------------ | ---- |
| `rules`, `rules/conditions`, `rules/permissions` | Rule behavior and its contract |
| `tests`                                          | Shared testing infrastructure |
| `readme`, `development`                          | User and contributor documentation |
| `build`, `dependencies`                          | Packaging and dependency management |
| `release`, `licensing`, `repository`             | Release preparation, licensing and repository-wide concerns |


## Testing<a id="testing"></a>

### Running tests<a id="running-tests"></a>

After reinstalling the source changes, run the full suite or a focused subset:

```sh
uv run --no-sync pytest
uv run --no-sync pytest tests/unit/
uv run --no-sync pytest tests/integration/
uv run --no-sync pytest tests/unit/test_policy.py
uv run --no-sync pytest --cov=ansible_lint_foundata
```

Unit tests exercise parsing and policy helpers. Integration tests run the
installed Ansible Lint command in temporary projects. They create their YAML and
Jinja inputs under `tmp_path`, without modifying users' collections.

### Writing tests<a id="writing-tests"></a>

- Add positive and negative cases for each rule, including a regression for each
  fixed bug.
- Use the existing `configure`, `run_lint` and `diagnostics` helpers in
  [`tests/integration/test_cli.py`](./tests/integration/test_cli.py) for
  installed-CLI tests. Keep subprocess tests marked `integration`.
- For fixes, check semantic values, comments and a second pass that leaves the
  bytes unchanged. Test anchored values, imports and exclusions when the changed
  behavior touches them.
- Verify discovery and actual execution under the intended profile.
  [`test_consumer_config.py`](./tests/integration/test_consumer_config.py) tests
  the published configuration against known-invalid inputs for every adopted
  rule.
- Keep the verification command's bundled examples current when adding rules.
- Keep tests isolated from user configuration and use pytest's temporary
  directories. Do not make fixtures pass by rewriting their expected inputs.

### Compatibility tests<a id="compatibility-tests"></a>

Run the locked suite in a separate environment for each supported Python
version. The subshell keeps these environment selections out of your normal
development session and stops at the first failure:

```sh
(
  set -eu
  for version in 3.12 3.13 3.14; do
    export UV_PROJECT_ENVIRONMENT=".cache/venvs/${version}"
    uv sync --locked --no-editable --python "${version}" \
      --reinstall-package ansible-lint-foundata
    uv run --no-sync --python "${version}" pytest
  done
)
```

Check the lower dependency bounds separately without rewriting `uv.lock`:

```sh
uv venv --python 3.12 .cache/venvs/minimum
uv pip install --python .cache/venvs/minimum/bin/python \
  --resolution lowest-direct --group dev .
.cache/venvs/minimum/bin/python -m pytest
```

Use a fresh environment for this resolution. Check the resolved versions:
transitive constraints can raise a declared lower bound. Resolve any untested
lower-bound claim before a release.

### Distribution checks<a id="distribution-checks"></a>

```sh
uv build
uv run --no-sync python scripts/check_distribution.py
```

The script builds temporary artifacts, checks wheel contents and
source-distribution completeness, rebuilds the wheel from the source
distribution, and verifies installed rule discovery outside the checkout. It
also uninstalls the extension and checks that stock linting still works. It
requires `uv` on `PATH` and may download dependencies into its disposable
environment.

Those temporary artifacts are deleted when the script finishes. The script does
not validate an existing `dist/` directory; smoke-test the exact files selected
for publication as described under [Releases](#releases).


## Development workflow<a id="development-workflow"></a>

1. Start from a working [development environment](#getting-started) and passing
   tests. Create a topic branch for the change.
2. Update the behavior and its tests together. Keep the
   [rule contract](./docs/rules.md) and user configuration examples consistent
   with any change in coverage or fixes.
3. Reinstall with
   `uv sync --locked --no-editable --reinstall-package ansible-lint-foundata`,
   then run the affected tests and [local checks](#local-checks). Run the full
   suite for shared parsing, discovery or cross-file behavior.
4. Review `git diff` and commit only the intended paths.


## Releases<a id="releases"></a>

A release of `ansible-lint-foundata` consists of:

- one Semantic Versioning `X.Y.Z` version
- one annotated `vX.Y.Z` Git tag
- one GitHub release for that tag
- the source distribution and wheel published on PyPI for that version.

The maintainer performing a release needs:

- an authenticated `gh` installation
- an authorized PyPI publishing identity
- push access to `origin`
- [our `release` tool](https://foundata.com/en/projects/releasing/), installed
  with the development dependencies. It reads the `[tool.releasing]` declaration
  in [`pyproject.toml`](./pyproject.toml), which selects this repository and
  uses the defaults for the version site, changelog, tag format and publishing
  services.

Release only a clean, committed revision. Test results and retained artifacts
belong to that exact revision and cannot be carried over after another commit.
Keep credentials and release artifacts outside the repository.

Run the steps from the repository root in the same Bash session and stop on any
failure. Keep `--no-sync` on the `uv run` commands so they preserve the
noneditable installation required for rule discovery.

1. **Choose the version and confirm the starting point.** Select the version
   according to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

   ```sh
   version="<CHANGEME version>" # major.minor.patch
   tag="v${version}"

   git status --short
   git tag --list "${tag}"

   uv run --no-sync release config check
   uv run --no-sync release version check
   uv run --no-sync release changelog check
   ```

   Start from a clean branch and stop if the tag already exists or a check
   reports a problem. Every
   [release acceptance check](./docs/rules.md#release-acceptance) must pass
   before publication. Required consumer CI must verify installation, discovery
   and execution; package-free fallback is only for optional local use.

2. **Prepare the versioned sources and changelog.** Review the entries under
   `Unreleased`, then move them to the new release.

   ```sh
   uv run --no-sync release version bump "${version}"
   uv run --no-sync release changelog release "${version}"

   uv run --no-sync release version check --expect "${version}"
   uv run --no-sync release changelog check
   uv sync --locked --no-editable --reinstall-package ansible-lint-foundata
   ```

   `version bump` updates [`pyproject.toml`](./pyproject.toml) and runs
   `uv lock`. The package reads its version from installed distribution
   metadata; there is no second version constant. `changelog release` moves the
   reviewed entries in [`CHANGELOG.md`](./CHANGELOG.md) into a dated section,
   retains `Unreleased` and updates comparison links. It requires at least one
   release-note entry.

   Review the [rule contract](./docs/rules.md), consumer configuration and
   README for changes the release needs to document.

3. **Review and commit the release preparation.** Stage only the reviewed
   release changes. The tag will name this commit.

   ```sh
   git diff --check
   git diff
   git add --all
   git diff --cached
   git commit -m "release: prepare ${version}"

   revision="$(git rev-parse --verify HEAD)"
   git status --short # must print nothing
   ```

   Do not amend the release commit after validation starts; a source change
   requires a new commit and repeated checks.

4. **Run the checks and build from the committed revision.** Run the
   [local checks](#local-checks),
   [Python and dependency compatibility tests](#compatibility-tests), and
   [distribution checks](#distribution-checks). Once they pass, build the files
   that will be published:

   ```sh
   install -d -m 0700 "${HOME}/.local/share/ansible-lint-foundata/distributions"
   artifact_dir="${HOME}/.local/share/ansible-lint-foundata/distributions/${revision}"

   uv run --no-sync release build --out "${artifact_dir}" --expect "${version}"
   uv run --no-sync release artifacts verify "${artifact_dir}/artifacts.json"
   ```

   The destination must not exist before the build starts. The command exports
   the commit, prepares README links for the version's GitHub tag inside the
   export, builds the source distribution and then the wheel from it, and checks
   both. The committed README keeps its relative links. `artifacts.json` records
   the source revision, version and SHA-256 digests; retain it with the
   distributions through publication.

5. **Test the retained wheel outside the checkout.** Install it into a fresh
   environment and run the full suite from an export of the same revision.

   ```sh
   verification_dir="$(mktemp -d)"
   git archive --format=tar --output="${verification_dir}/source.tar" "${revision}"
   mkdir "${verification_dir}/source"
   tar -xf "${verification_dir}/source.tar" -C "${verification_dir}/source"

   uv venv --python 3.12 "${verification_dir}/venv"
   uv pip install --python "${verification_dir}/venv/bin/python" \
     --group dev "${artifact_dir}"/*.whl
   "${verification_dir}/venv/bin/python" -c \
     "from importlib.metadata import version; assert version('ansible-lint-foundata') == '${version}'"
   (
     cd "${verification_dir}/source"
     "${verification_dir}/venv/bin/python" -m pytest
   )
   uv run --no-sync release artifacts verify "${artifact_dir}/artifacts.json"
   ```

   These integration tests cover installed rule discovery, stock-rule
   coexistence, enabled-rule execution and autofixes. The earlier distribution
   script builds disposable artifacts; it does not replace this check of the
   files selected for upload.

6. **Tag the validated revision, then push the branch and tag.** Confirm that
   `HEAD` is still the revision whose artifacts passed the tests.

   ```sh
   test "$(git rev-parse --verify HEAD)" = "${revision}"
   uv run --no-sync release tag create "${version}" \
     --manifest "${artifact_dir}/artifacts.json"
   git show "${tag}"

   uv run --no-sync release push "${version}"
   ```

   `tag create` checks the clean tree, version, lockfile and changelog. The
   manifest prevents tagging a revision other than the artifact source. `push`
   sends the branch before the tag and checks that the branch contains the
   tagged commit.

7. **Publish the retained distributions to PyPI without rebuilding.** Supply
   `UV_PUBLISH_TOKEN` through your credential manager or a hidden Bash prompt,
   keeping it out of shell history and process arguments:

   ```sh
   printf 'PyPI API token: '
   read -rs UV_PUBLISH_TOKEN
   printf '\n'
   export UV_PUBLISH_TOKEN

   uv run --no-sync release publish "${artifact_dir}/artifacts.json"

   unset UV_PUBLISH_TOKEN
   ```

   `publish` rechecks every digest and refuses unlisted distributions beside the
   manifest. PyPI versions are immutable; corrected contents need a new version.

8. **Create the GitHub release.**

   ```sh
   uv run --no-sync release forge release-create "${version}" \
     --manifest "${artifact_dir}/artifacts.json"
   ```

   The notes come from the version's changelog section. The assets are
   `artifacts.json` and the distributions it names, verified before the entry is
   created. The command uses the authenticated `gh` session.

9. **Verify the published release.**

   ```sh
   uv run --no-sync release verify "${artifact_dir}/artifacts.json" \
     --version "${version}"
   uv run --no-sync release status "${version}" \
     --manifest "${artifact_dir}/artifacts.json"
   ```

   Verification checks the files and digests served by PyPI, the version
   reported by an isolated installation and GitHub's latest release. Repeat
   installed rule discovery and a consumer lint smoke check against the
   published package; the generic version check does not exercise custom rules.

To inspect progress after an interruption, run:

```sh
uv run --no-sync release status "${version}" --manifest "${artifact_dir}/artifacts.json"
```

Omit `--manifest` before the build has produced one. The command reports
completed, unfinished, broken or unreachable steps without performing them.

Before any upload and while no GitHub release exists, an incorrect tag can be
removed locally and remotely:

```sh
uv run --no-sync release tag delete "${version}"
```

Correct the source and repeat from step 3, using a new revision-specific
artifact directory. Once either service exposes the release, preserve its tag
and artifacts; resume missing steps with the same files, or publish corrected
contents under a new version.


## Troubleshooting<a id="troubleshooting"></a>

- If tests still exercise old code, repeat the non-editable reinstall in
  [Getting started](#getting-started), then use `uv run --no-sync`. Editing
  `src/` alone does not update an installed wheel.
- If custom rules are missing, run the discovery command from the same
  environment as the failing test. Check both package installation and
  `enable_list`; listing a rule does not prove it executes. Do not patch Ansible
  Lint's files or add source paths as a workaround.
- If an autofix test exits with code `8`, check `RC.FIXED_VIOLATIONS`: Ansible
  Lint 26.9.0 uses that code when all findings were fixed. The next lint run
  should return zero. A remaining diagnostic-only finding can still produce code
  `2`.
- If distribution checks fail while unit tests pass, read the failed build or
  subprocess output. Check included files and installed discovery; the check
  deliberately runs outside the source checkout. Network failures can require
  retrying dependency installation, but do not bypass a missing-file or
  discovery assertion.
