# Rule contract

Rule IDs and behavior are provisional until 1.0.0. Existing violations,
including guide examples, receive no automatic exemptions.

## Implemented rules

All rules are opt-in, including under stock profiles: add `enable_list` entries.
Severity describes impact; enabled rules fail unless in `warn_list` or
`skip_list`. With `strict: true`, warnings also fail. Projects must explicitly
adopt and document SHOULD-level rules enforced as CI errors.

|         Rule ID          | Guide level |                                                     Scope and detection                                                     | Autofix |
| ------------------------ | ----------- | --------------------------------------------------------------------------------------------------------------------------- | ------- |
| foundata-condition-list  | MUST        | Require lists for task/block/handler `when`, `changed_when`, `failed_when`, `until`.                                        | Wrap strings/booleans only. |
| foundata-condition-bool  | MUST        | Reject provably nonboolean condition results without evaluating variables or plugins.                                       | None.   |
| foundata-handler-listen  | MUST        | Require nonempty lists of static lowercase handler topics, including legacy aliases.                                        | Wrap a valid scalar topic; never rename. |
| foundata-task-order      | SHOULD      | Order middle task keys, retaining unknown keys' relative slots.                                                             | None: stock owns ordering autofix. |
| foundata-file-mode       | Policy      | Require absolute symbolic permission modes with matching inline octal comments in supported built-in file modules.          | None: resolve mode/comment disagreements manually. |
| foundata-debug-verbosity | MUST        | Require explicit `verbosity`; allow zero for normal-run output.                                                             | None.   |
| foundata-no-end-play     | Policy      | Require reviewed caller-termination exceptions for reusable content; check orchestration explanations and `end_role` scope. | None: `end_host` is not equivalent. |
| foundata-task-name       | MUST NOT    | Reject templated play names and current-loop variable references in task names.                                             | None.   |
| foundata-jinja-fqcn      | MUST        | Check literal filter/test/lookup names in task templates and implicit conditions, including higher-order plugin arguments.  | None: review provider resolution. |
| foundata-template-inputs | MUST        | Require `tpl_*` external inputs in selected Jinja files; exempt lexical locals and native Jinja globals.                    | None: inputs define the interface. |
| foundata-command-argv    | MUST NOT    | Reject shell-quoting filters in `ansible.builtin.command` or `ansible.legacy.command` argv expressions.                     | None: preserve arguments for review. |

### Boundaries

- Conditions: cover `when`, `changed_when`, `failed_when` and `until`. Boolean
  checks reject literal nonbooleans and expressions whose branches are all
  known nonboolean. They do not evaluate plugins or infer runtime types.
  Neither rule splits `and`, rewrites
  role-list conditions or fix invalid scalar types. Fixes preserve anchored
  booleans and other scalar alias uses. Review mixed AND/OR grouping and
  command-specific exit codes separately.
- Handlers: check handler files and inline play handlers. Exempt static
  `import_tasks` directives, but check their handlers. Dynamic `include_tasks`
  handlers need topics on the include itself. Follow literal static imports,
  including nested imports missed by stock discovery, with cycle protection
  and stock path resolution/exclusions. No dynamic-path inference, cross-file
  `notify` resolution (including multiple parents) or public-topic migration.
  Topic prefixes, actions and objects are not yet checked. The guideline permits
  documented migration aliases, but this check still rejects mixed-case values.
  Use task-local `# noqa: foundata-handler-listen` for such aliases, with an
  adjacent migration comment and documented removal version; review the other
  handler requirements manually.
- Ordering: stock `key-order` owns `name` first and `block`, `rescue`, `always`
  last. Report only additional violations. Module-parameter ordering and
  undocumented groups for unknown keys are outside scope. The guide's optional
  parameter alphabetization is advisory; it excludes application data in
  `vars`, `set_fact` assignments and nested payloads.
- Permissions: cover `assemble`, `blockinfile`, `copy`, `file`, `get_url`,
  `lineinfile`, `replace`, `template`, `unarchive` and `uri` through
  `ansible.builtin`, `ansible.legacy` and normalized short names, in module,
  `action`, `local_action` and `args` mappings. YAML merges use the defining
  mapping's comment and source line, including nested merges and overrides.
  Put octal comments at literal definitions, not uses. Other collections
  (including basename matches) and `module_defaults` are unsupported. Review
  dynamic modes and variable definitions; the rule does not evaluate them.
  Mode comments must start with four octal digits, such as `# 0644`, optionally
  followed by an explanation. Assign every class with `=`; relative operations,
  conditional `X`, copied bits and umask-dependent forms fail. Explicit setuid,
  setgid and sticky bits are supported in their appropriate classes.
  `preserve` fails because it is not absolute. Artifact-staging copies needing
  source permissions may use task-local `# noqa: foundata-file-mode` with an
  adjacent explanation. Review must confirm the exception; the rule does not
  infer intent from task names, paths or comments.
- Debug output: check for `verbosity`. Review decides between normal output
  (`0`) and diagnostics (`1` or higher).
