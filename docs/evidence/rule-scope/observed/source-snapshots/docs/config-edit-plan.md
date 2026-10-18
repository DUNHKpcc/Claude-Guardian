# Private configuration edit candidates

Requirements: ENV-02 / ENV-06, D-ENV §5.3–5.6, D-SPEC M04/M06.

`skills/claude-guardian/scripts/config_edit_plan.py` bridges an original
`remedy_plans` request to exact candidate bytes. It is an offline library, with no
CLI, file reads/writes, native controller calls, transaction execution, or apply
interface. All inputs and tests are synthetic. This does not close native
compatibility, ownership, GUI merge/readback, route verification, or authorization
acceptance criteria.

## Supported slice

- An existing caller-supplied UTF-8 YAML snapshot, declared to be an owned profile
  extension, whose SHA-256 exactly matches the selected remedy revision layer
- `keep-existing` with exactly one `bind_selected_rules` proposal and no semantic
  blockers except the three mandatory adapter/version/native-acceptance blockers
- Existing, unique, plain single-line `DOMAIN` or `DOMAIN-SUFFIX` rules with exactly
  three comma-separated fields; only the last policy token can change
- ASCII domain tokens with nonempty labels of at most 63 characters and no
  leading/trailing label hyphens, and ASCII policy names matching the implementation's bounded
  patterns; no rule creation, removal, reordering, modifiers, arbitrary keys, DNS,
  mode, TUN, subscription source or generated runtime configuration edits
- The selected group must appear uniquely in the same snapshot's `proxy-groups`;
  the current minimal binding requires its name to equal the semantic egress alias
  (extensions referencing an external group are not supported)

Quoted or multiline selected scalars, flow-style root/rule lists, YAML directives,
multiple documents, anchors/aliases, explicit tags, merge keys, duplicate keys at
any nesting depth, ambiguous selected rules and duplicate group names are refused. Duplicate-selector
checks conservatively fold case, strip comma-field whitespace and ignore trailing
DNS root dots across all scalar rules, without broadening the editable grammar.
An earlier MATCH or covering DOMAIN-SUFFIX rule is rejected as a provable
first-match conflict. This conservative local check is not a full rule graph,
RULE-SET/IP/logical-rule analysis or verification of the final merged ordering.
Unknown unrelated fields are preserved. Input is bounded at 4 MiB, 20,000 parser
events and 48 container levels. PyYAML is optional, already pinned in the existing
development dependencies; missing parser returns a fixed error and never installs
anything. No dependency has been added.

## API and privacy

`compile_edit_plan(raw_bytes, original_remedy_request, private_binding)` invokes
`remedy_plans.compile_plan` internally instead of trusting an editable plan output.
The binding is a dictionary with exactly these fields:

- `schema_version`: `guardian-config-edit-binding/0.1`
- `target_ref` and ordered `scope_refs`: exactly equal to the original request
- `layer_ref`: a revision-map key whose digest binds the supplied bytes
- `layer_kind`: `owned-profile-extension`
- `group_name`: selected policy name, equal to the semantic egress alias
- `rules`: exact selected rule-ref keys, each mapped to `index` and `expected`

No authorization or native-verification flags are accepted. Product/version labels
must satisfy the semantic request contract, with no unknown versions. A syntactically
valid version is only a declaration: there is no production compatibility allowlist,
and no version is certified by this implementation.

Returned `PrivateCandidate` does not serialize through ordinary JSON or pickle and
its representation omits private data. `preview()` exposes only fixed states and
the changed/matched-rule counts; it omits configuration, domains, group names,
revision hashes, targets and paths. All three mandatory semantic blockers remain
explicit; `apply_supported` is always false. Changed candidates retain pending
action authorization. An all-matching supplied snapshot reports
`no_change_in_supplied_snapshot`, with authorization
`not_required_for_snapshot_observation` and no action-only pending blocker.
That observation does not certify the current app, effective configuration or route.

