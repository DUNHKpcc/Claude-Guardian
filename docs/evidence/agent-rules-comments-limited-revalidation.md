# Comment-preserving Agent-task review: T03, T05, T09, T18

Date: 2026-10-19 UTC. This separate, exact-source review preserves only the same
four current complete-case decisions. The disposition remains **4 accepted /
214 pending**, with all **51 historical evidence objects** retained and all
**218 original IDs, scenarios, full requirements and literal layers unchanged**.
It reviews a supplied-snapshot wrapper correction and affected guidance. It is
not native application acceptance, fresh model generation, a service observation,
an action authorization or a new acceptance for a pending case.

## Immutable earlier evidence and exact change

The preceding [Agent-task review](agent-rules-limited-revalidation.md), SHA-256
`e366916c628b95a3fddf620d323b2e7dc27d3ccb970c4a2b59013a54510e8900`, and its
[exact transition](agent-rules-limited-transition.json), SHA-256
`06fa421e121dba098770eb202ddd6acb0d4dae61e228957157f38ff3a1faedaf`, are unchanged.
Its nineteen original pins remain mandatory as a historical source basis. The
[earlier entry-order review](entry-order-limited-revalidation.md), its fifteen
pins, every retained response, source inventory and historical page/object remain
unchanged as well. The four preceding Agent-task evidence objects are copied
intact to `prior_agent_rules_revalidation_evidence`; their canonical SHA-256 is
`48544fb2ed2816b49297d6f7943dde8b309a2b90c902d4a5369fe39bba770cdc`. The existing
`prior_revalidation_evidence` and `historical_evidence` objects are not rewritten.

The new [three-file transition](agent-rules-comments-limited-transition.json),
SHA-256 `0e4b9ab806fddf72b2f79183b4aba4e24b6f9190dda742ac8f464362e8826214`, records literal before/after spans and
complete before/after file hashes for only:

- `skills/claude-guardian/scripts/agent_rules_task.py`
- `tests/test_agent_rules_task.py`
- `skills/claude-guardian/references/agent-rules-task.md`

Reversing those spans reconstructs each complete prior file, including its old
hash. All sixteen other sources in the prior nineteen-pin review are unchanged.
The packager, its 67-member allowlist, both source manifests, historical sparse
snapshots, shared parser and rules compiler require no change in this batch.
Reconstruction is an integrity check of historical bytes; current behavioral
checks execute the actual current implementation separately.

## Reviewed wrapper behavior and limits

The wrapper still uses the existing bounded YAML parser and shared rules
compiler. It stops rejecting every document containing a hash marker, while
retaining exactly the three `prepend` / `append` / `delete` keys and all existing
rule, semantic, source, ownership and entry gates. The compiler inserts the one
selected DOMAIN rule into its existing supported inline sequence by byte offset;
it does not strip comments, reserialize the document or manufacture missing facts.
Legal header, tail and inline comments therefore survive in the private original
and candidate, including reviewed Unicode, BOM and CRLF forms. This does not add
support for arbitrary YAML layouts or nonempty extension content.

After the existing source/ownership and content checks, readback gives priority
to exact candidate and exact original bytes. Only when original, candidate and
readback all lack `#` may the existing limited candidate-semantic comparison
apply. Any hash marker is a conservative reason to require exact bytes; it is not
a second comment parser. Removing, adding, changing or moving comments, or
reformatting a marked document, returns `unexpected_delta` and
`conflict_requires_new_review`. Comment-free supported formatting comparisons
remain available. Private `format_scope` now states which boundary applies.

An exact original readback means only that supplied original bytes match. It
proves neither an actual restore nor a failed save. Cancellation, changed entry,
source mismatch, expiration, absent native evidence and exact-host approval keep
their existing distinct meanings. Original private bytes remain available for
recovery review; no file save, backup store, restoration transaction or execution
receipt is implemented by this correction. `SEMANTIC_PLAN_BLOCKED` remains the
shared compiler's existing semantic/template gate, independent of comment support.

