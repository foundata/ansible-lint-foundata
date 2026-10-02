# Development

Follow foundata's [Python guide](https://foundata.com/en/guidelines/python/).
Runtime dependencies use lower bounds without speculative upper limits. The
lock file pins development tools, not downstream installations. Python 3.12 is
the minimum; test 3.12, 3.13 and 3.14 before release.

## Local Checks

```sh
uv sync --locked --no-editable --reinstall-package ansible-lint-foundata
uv run --no-sync ruff format --check .
uv run --no-sync ruff check .
uv run --no-sync mypy src tests scripts
uv run --no-sync pytest
uv run --no-sync reuse lint
rumdl check .
uv build
uv run --no-sync python scripts/check_distribution.py
```

Run the sync command after source changes: Ansible Lint discovers physical
directories under its installed package. A source-tree editable installation
alone does not put the discovery adapter there. Never work around this with
`sys.path` edits or by replacing Ansible Lint's own package files.

The wheel contains `ansible_lint_foundata` helpers and a small discovery package
under `ansiblelint.rules.custom.foundata`, but no parent
`ansiblelint/__init__.py`. Each uniquely named discovery module defines its
concrete rule class because the upstream loader verifies the class's source
directory. Put reusable policy logic in the ordinary helper package.

The initial minimum Ansible Lint version is 26.9.0, the tested integration
baseline for discovery, profiles and transforms. Lower it only after the full
compatibility suite passes. Integration tests invoke the installed command in
temporary projects and never operate on the user's collections.

The distribution check requires `uv` on PATH and may download dependencies into
its disposable environment. It checks source-distribution completeness and
verifies that uninstalling this package leaves stock linting intact. Ansible
Lint 26.9.0 returns exit code 8 when all reported violations were fixed; a
subsequent clean check returns zero.

Run the same suite in isolated environments for the supported Python matrix:

```sh
for version in 3.12 3.13 3.14; do
  export UV_PROJECT_ENVIRONMENT=".cache/venvs/$version"
  uv sync --locked --no-editable --python "$version" \
    --reinstall-package ansible-lint-foundata
  uv run --no-sync --python "$version" pytest
done
unset UV_PROJECT_ENVIRONMENT
```

## Commit Scopes

Use one-line scoped subjects following foundata's
[commit guide](https://foundata.com/en/guidelines/git-commits/).
Useful scopes include `repository`, `build`, `rules`, `rules/conditions`,
`rules/permissions`, and `tests`. Do not add attribution trailers.

## Release Boundary

Do not tag 1.0.0 until the
[release acceptance checks](docs/rules.md#release-acceptance) pass. Lint
environments in consumer CI must explicitly require and verify this package;
fallback without it is for optional local use.
