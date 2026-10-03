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
| foundata-task-order      | SHOULD      | Extend stock ordering within the middle task keys; retain unknown keys' relative slots in that group.                                   | None: stock owns ordering autofix. |
| foundata-file-mode       | Policy      | Literal permission modes in supported built-in file modules must be absolute symbolic assignments with a matching inline octal comment. | None: mode/comment disagreement needs review. |
| foundata-debug-verbosity | MUST        | Debug tasks explicitly supply `verbosity`; zero is accepted for output intended for normal runs.                                        | None.   |
| foundata-no-end-play     | Policy      | Reject `ansible.builtin.meta: end_play`.                                                                                                | None: `end_host` is not equivalent. |
| foundata-task-name       | MUST NOT    | Reject templated play names and references to the current loop variable in a looping task's name.                                       | None.   |
| foundata-jinja-fqcn      | MUST        | Check literal filter/test/lookup names in task templates and implicit conditions, including higher-order plugin arguments.              | None: provider resolution requires review. |
| foundata-template-inputs | MUST        | Selected Jinja files use `tpl_*` external inputs, exempting lexical locals and native Jinja globals.                                    | None: changing inputs changes the interface. |
| foundata-command-argv    | MUST NOT    | Reject shell-quoting filters applied in `ansible.builtin.command` or `ansible.legacy.command` argv expressions.                         | None: preserve argument values for review. |

### Boundaries

- Conditions: no splitting of `and`, no runtime type inference, and no rewriting
  of role-list conditions in this alpha. Invalid scalar types remain unfixed.
  Anchored booleans retain their boolean type and other scalar alias uses.
- Handlers: no cross-file `notify` resolution or public-topic migration. Both
  task files identified as handlers and inline play handlers are checked.
  Static `import_tasks` directives are exempt; their imported handlers are not.
  Dynamic `include_tasks` handlers need topics on the include itself.
  Literal static imports are followed with cycle protection and the stock path
  resolver/exclusions, including nested imports stock discovery does not visit.
  Dynamic paths and multi-parent notification resolution are not inferred.
- Ordering: module-parameter ordering is not implemented. Unknown task keys are
  not guessed into undocumented groups. Stock `key-order` remains responsible
  for `name` first and `block`, `rescue`, `always` last. The extension reports
  only additional ordering violations, not stock-only violations.
- Permissions: check `assemble`, `blockinfile`, `copy`, `file`, `get_url`,
  `lineinfile`, `replace`, `template`, `unarchive` and `uri` from
  `ansible.builtin` and `ansible.legacy`, as well as normalized short names.
  Check explicit module, `action`, `local_action` and `args` mappings. YAML
  merges use the defining mapping's comment and source line, including nested
  merges and local overrides. Other collections are not matched by basename.
  Dynamic modes and their variable definitions require review and are not
  statically evaluated. Put the octal comment at the literal definition, not at
  each use. Other collections and `module_defaults` are not yet covered.
  `preserve` is not an absolute mode and is reported. The guide permits a
  task-local `# noqa: foundata-file-mode` for artifact-staging copies that must
  retain source-file permissions, with an adjacent explanation. Review must
  establish that the exception applies; the rule does not infer intent from a
  task name, path or comment. Comments on absolute modes start with four octal
  digits, such as `# 0644`; subsequent explanation is allowed. All classes must
  be assigned explicitly with `=`; reject relative operations, conditional `X`,
  copied bits and umask-dependent forms. Support explicit setuid, setgid and
  sticky bits in their appropriate classes.
- Debug output: the rule checks that `verbosity` is present. Review determines
  whether output belongs in a normal run (`0`) or is diagnostic (`1` or higher).
- Names: inherited outer-loop variables across included files are not resolved.
  Jinja loop/macro/assignment locals do not count as Ansible inputs. Static
  `vars['name']` and `lookup`/`query`/`q` calls to the `vars` plugin are
  checked, as are the current loop's index variable and `ansible_loop` metadata.
  Dynamically constructed variable names require review. Malformed Jinja belongs
  to stock syntax diagnostics, not this rule.
- Jinja FQCNs: task-level diagnostics cover literal plugin names, including
  `map`, `select`, `reject`, `selectattr`, `rejectattr` and lookup/query/q
  arguments. Native globals and comparison-operator test aliases are not
  collection names. Dynamic plugin names, plugin availability, canonical alias
  resolution, play variables, vars files and template-file plugin calls remain
  review concerns. Qualified third-party names are never rewritten to builtins.