## Whole original clauses and current applicability

### T03 — 403 错误 (L+C)

Full clause: **不直接认定封号；先确认响应来源、认证与权限**.

Both complete retained responses were reread. They separately preserve response
origin, accepted authentication and operation permission, and do not infer an
account suspension from a status code or possession of a key. The comment change
only affects already supplied configuration text. Neither a comment nor a
successful comparison becomes an account fact, a response-origin finding or
permission to query a service. The reference still requires fresh target/action
permission and forbids bypassing denial, withdrawal or PC0. All original clause
components remain supported within the retained exercise.

### T05 — VPS 实测正常一周 (L+C)

Full clause: **可记录观察期，不能输出“极低封号率”**.

Both retained responses were reread in full. The second bounds the user-reported
period to seven named UTC dates and about twenty minutes per day, with version,
path and other periods still unknown; it rejects continuous uptime, ban-rate and
future-account extrapolations. Preserving comments supplies no VPS observation or
risk estimate. The stricter marked-document comparison cannot be promoted to
save, load, effective routing or recovery evidence. The reference retains those
separate layers and no-immunity boundary. Both original requirements remain
supported.

### T09 — 两份完全相同教程 (L+C)

Full clause: **只算一个来源，不当交叉证据**.

The active source procedure, evidence-policy/source-library text, pure helper and
complete eleven-file source inventory are unchanged. The exact two-real-S07-copy
scenario was rerun and still returns one byte-identity group with both aliases
and `independent_sources: not_established`. Full result and rejection/no-I/O
assertions, plus the extracted-package helper, remain enforced. The changed
wrapper/reference are implementation material, not additional independent
sources; preserving comments does not establish provenance or truth. Both
clauses remain supported without inventing a new model transcript.

### T18 — 申诉事实未确认 (L+C)

Full clause: **使用待补充字段，不能捏造使用地点、本人行为或付款事实**.

Both entire retained drafts were reread. Unknown location, payment and actions
remain placeholders; the second adds only the reported web-writing event and
does not turn that usage date into the restriction date. Submission is separate
and still unsent. Preserved configuration comments and supplied-content matches
supply none of those missing facts, prove no user action and restore no authority.
The reference continues to prohibit default Claude contact and does not impose a
configuration repair before a placeholder draft. The whole original clause
remains supported.

## Actual executed checks and limits

The following scoped commands ran successfully on the current implementation,
with zero failures, errors or skips:

- `python -B -m unittest discover -s tests -p 'test_source*.py' -v`:
  **23 tests**, including full T09 output and extracted-package behavior
- `python -B -m unittest discover -s tests -p 'test_acceptance_diagnostic_evidence.py' -v`:
  **6 tests**, retained T03/T05 artifacts under explicitly historical sources
- `python -B -m unittest discover -s tests -p 'test_acceptance_t18_evidence.py' -v`:
  **8 tests**, retained T18 artifacts under explicitly historical sources
- `python -B -m unittest discover -s tests -p 'test_acceptance_historical_source.py' -v`:
  **10 tests**, unchanged historical snapshots and fail-closed controls
- `python -B -m unittest discover -s tests -p 'test_agent_rules_task.py' -v`:
  **38 tests**, actual current supplied-snapshot code with comment preservation,
  exact readbacks/no-change, comment mutations and retained guard/privacy cases

- `python -B -m unittest discover -s tests -p 'test_acceptance_rebuild_ledger.py' -v`:
  **16 tests**, current pins, both prior reviews, complete reverse transitions,
  preserved evidence objects and unchanged 4/214/51/218 disposition

The two new preservation/no-change regression methods were also run against the
exact old helper: two tests produced seven subcase errors with
`UNSUPPORTED_AGENT_EXTENSION_FORMAT`. The same regression paths pass on the new
helper. This is a synthetic failing-first result, not an observed device edit.