- Play termination: require a reviewed task-local `# noqa: foundata-no-end-play`
  for `end_play`/`end_host` in roles or task files whose caller scope is
  unknown. Direct orchestration tasks require an adjacent explanation; review
  its meaning. Reject `end_role` outside recognized roles or inside handlers.
  Declared minimum core-version compatibility remains a review concern. Never
  substitute `end_host` just to avoid a finding.
- Names: exclude Jinja loop/macro/assignment locals. Check static
  `vars['name']`, `lookup`/`query`/`q` calls to `vars`, the current loop's index
  variable and `ansible_loop` metadata. Review dynamically constructed names and
  inherited outer-loop variables across included files. Stock rules diagnose
  malformed Jinja.
- Jinja FQCNs: report literal plugin names at task level, including `map`,
  `select`, `reject`, `selectattr`, `rejectattr` and lookup/query/q arguments.
  Exempt native globals and comparison-operator test aliases. Review dynamic
  names, plugin availability, canonical aliases, play variables, vars files
  and template-file plugin calls. Never rewrite qualified third-party names
  to builtins.
- Template inputs: treat selected `.j2` files as Ansible templates. Support
  literal delimiter headers; report invalid or unsupported syntax as
  `[unresolved]`. Renderer-provided metadata has no exemption. Call-site input
  completeness, imports/includes/inheritance and task-specific delimiter
  overrides are unchecked. Inherited template-local values may be reported as
  external inputs. Exclude unrelated application templates. For these false
  positives or intentionally different interfaces, use first-line
  `noqa: foundata-template-inputs` comments with an explanation.
- Command argv: check `quote` filter calls and literal higher-order uses. Do not
  infer intent from literal quote characters, inspect dynamic argv definitions
  or rewrite shell command strings.

## Stock coverage

Use `.ansible-lint` and `.yamllint` for indentation, line endings, trailing
whitespace, document markers, line-length ceilings, lowercase YAML booleans,
double-quote preference with the agreed quoted-quote exception, basic names,
module FQCNs, explicit role loop-variable patterns and common command risks.
Do not duplicate stock checks. The formatter controls layout; one blank line
between tasks is a guide preference, not an exact-placement rule.

Context-aware quote checks are not implemented. Distinguish ordinary string
values from structural keys, identifiers and implicit Jinja expressions; allow
YAML-required outer quotes. Preserve parsed values and avoid blanket quote
insertion.

### Compatible task ordering

The extension adds constraints to stock
[`key-order`](https://docs.ansible.com/projects/lint/rules/key-order/):

1. Stock owns `name` first and the terminal `block`, `rescue`, `always` group.
2. Order middle keys by context/action, arguments/variables/environment,
   conditions, loops, results, notifications and tags, following the guide's
   detailed list.
3. Keep unknown keys' relative slots in the middle group. They cannot displace
   `name` or follow block-related keys.
4. Do not extend play ordering or recursively sort module parameters.

This alpha removes the task-order autofix: Ansible Lint 26.9.0 replays stock's
key order captured before other fixes, potentially undoing an extension's
transform while both report success. The extension is diagnostic-only, leaving
stock's fix intact and reporting remaining violations. Repeated fixes must be
byte-stable. Do not disable stock, monkey-patch rules or coordinate transforms
through diagnostic sort order. Combined autofix requires a tested upstream
composition mechanism.

## Planned checks

Not yet implemented; guideline obligations still apply:

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

Define scope and regression fixtures before implementation. Parse YAML/Jinja
instead of approximating it with regular expressions. Static analysis cannot
resolve every dynamic reference.

## Review and runtime checks

Integration tests must verify configuration convergence and operation without
pre-gathered facts, with fact injection disabled. Cover missing facts and stale
values requiring a refresh; presence checks do not establish freshness. Review
required fact keys separately from collection selectors. Injected-alias checks
are not implemented; a blanket `ansible_*` ban would also reject valid magic
and connection variables.

Intentionally repeatable operations need an explicit trigger or documented
purpose and accurate change reporting. `changed_when: false` cannot make a
mutating operation idempotent.

Review module choices, comment usefulness, template decomposition and runtime
types. Boolean conversion requires supported inputs; Python truthiness is a
separate choice. Literal command arguments need `expand_argument_vars: false`
and no shell quoting in `argv`. ShellCheck covers shell syntax and dialect
checks; review Bash availability, shell-version requirements and explicit error
handling separately. Keep stock `risky-shell-pipe` enabled and test critical
failure paths on supported shells. Use native data and serialization filters
for structured output.

Keep suppressions local, rule-specific and explained for allowed exceptions or
false positives. Required CI must check discovery with
`ansible-lint --list-rules --format brief` and execution with known-invalid
fixtures in its lint environment. Listing bypasses profile filtering and does
not prove execution. Integration tests verify the published consumer
configuration this way.

## Release acceptance

- Keep positive/negative fixtures for every rule, including real-world findings.
- Test fix output, comment retention, semantic values and second-pass stability.
- Test the installed CLI with and without configuration/package, and under a
  production profile. Verify stock rules remain available.
- Build wheel and sdist, install the wheel outside the checkout and verify
  discovery of every expected rule ID. Rebuild the sdist to check completeness.
- Before claiming compatibility, test Python 3.12, 3.13 and 3.14, the supported
  lower dependency bound and the locked development environment.
