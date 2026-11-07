# Rule contract

<!--
SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
SPDX-License-Identifier: GPL-3.0-or-later
-->

Rules apply to existing violations, including guideline examples.

## Table of contents

- [Implemented rules](#implemented-rules)
  - [Boundaries](#boundaries)
- [Stock coverage](#stock-coverage)
  - [Compatible task ordering](#compatible-task-ordering)
- [Planned checks](#planned-checks)
- [Review and runtime checks](#review-and-runtime-checks)
- [Release acceptance](#release-acceptance)


## Implemented rules<a id="implemented-rules"></a>

All rules are opt-in, including under stock profiles: add `enable_list` entries.
Severity describes impact. Enabled rules fail unless listed in `warn_list` or
`skip_list`; with `strict: true`, warnings also fail. Explicitly adopt and
document any SHOULD-level rules enforced as CI errors.

|          Rule ID           | Guide level |                                                     Scope and detection                                                     | Autofix |
| -------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------- | ------- |
| `foundata-condition-list`  | MUST        | Require lists for task/block/handler `when`, `changed_when`, `failed_when`, `until`.                                        | Wrap strings/booleans only. |
| `foundata-condition-bool`  | MUST        | Reject provably nonboolean condition results without evaluating variables or plugins.                                       | None.   |
| `foundata-handler-listen`  | MUST        | Require scoped topic lists; allow documented broadcasts.                                                                    | Wrap a valid scalar topic; never rename. |
| `foundata-task-order`      | SHOULD      | Order middle task keys, retaining unknown keys' relative slots.                                                             | None: stock owns ordering autofix. |
| `foundata-file-mode`       | Policy      | Require absolute symbolic permission modes with matching inline octal comments in supported built-in file modules.          | None: resolve mode/comment disagreements manually. |
| `foundata-debug-verbosity` | MUST        | Require explicit `verbosity`; allow zero for normal-run output.                                                             | None.   |
| `foundata-no-end-play`     | Policy      | Require reviewed caller-termination exceptions for reusable content; check orchestration explanations and `end_role` scope. | None: `end_host` is not equivalent. |
| `foundata-task-name`       | MUST NOT    | Reject templated play names and current-loop variable references in task names.                                             | None.   |
| `foundata-jinja-fqcn`      | MUST        | Check literal filter/test/lookup names in task templates and implicit conditions, including higher-order plugin arguments.  | None: review provider resolution. |
| `foundata-template-inputs` | MUST        | Require `tpl_*` external inputs in selected Jinja files; exempt lexical locals and native Jinja globals.                    | None: inputs define the interface. |
| `foundata-command-argv`    | MUST NOT    | Reject shell-quoting filters in `ansible.builtin.command` or `ansible.legacy.command` argv expressions.                     | None: preserve arguments for review. |
| `foundata-fact-vars`       | MUST        | Check known injected fact references in task expressions, play vars and vars files.                                         | None: review host and variable scope. |
| `foundata-notify`          | MUST        | Resolve static local notifications; reject name coupling and missing targets in closed plays.                               | None: never rename topics. |
| `foundata-loop-collision`  | MUST        | Detect loop/index bindings that shadow outer include/role loop bindings.                                                    | None: renaming changes references. |
| `foundata-set-fact`        | SHOULD      | Reject overwrites of statically declared task/play variables, role defaults/vars and role argument options.                 | None: choose a separate state variable. |
| `foundata-string-quotes`   | SHOULD      | Check ordinary task string values, excluding implicit expressions and binding identifiers.                                  | None.   |
| `foundata-parameter-order` | SHOULD      | Group parameters of supported built-in modules, without sorting application data.                                           | None.   |

### Boundaries<a id="boundaries"></a>

- Conditions: both rules cover `when`, `changed_when`, `failed_when` and
  `until`. The boolean check also covers `assert.that`. It rejects literal
  nonbooleans and expressions whose branches are all known nonboolean, without
  evaluating plugins or inferring runtime types. Neither rule splits `and`,
  rewrites role-list conditions or fixes invalid scalar types. Fixes preserve
  anchored booleans and other scalar alias uses. Review mixed AND/OR grouping
  and command-specific exit codes separately.
- Handlers: check handler files and inline play handlers. Exempt static
  `import_tasks` directives, but check their handlers. Dynamic `include_tasks`
  handlers need topics on the include itself. The rule follows literal static
  imports, including nested imports missed by stock discovery. It detects
  cycles and uses stock path resolution and exclusions.
  Recognized roles require `role[_collection]_<action>_<object>` topics.
  Adjacent `Shared broadcast` comments permit intentional shared topics. Review
  the stated purpose.
  Unknown role layouts retain lowercase checks; use an explained local
  suppression for a different public prefix. Topics are never renamed.
- Graph checks: follow literal local task includes and imports, role entry
  points and dependencies, with separate play namespaces and include-loop
  contexts. Respect exclusions and project boundaries; cap traversal at 128 file
  contexts and 5,000 tasks. Dynamic/external references, cycles and limits leave
  the graph open. Missing notification targets are reported only in fully
  resolved plays; reusable roles may notify external topics. References to known
  handler names are still reported. Role resolution covers conventional local
  paths; custom search paths remain unresolved.
- Ordering: stock `key-order` owns `name` first and `block`, `rescue`, `always`
  last. Report only additional violations. The separate parameter rule covers
  `file`, `template`, `copy`, `debug`, `command`, `shell`, `service`, `systemd`,
  `systemd_service`, `package`, `apt`, `dnf`, `uri` and `get_url`. Keep primary
  parameters' relative order, then `owner`, `group`, `mode`, then alphabetized
  optional parameters. Inspect direct module and argument mappings only; skip
  YAML merges, unknown interfaces and nested application data. This advisory
  rule and string quoting are not enabled in the consumer example; adopt them
  separately.
- Permissions: cover `assemble`, `blockinfile`, `copy`, `file`, `get_url`,
  `lineinfile`, `replace`, `template`, `unarchive` and `uri` through
  `ansible.builtin`, `ansible.legacy` and normalized short names, in module,
  `action`, `local_action` and `args` mappings. YAML merges use the defining
  mapping's comment and source line, including nested merges and overrides. Put
  octal comments at literal definitions, not uses. The rule does not support
  other collections, even when module basenames match, or `module_defaults`.
  Review dynamic modes; the rule does not evaluate expressions. For unmodified
  variable or literal mapping references, inspect task/play/block declarations,
  literal `vars_files` and role `defaults/main`/`vars/main` definitions. Check
  comments at definitions and report their locations in the diagnostic at the
  task. The rule does not simulate variable precedence or resolve dynamic
  includes and lookups. Mode comments must start with four octal digits, such as
  `# 0644`, optionally followed by an explanation. Assign every class with `=`;
  relative operations, conditional `X`, copied bits and umask-dependent forms
  fail. Explicit setuid, setgid and sticky bits are supported in their
  appropriate classes. `preserve` fails because it is not absolute. Copies that
  stage artifacts needing source permissions may use task-local
  `# noqa: foundata-file-mode` with an adjacent explanation. Review must confirm
  the exception; the rule does not infer intent from task names, paths or
  comments.
- Debug output: require `verbosity`. Review decides between normal output
  (`0`) and diagnostics (`1` or higher).
- Play termination: require a reviewed task-local `# noqa: foundata-no-end-play`
  for `end_play`/`end_host` in roles or task files whose caller scope is
  unknown. Direct orchestration tasks require an adjacent explanation; review
  its meaning. Reject `end_role` outside recognized roles or inside handlers.
  Review compatibility with the declared minimum core version. Never
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
- Template inputs: follow literal local includes, imports and inheritance with
  lexical locals and context-free macro interfaces. Honor root delimiter headers
  and literal task overrides. Check unconditional input references against task
  `vars`; optional/defaulted inputs, conditional branches and macro execution
  remain runtime concerns. Static parents own fragment analysis; standalone
  fragments without discoverable callers may need an explained first-line
  `noqa: foundata-template-inputs`. Exclusions, dynamic paths, cycles and the
  128-visit limit leave requirements unresolved. Invalid syntax is reported as
  `[unresolved]`. Renderer metadata has no exemption. Exclude unrelated
  application templates; no templates or bindings are rewritten.
- Command argv: check `quote` filter calls and literal higher-order uses. The
  rule does not infer intent from literal quote characters, inspect dynamic
  argv definitions or rewrite shell command strings.
- Facts: check an explicit catalog of built-in aliases, including direct names,
  literal `vars` lookups and `hostvars` access. Honor Jinja locals. Unknown
  aliases, dynamic variable names and fact freshness remain review concerns;
  magic and connection variables are not rejected by their prefix.
- Input overwrites: check `set_fact` against the literal variable declarations
  described under permissions and against role argument specifications.
  Runtime-only caller inputs and arbitrary `include_vars` files remain
  unresolved. Application dictionary contents and
  newly computed variables are not treated as declared inputs.


## Stock coverage<a id="stock-coverage"></a>

Use `.ansible-lint` and `.yamllint` for indentation, line endings, trailing
whitespace, document markers, line-length ceilings, lowercase YAML booleans,
double-quote preference with an exception for strings containing double quotes,
basic names, module FQCNs, explicit role loop-variable patterns and common
command risks. Do not duplicate stock checks. The formatter controls layout; one
blank line between tasks is a guide preference, not an exact-placement rule.

The optional string-quote rule checks task values, not structural keys. It
exempts conditions, `assert.that`, `debug.var`, register names and loop/index
bindings. It accepts quoted expressions and block scalars. Standalone vars files
and play keywords remain review concerns. Stock owns quote style; neither custom
style rule rewrites values or order. Explain readability exceptions with local
skips.

### Compatible task ordering<a id="compatible-task-ordering"></a>

The extension adds constraints to stock
[`key-order`](https://docs.ansible.com/projects/lint/rules/key-order/):

1. Stock owns `name` first and the terminal `block`, `rescue`, `always` group.
2. Order middle keys by context/action, arguments/variables/environment,
   conditions, loops, results, notifications and tags, following the guide's
   detailed list.
3. Keep unknown keys' relative slots in the middle group. They cannot displace
   `name` or follow block-related keys.
4. Do not extend play ordering or recursively sort module parameters.

Keep stock `key-order` enabled. `foundata-task-order` is diagnostic-only;
apply its suggested middle-key order manually.


## Planned checks<a id="planned-checks"></a>

These checks are not implemented. The guideline requirements still apply:

- Quoting outside tasks and broader Jinja style coverage.
- Jinja plugin coverage outside tasks and dictionary retrieval.
- Parsed top-level `and` diagnostics, explicit predicates and categorical facts.
- Additional module interfaces and mapping-form argument checks.
- Internal-variable scope beyond statically resolved loop collisions.
- Selective `with_*` migration preserving lookup and flattening semantics.
- Command interpolation and literal-dollar expansion.
- Contextual file naming, loader extensions and comment structure.

Define scope and regression fixtures before implementation. Parse YAML/Jinja
instead of approximating it with regular expressions. Static analysis cannot
resolve every dynamic reference.


## Review and runtime checks<a id="review-and-runtime-checks"></a>

Integration tests must verify configuration convergence and operation without
pre-gathered facts, with fact injection disabled. Cover missing facts and stale
values requiring a refresh; presence checks do not establish freshness. Review
required fact keys separately from collection selectors. Static alias checks
cannot establish whether required facts were collected or remain current.

Intentionally repeatable operations need an explicit trigger or documented
purpose and accurate change reporting. `changed_when: false` cannot make a
mutating operation idempotent.

Review module choices, comment usefulness, template structure and runtime
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


## Release acceptance<a id="release-acceptance"></a>

- Keep positive/negative fixtures for every rule, including real-world findings.
- Test fix output, comment retention, semantic values and second-pass stability.
- Test the installed CLI with and without the configuration and package, and
  under a production profile. Verify stock rules remain available.
- Build wheel and sdist, install the wheel outside the checkout and verify
  discovery of every expected rule ID. Rebuild the sdist to check completeness.
- Before claiming compatibility, test Python 3.12, 3.13 and 3.14, the supported
  lower dependency bound and the locked development environment.