Before the new review wiring, the unchanged ledger integrity suite ran 11 tests
on the in-progress implementation and reported two failures: the new helper and
test bytes no longer matched the preceding review's strict current pins. The
reference had not yet changed during that run. This genuine invalidation is
retained here; a later pass does not erase it or make old pins current.

The renewed ledger controls require nineteen exact current source pins, the
unchanged preceding nineteen-pin review reconstructed through exactly three
complete files, the unchanged earlier fifteen-pin review and its original
transitions, all historical page/object hashes, response/source inventories and
original clauses/layers. Negative controls reject extra source bytes, changed
reverse spans, a changed transition proof and symlink proof/source inputs. The
four old Agent-task evidence objects are hash-checked independently from current
evidence. These integrity assertions support, and do not replace, the semantic
review above.

Original diagnostic/appeal responses remain historical. No new dialogue was
generated or needed for this non-conflicting, bounded configuration-wrapper
change. The other 47 historical acceptances remain pending, as do the previously
pending 167 cases. Native UI save, side effects, concurrency, load, effective
routing and actual recovery need separate evidence and authorization. Any future
test-only save/restore contract remains unimplemented and outside this review.
Whole-repository integration, cross-platform CI and any publication are separate
gates; the scoped checks here do not claim those outcomes. Further drift in any
reviewed source invalidates this bounded current applicability.

## Exact current reviewed source pins

| Path | SHA-256 |
|---|---|
| `skills/claude-guardian/SKILL.md` | `4d66015c1a0af5a4d325c99e839703ffd1b860a24804df6590d59014f29b1ff6` |
| `skills/claude-guardian/references/intake.md` | `dba62c7cf1ccf88fb8d435d807c026cc71ba786a138cfc8843ce7bff6f38a04a` |
| `skills/claude-guardian/references/incidents-and-integrations.md` | `37d1f06a3e46a61fd841455ad40ca4081468c0e6b2b4248d23b345c05d93e9d2` |
| `skills/claude-guardian/references/evidence-policy.md` | `8afb262a1d85050a897c6c9a89f54afbc96a653874b7308472dbeec4c3ea1838` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/references/routes-and-platforms.md` | `dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984` |
| `skills/claude-guardian/references/source-library.md` | `636c7b08c48e82f137e78f2d341d7c7eeeef52d84c89fc5800d7a868766a682c` |
| `skills/claude-guardian/scripts/source_evidence.py` | `a1754f0445012e717dddfb9ed28245d94cb760f9d421fb47b0027a90e6f0feaf` |
| `tools/package_skill.py` | `91b78bc2d33024941614f7a4b9377df075888b9d02564620ac1cbe4c78754cee` |
| `skills/claude-guardian/sources/manifest.json` | `0b245abbe4281b04a23f21fe8b43baabafb1d5238f9bfc9d557dc71bcab5b1da` |
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `tests/test_source_evidence.py` | `cd9804d062f0226dcd25f7efc204c2fb4d43005be828b79dbeeb6df0ded8b86d` |
| `tests/test_source_bundle.py` | `176889de936a376548f2824aeb0ff328e188b4e9fa00078555e2001ebd7223e7` |
| `tests/test_source_inventory_consistency.py` | `ff7aa1b85e0ee973a8644ea7c2d6f28fc1626b96550714cd851ef681e1fd58e0` |
| `docs/rules-extension-plan.md` | `14d8e97ac66a8afa544d93bbf5a69e89dfb731025953fb92b7961f3f0d6c0548` |
| `skills/claude-guardian/scripts/agent_rules_task.py` | `b09ad827d1c39f2ca2d7fbf8355f45a51a9ede4ef3f1d9068a3045412b49dc91` |
| `skills/claude-guardian/references/agent-rules-task.md` | `74cb4af01e0e8b36477f468310919932f67b49a1c5729d0a534e753fd77e525f` |
| `tests/test_agent_rules_task.py` | `8c0b364d3111807a8dcfbb708edcca5455f5601ab6af594fde9c70586fef651f` |