`private_material()` deliberately exposes the original and candidate bytes, their
SHA-256 hashes, and immutable declared target/scope/layer/revision/version bindings
for an explicitly private local review. It also exposes immutable
`policy_token_edits` tuples, each containing an original-byte start/end offset
and the before/after bytes, in ascending offset order. Immutable
`matched_rule_refs` and `changed_rule_refs` identify the two sets in the semantic
request order. Apply these spans in
reverse order to reconstruct the candidate; they are not executable write plans. Never log or serialize this material into
public reports. Serialization guards prevent accidental default export, not access
by a caller already holding the configuration. This module is not an isolation or
authentication boundary against such a caller.

## Byte and semantic invariants

Only policy-token byte spans are replaced. PyYAML character marks are converted to
UTF-8 byte offsets before slicing, preserving Unicode before a rule, UTF-8 BOM,
CRLF/LF line endings, trailing comments, unknown fields and all other original
bytes. Multiple edits are sorted, checked for overlap and applied in reverse order.
The candidate is parsed again; its complete syntax-tree semantic signature must
equal the original tree with only selected rule values changed. No YAML dump or
constructor-driven object loading occurs.

Every selected rule is validated, including already-correct rules. Already-correct
policy tokens enter `matched_rule_refs` and produce no edit; other selected rules
produce the exact minimal token edits. This works with either selection order and
does not short-circuit later malformed, duplicate, stale or shadowed selections.
An all-matching result keeps the original bytes/hash and has no edit spans. A
repeat request must be rebound to the freshly supplied snapshot and expected
rule values; the earlier immutable request remains stale. Failure codes never
embed raw parser errors or supplied configuration values.

## Agent integration boundary

Ownership, selected-rule scope, group-name provenance and target identity remain
caller declarations. The parser proves neither valid Mihomo semantics nor GUI
merge behavior. A future native adapter must verify version-specific ownership,
protected paths, effective group graph and ordering, then show exact local diff,
backup/recovery plan and obtain action-specific permission. A fresh safe read and
revision conflict check are required immediately before any separately authorized
write. The shared `repair_cli.preflight` now uses `transactions.py` only when
candidate bytes differ. An unchanged candidate has no transaction plan, action
ID, retained artifact or receipt. Before returning or presenting this observation,
the CLI rechecks the full request digest, target bytes/file/parent identity,
explicit supporting sources, cancellation and the original deadline. Supplying
`--plan-file`/`--backup-directory` does not cause destination access for this branch;
existing artifacts are not replaced. Direct `repair_execution.retain` rejects it
with `NO_CHANGE_TO_RETAIN` before any destination access.

Mixed-change private review lists only real edits while the retained artifact
still binds the complete original request. An execute-time no-change recompile
is stale, not an applied receipt. Production native admission remains blocked.
Native acceptance and actual route behavior must be measured independently.

## Evidence and rollback

`python -m unittest discover -s tests -p test_config_edit_plan.py -v`

The synthetic regressions cover exact bytes/hashes, Unicode/BOM/CRLF, multiple
edits, private previews, no I/O, malformed structures, duplicate keys/rules/groups,
injection, stale bindings, cancellation, versions, missing parser, bounds and no-ops.
No real configuration, account, network, controller or native device was accessed.
This library-only increment can be rolled back by removing the module, its tests
and this document; it creates no user configuration changes to undo.

2026-10-16 increment: 23 focused synthetic tests pass, including private span
reconstruction, domain-label bounds, known earlier coverage, later/noncovering
rules, unknown rule types remaining unverified, and rejection after an earlier
in-memory edit without modifying any input. The full batch evidence and remaining
native/CI limits are recorded in `validation.md`.

2026-10-18 idempotent-replanning increment: 28 compiler tests pass. See
[evidence and original-requirement limits](evidence/rebuild-idempotent-replanning.md).
This closes only a bounded candidate/replanning subgap, not full ENV-T60 (L + R).
