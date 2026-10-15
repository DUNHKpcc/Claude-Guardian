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
- ASCII domain tokens and ASCII policy names matching the implementation's bounded
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
the changed-rule count; it omits configuration, domains, group names, revision
hashes, targets and paths. All three mandatory semantic blockers remain explicit,
alongside pending action authorization; `apply_supported` is always false.

`private_material()` deliberately exposes the original and candidate bytes, their
SHA-256 hashes, and immutable declared target/scope/layer/revision/version bindings
for an explicitly private local review. Never log or serialize this material into
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

No-op rules are rejected rather than silently generating a misleading change.
Failure codes never embed raw parser errors or supplied configuration values.

## Future integration boundary

Ownership, selected-rule scope, group-name provenance and target identity remain
caller declarations. The parser proves neither valid Mihomo semantics nor GUI
merge behavior. A future native adapter must verify version-specific ownership,
protected paths, effective group graph and ordering, then show exact local diff,
backup/recovery plan and obtain action-specific permission. A fresh safe read and
revision conflict check are required immediately before any separately authorized
write. Existing `transactions.py` may eventually provide a restricted transport;
this candidate object is not a transaction plan and is not wired to that engine.
Native acceptance and actual route behavior must be measured independently.

## Evidence and rollback

`python -m unittest discover -s tests -p test_config_edit_plan.py -v`

The synthetic regressions cover exact bytes/hashes, Unicode/BOM/CRLF, multiple
edits, private previews, no I/O, malformed structures, duplicate keys/rules/groups,
injection, stale bindings, cancellation, versions, missing parser, bounds and no-ops.
No real configuration, account, network, controller or native device was accessed.
This library-only increment can be rolled back by removing the module, its tests
and this document; it creates no user configuration changes to undo.
