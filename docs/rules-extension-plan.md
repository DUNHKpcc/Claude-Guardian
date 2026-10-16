# Explicit prepend candidates for rules extensions

Requirements: ENV-02/06, D-ENV §3.4 and §20.9; configuration priority and
protected-control-path preservation remain independent acceptance requirements.

`rules_extension_plan.py` handles a separate format from `config_edit_plan.py`.
The source baseline is Clash Verge Rev v2.5.8, commit
`4337bd85758d54d7b9044b2da3c9ac1176eae1f3`. A rules extension has `prepend`,
`append` and `delete` sequences. The pinned sequence implementation combines
prepend entries, existing base rules excluding exact full-string deletions,
then append entries. This is not a merge mapping's full `rules` replacement.

## Supported candidate, not application

The compiler accepts only an existing literal, single-line empty prepend list
such as `prepend: []` or `prepend: [ ]`. It inserts explicitly selected, ordered
`DOMAIN` or `DOMAIN-SUFFIX` rules with one explicitly selected group. It does not
choose domains, placement or a group, initialize an empty merge document, replace
the base ruleset, edit existing rules or execute scripts.

Delete must be empty in this first slice because deletion analysis is outside
the supported scope. This is a conservative implementation limit; the pinned
source does not apply delete entries to newly prepended rules. Append entries and
unrelated extension fields remain byte-for-byte unchanged. Existing rules must
be scalar strings. YAML aliases, anchors, explicit tags, duplicate mapping keys
and ambiguous syntax are rejected by the existing bounded parser.

Only one insertion occurs inside the original empty brackets. UTF-8/BOM,
CRLF/LF, comments and other original bytes are preserved. The candidate is parsed
again and its complete syntax-tree signature must equal the original with only
the expected prepend values added. A later invalid selection rejects the entire
candidate without changing input objects.

## Inputs and private review

`compile_rules_extension(extension_bytes, base_bytes, original_remedy_request,
binding)` recompiles the semantic request instead of trusting an editable plan
projection. Both byte snapshots must match different named revision layers in
that request. The existing keep-existing semantic graph/control prerequisites
must hold as declarations, and the declared product/GUI version must be
clash-verge-rev/2.5.8. The core version is not thereby observed or certified.

The binding has exactly:

- `schema_version`: `guardian-rules-extension-binding/0.1`
- `operation`: `insert_selected_prepend_rules`
- `target_ref`, `scope_refs`: exactly the original request's target/scope
- `layer_ref`, `base_layer_ref`: distinct revision keys for the extension/base
- `layer_kind`: `owned-profile-rules-extension`
- `placement`: `prepend`
- `group_name`: exactly the selected semantic egress alias, appearing uniquely
  among the supplied base snapshot's proxy groups
- `rules`: selected rule references mapped to exact `{kind, domain}` objects
- `rule_order`: exactly the semantic request's ordered selected references
- `protected_rule_indexes`: explicit indexes in the supplied base rule list

The base snapshot is supplied data, not proof of active or effective application
configuration. Reading it requires its own exact scope; it may contain private
subscription information and must not be exported as part of a review.

The candidate's normal preview omits domains, groups, bytes, hashes and targets.
Explicit private material provides original/candidate bytes and hashes, ordered
additions, a reconstructible insertion and known priority overlaps labeled with
their base/append layer and index. Review only the selected additions and relevant
overlaps in the authorized private host/user conversation; do not publish the
full private material or unrelated base configuration.

## Priority limitations

Prepend changes priority. It is not automatically safe because the extension was
empty. Exact existing selectors, including conservative case/root-dot variants,
and mutually overlapping additions are rejected. Known overlaps with declared
protected DOMAIN/DOMAIN-SUFFIX/MATCH rules are rejected. Unknown protected rule
types are also rejected instead of guessed. Known unprotected base and append
overlaps are exposed for review; unknown forms remain unverified.

The protected index list is caller-declared and cannot prove that all
organizational, rescue or control-path rules were included. Even an empty list
retains `PROTECTED_RULE_COVERAGE_UNVERIFIED`. Base graph, effective priority,
group graph and later merge/script effects remain unconditional blockers.
No JSON field turns this candidate into an approval or supported native action.

The compiler itself does no I/O, launches nothing and never changes production
execution admission. The pinned linkage validator now has an explicit rules
mode resolving current profile → option.rules → a type=rules entry; it remains
supplied-metadata validation, not native ownership proof. `apply_supported` is
always false. Real Mac metadata preservation, writer exclusion, effective
configuration validation, reload and routing acceptance remain separate gaps.

## Unified internal CLI route

The shared `repair_cli.py` uses an explicit `--candidate-kind rules-prepend`;
it does not silently retry the merge editor with another format. In addition to
the exact request/target, this route requires `--base-path`, `--app-info`,
`--profile-index` and `--extension-uid`. All are explicit host-authorized read
inputs, not paths discovered and opened from request or registry JSON/YAML.
For example, with illustrative paths:

```sh
python3 -B skills/claude-guardian/scripts/repair_cli.py plan \
  --candidate-kind rules-prepend \
  --request /private/review/request.json --target-ref selected-device \
  --target-path /private/config/profiles/extension.yaml \
  --base-path /private/config/profiles/source.yaml \
  --app-info /approved/app/Contents/Info.plist \
  --profile-index /private/config/profiles.yaml --extension-uid selected-rules \
  --plan-file /private/review/plan.json --backup-directory /private/recovery \
  --private-review
```

The base and target must be in the index directory's `profiles` subdirectory;
the base basename must match the selected current profile's registry entry.
The private review contains exact ordered additions, known priority overlaps,
source paths/hashes, selected UID and the retained artifact digest. Unrelated
configuration is omitted. Required source arguments are checked before reads;
request and selected scope still need the trusted host's actual permission.

Retained artifact schema `guardian-retained-repair/0.2` binds candidate kind,
selected UID and each source's exact path, parent identity and file snapshot,
alongside the target plan and backup destination. Execute takes the same exact
source arguments and reviewed digest; it recompiles and rejects changes,
including same-byte inode replacement. Older retained artifacts must be replanned
and reviewed; no saved grant or automatic approval migration exists.

The existing exact reader's ownership, symlink/hardlink and xattr restrictions
remain intact. A real Mac input that fails those checks still blocks; consistent
metadata does not relax them. Production execute always denies at the native
admission gate. This integration makes blocked planning and review usable by an
Agent; it does not establish successful native repair.

## Tests and rollback

`python -B -m unittest discover -s tests -p test_rules_extension_plan.py -v`

Tests use synthetic supplied bytes, including the all-empty SeqMap shape found
in the independently authorized Mac observation. They are not tests against that
private configuration and do not read or write it. Rollback of this candidate
capability is removing the module/test/packaging registration; there is no user
configuration mutation to reverse.

Selected global/default UIDs and extensions referenced by another local/remote profile are rejected; a unique file item alone does not establish a single-profile change scope.
