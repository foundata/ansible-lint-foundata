# Rule Contract

This document separates implemented checks from stock coverage, planned checks
and human review. Existing violations, including guide examples, are findings,
not automatic exceptions. Rule IDs and behavior are provisional until 1.0.0.

## Implemented Rules

All rules are opt-in. Stock profiles require explicit `enable_list` entries.
Severity describes impact, not exit status: enabled rules fail unless selected
by `warn_list` or `skip_list`. `strict: true` makes warnings fail too. Enabling
a SHOULD-level rule as a CI error is an explicit project policy decision.

|         Rule ID          | Guide Level |                                                           Scope and Detection                                                           | Autofix |
| ------------------------ | ----------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| foundata-condition-list  | MUST        | Task/block/handler `when`, `changed_when`, `failed_when` values must be lists.                                                          | Wrap strings/booleans only. |
| foundata-handler-listen  | MUST        | Handlers must have nonempty lists of static lowercase topics; uppercase legacy aliases fail.                                            | Wrap a valid scalar topic; never rename. |
| foundata-task-order      | SHOULD      | Documented task keys follow the guide's ordering; unspecified keys retain their slots.                                                  | Reorder ordinary mappings, not YAML merges. |
| foundata-file-mode       | Policy      | Literal permission modes in supported built-in file modules must be absolute symbolic assignments with a matching inline octal comment. | None: mode/comment disagreement needs review. |
| foundata-debug-verbosity | Policy      | Debug tasks explicitly supply `verbosity`; zero is accepted because the guide specifies no minimum.                                     | None.   |
| foundata-no-end-play     | Policy      | Reject `ansible.builtin.meta: end_play`.                                                                                                | None: `end_host` is not equivalent. |
| foundata-task-name       | MUST NOT    | Reject templated play names and references to the current loop variable in a looping task's name.                                       | None.   |

### Boundaries

- Conditions: no splitting of `and`, no runtime type inference, and no rewriting
  of role-list conditions in this alpha. Invalid scalar types remain unfixed.
- Handlers: no cross-file `notify` resolution or public-topic migration. Both
  task files identified as handlers and inline play handlers are checked.
- Ordering: module-parameter ordering is not implemented. Unknown task keys are
  not guessed into undocumented groups. Stock `key-order` remains responsible
  for `name` first and block-related keys last.
- Permissions: check `assemble`, `blockinfile`, `copy`, `file`, `get_url`,
  `lineinfile`, `replace`, `template`, `unarchive` and `uri` from
  `ansible.builtin`. Check explicit module mappings and `args` mappings.
  Dynamic modes require review and are not statically evaluated. Other
  collections and `module_defaults` are not yet covered. `preserve` is not an
  absolute mode and is reported. Comments start with four octal digits, such as
  `# 0644`; subsequent explanation is allowed. All classes must be assigned
  explicitly with `=`; reject relative operations,
  conditional `X`, copied bits and umask-dependent forms. Support explicit
  setuid, setgid and sticky bits in their appropriate classes.
- Names: inherited outer-loop variables across included files are not resolved.
  Malformed Jinja belongs to stock syntax diagnostics, not this rule.

## Stock Coverage

Use `.ansible-lint` and `.yamllint` for indentation, line endings, trailing
whitespace, document markers, line-length ceilings, lowercase YAML booleans,
double-quote preference with the agreed quoted-quote exception, basic names,
module FQCNs, explicit role loop-variable patterns and common command risks.
Do not duplicate those rules here. One blank line between tasks is a guide
preference, not an exact-placement rule. The formatter owns mechanical layout.

## Planned Checks

These remain guide obligations, not implemented coverage claims:

- Context-aware quoting and broader Jinja style coverage.
- Jinja plugin FQCNs, dictionary retrieval and injected-fact references.
- Template `tpl_*` inputs, allowing documented globals and local template names.
- Parsed top-level `and` diagnostics, explicit predicates and categorical facts.
- Module-parameter order and additional mapping-form argument checks.
- Internal-variable scope and cross-file nested-loop collisions.
- Selective `with_*` migration preserving lookup and flattening semantics.
- Command interpolation, `argv`, and overwriting input variables with
  `set_fact`.
- Contextual file naming, loader extensions and comment structure.

Implement these only with explicit scope and regression fixtures. Do not use
regular expressions as substitutes for YAML/Jinja parsing or pretend that
dynamic references can always be resolved statically.

## Review and Runtime Checks

Integration tests must establish idempotency and operation without pre-gathered
facts. Review establishes justified module choices, useful comments, sensible
template decomposition and meaningful runtime types. ShellCheck complements
the unchanged Bash/POSIX and shell error-handling policies. Structured output
uses native data and serialization filters, not manually interpolated JSON/YAML.

## Release Acceptance

- Keep positive/negative fixtures for every rule, including real-world findings.
- Test fix output, comment retention, semantic values and second-pass stability.
- Run installed-package CLI tests with and without configuration/package, and
  with a production profile. Assert that stock rules remain available.
- Build wheel and sdist, install the wheel outside the checkout, and verify all
  expected rule IDs are discovered. Rebuild the sdist to check its completeness.
- Test Python 3.12, 3.13 and 3.14 and both the supported lower dependency bound
  and the locked development environment before claiming compatibility.