- Template inputs: selected `.j2` files are treated as Ansible templates.
  Literal delimiter headers are supported; invalid or unsupported syntax is an
  explicit `[unresolved]` finding, not a clean result. This does not yet prove
  that calling tasks supply every input, resolve imports/includes, or account
  for task-specific delimiter overrides. Exclude unrelated application
  templates from this opt-in check.
  A first-line `noqa: foundata-template-inputs` comment suppresses the check for
  an intentionally different template interface; explain the exception there.
- Command argv: check `quote` filter calls and literal higher-order uses in
  argv expressions. Do not infer intent from literal quote characters, inspect
  dynamically supplied argv definitions, or rewrite shell command strings.

## Stock Coverage

Use `.ansible-lint` and `.yamllint` for indentation, line endings, trailing
whitespace, document markers, line-length ceilings, lowercase YAML booleans,
double-quote preference with the agreed quoted-quote exception, basic names,
module FQCNs, explicit role loop-variable patterns and common command risks.
Do not duplicate those rules here. One blank line between tasks is a guide
preference, not an exact-placement rule. The formatter owns mechanical layout.

### Compatible Task Ordering

The extension refines, rather than replaces, stock
[`key-order`](https://docs.ansible.com/projects/lint/rules/key-order/):

1. Stock owns `name` first and the terminal `block`, `rescue`, `always` group.
2. Within the remaining middle group, order documented keys as context/action,
   arguments/variables/environment, conditions, loops, results, notifications,
   and tags, following the guideline's detailed list.
3. Leave unknown keys in their relative slots within that middle group. An
   unknown key can never displace `name` or follow a block-related key.
4. Do not extend play-level ordering or recursively sort module parameters.

This alpha deliberately removes the previous task-order autofix. In Ansible
Lint 26.9.0, stock's transform replays a key order captured before other fixes;
it can undo an extension's transform while both claim success. A diagnostic-only
extension leaves stock's fix intact and continues reporting any remaining
extension violation. Repeated fix runs must be byte-stable, not alternate
between ordering policies. Do not disable stock, monkey-patch its rules, or
depend on diagnostic sort order to coordinate transforms. Combined autofix can
return after an upstream composition mechanism is available and tested.

## Planned Checks

These remain guide obligations, not implemented coverage claims:

- Context-aware quoting and broader Jinja style coverage.
- Jinja plugin coverage outside tasks, dictionary retrieval and injected facts.
- Template call-site input completeness, imports/includes and task-specific
  delimiter overrides.
- Parsed top-level `and` diagnostics, explicit predicates and categorical facts.
- Module-parameter order and additional mapping-form argument checks.
- Internal-variable scope and cross-file nested-loop collisions.
- Selective `with_*` migration preserving lookup and flattening semantics.
- Command interpolation, literal-dollar expansion, and overwriting inputs with
  `set_fact`.
- Contextual file naming, loader extensions and comment structure.

Implement these only with explicit scope and regression fixtures. Do not use
regular expressions as substitutes for YAML/Jinja parsing or pretend that
dynamic references can always be resolved statically.

## Review and Runtime Checks

Integration tests must establish convergence for configuration automation and
operation without pre-gathered facts. Review intentionally repeatable operations
for an explicit trigger or documented purpose, and verify that change reporting
reflects actual behavior. `changed_when: false` cannot make a mutating operation
idempotent.

Review also covers module choices, useful comments, template decomposition and
runtime types. Boolean conversion must use supported input representations;
Python truthiness is a separate choice. Literal command arguments need
`expand_argument_vars: false` and no shell quoting in `argv`. ShellCheck
complements the unchanged Bash/POSIX and shell error-handling policies.
Structured output uses native data and serialization filters.

Projects must document which SHOULD-level recommendations they enforce as
errors. Keep suppressions local and specific, with an explanation for an allowed
exception or false positive. Required CI must verify discovery with
`ansible-lint --list-rules --format brief` and execution with known-invalid
fixtures in the environment used for linting. The listing bypasses profile
filtering and does not prove that an installed rule runs. The published
consumer configuration is exercised this way by integration tests.

## Release Acceptance

- Keep positive/negative fixtures for every rule, including real-world findings.
- Test fix output, comment retention, semantic values and second-pass stability.
- Run installed-package CLI tests with and without configuration/package, and
  with a production profile. Assert that stock rules remain available.
- Build wheel and sdist, install the wheel outside the checkout, and verify all
  expected rule IDs are discovered. Rebuild the sdist to check its completeness.
- Test Python 3.12, 3.13 and 3.14 and both the supported lower dependency bound
  and the locked development environment before claiming compatibility.

## Proposed Guideline Revisions

The following are policy proposals, not silently adopted rule changes. They
are distinct from the stock-compatibility corrections already made in the
guideline. Decide these interfaces before implementing cross-file enforcement.

|         Area          |                                                                                                                                   Recommended change                                                                                                                                    | Enforcement consequence |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| Handler topics        | Namespace new role topics by their public role/collection prefix. Keep intentional shared broadcast topics explicit. Treat published topics as interfaces: allow documented, time-bounded legacy aliases during a migration instead of requiring an immediate breaking rename.          | Resolve literal notifications against a bounded role/play graph. Dynamic includes and external handlers must remain unresolved, not missing. Never rename topics automatically. |
| Play termination      | Prohibit `end_play` and `end_host` inside reusable roles unless stopping their caller is an explicit contract. Prefer role-local control flow or `end_role` where the supported core version permits it. Allow deliberately play-wide termination in orchestration with an explanation. | Replace the blanket ban only after defining role versus orchestration scope. `end_host` still ends the rest of the play for that host and is not a general safe replacement. |
| Static files          | Use `copy` for static files and `template` when rendering is actually needed; remove the preemptive-template recommendation.                                                                                                                                                            | Avoid a rule that recommends rendering otherwise literal file content merely for possible future use. |
| Permission notation   | Consider permitting quoted four-digit octal modes alongside complete absolute symbolic modes. Make the duplicate octal comment optional if symbolic notation remains preferred. Keep explicit ownership/permissions and narrowly documented preservation exceptions.                    | Separate deterministic permission semantics from notation preference. Quoted octal is supported by Ansible and stock lint; this proposal is not a reason to relax the current rule silently. |
| Template interfaces   | Keep explicit inputs, but distinguish external data from native Jinja facilities, locally declared names and renderer-provided metadata. Define how imports, includes, macros and alternative delimiters inherit the input interface.                                                   | Add task-to-template input completeness only for statically resolved call sites. Dynamic paths and runtime values require an explicit unresolved boundary. |
| Shell execution       | State whether Bash availability is a supported-platform requirement. Otherwise use POSIX shell by default and require a capable shell for pipelines that need pipefail. Treat `set -e` as contextual, not a substitute for error handling.                                              | Keep stock pipeline checks; use ShellCheck for shell syntax instead of building another shell parser. Test critical statuses and substitutions. |
| Conditions            | Explicitly include `until` and explain that lists are AND, especially for `failed_when` and `changed_when`. Show a single list item containing OR for alternative failures. Preserve task-status versus process-exit-status distinctions.                                               | Check definitely nonboolean literals first; do not reject unknown variables or split mixed AND/OR expressions automatically. |
| Facts                 | Separate required fact keys from collector subsets. Show `!all` and `!min` when the example promises to collect only selected subsets, and document freshness requirements rather than treating presence as freshness.                                                                  | Check known injected fact names, not every `ansible_*` variable. Runtime tests remain necessary for missing or stale facts. |
| Quoting and ordering  | Define exceptions by syntax context, not the phrase "local Ansible environment". Keep optional-parameter alphabetization advisory; clarify that it never applies to arbitrary application data.                                                                                         | Avoid blanket quote insertion and recursive dictionary sorting. The stock formatter remains authoritative. |
| Examples and adoption | Test complete positive examples against the adopted configuration; label incomplete snippets and their prerequisites. Record the guideline revision and supported core/lint versions alongside adopted rule IDs.                                                                        | Catch stale examples and changes in upstream behavior, including rules listed in profiles but not yet implemented. |

After those decisions, prioritize a cycle-safe static file graph for template
inputs, notifications and nested loop-variable collisions. Follow it with
literal variable-mode definitions and input/default collisions in `set_fact`.
Keep unknown dynamic references visible as unresolved review work. Lower-value
style checks, such as contextual quoting and optional parameter order, come
last and should not change execution semantics.
