# Whole-device network-guidance review: T03, T05, T09, T18

Date: 2026-10-19 UTC. This separate source and whole-clause review preserves only
**T03, T05, T09 and T18** as currently accepted. The ledger remains **4 accepted /
214 pending**, with all **51 historical evidence objects**, **218 original IDs,
scenarios, complete requirements and literal layers** unchanged. This is a
prompt/guidance change, not implementation or acceptance of whole-device traffic
interception, persistent enforcement, native TUN behavior or actual recovery.
It grants no device, network, account or publication authority.

## Preserved evidence and exact scope

The preceding [comment-wrapper review](agent-rules-comments-limited-revalidation.md)
keeps SHA-256 `93621e537809d78cc7482919bb979a1f8e4c47498933b7943dab524a37ca4900`
and all nineteen original source pins. The prior Agent-task and entry-order
reviews, their transitions, original dialogue packets and source inventories
also remain byte-identical. The four preceding current evidence objects are
copied intact to `prior_comment_revalidation_evidence`; their canonical SHA-256
is `9aea03755067a37c19007fbbbfb5c163292fea124916244b71dc0618358d6e46`.
No earlier evidence object or historical source pin is refreshed in place.

The [exact transition](whole-machine-limited-transition.json), SHA-256
`04e401b9721d729359de50b6bc6973c61f5fa3e4e990292c2f389a42ded61d7f`, retains literal before/after spans and complete file
hashes for only these reviewed guidance and regression-test changes relative to
the public baseline `b3f7051c6744f150bf792712674484a96d34b352`:

- `skills/claude-guardian/SKILL.md`
- `skills/claude-guardian/references/agent-remediation.md`
- `skills/claude-guardian/references/network-and-remedies.md`
- `skills/claude-guardian/references/routes-and-platforms.md`
- `tests/test_guides.py`

Reversing these exact spans reconstructs every complete preceding file.
The old nineteen-pin review is checked against that reconstructed basis, then
its existing earlier transitions reconstruct the preceding nineteen- and
fifteen-pin reviews. Reconstructing old bytes is an integrity check only; current
guidance checks run on the actual current files. Current source/helper/package
checks do not execute a rewritten historical implementation.

The two network references previously used `origin: repository` in the sparse
historical fixture. Their exact original bytes now use `origin: snapshot`:

- `network-and-remedies.md`: 16,003 bytes, SHA-256
  `a13f51b7b996bd2a2c3f920b3a944d8b3f8a059e6a28cb921be5cd84b3f6d48b`
- `routes-and-platforms.md`: 25,984 bytes, SHA-256
  `dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984`

All 64 original source members, hashes and sizes remain fixed. The sparse fixture
now stores 14 files totaling 604,006 bytes. Its new manifest SHA-256 is
`17ce86957d19f476247ca35203c9d8153316d2d95c453a91c19bd75494ef291b`.
A regression reverses only those two origins, totals and explanatory README hash
to the complete prior manifest
`696c39044e3711a6594bfc3861d20396b9ff462c097a6d9afb5cd8070a38e692`;
it also reconstructs the whole prior README and retains the earlier rules-plan
preservation reversal. Missing snapshots never fall back to current guidance.
Neither `skills/claude-guardian/sources/manifest.json` nor
`docs/source-manifest.json`, the packager or its 67-member allowlist changes.

## Reviewed guidance and explicit non-capabilities

For a network preparation or repair task, the dated default is the same target
computer's ordinary applications, subprocesses and background traffic using the
specified proxy path. TCP, UDP and DNS, including application-specific resolvers,
are in the intended scope. A user may explicitly choose a narrower application
scope or a separately specified route; its identity, children, destinations,
protocols, address families, priority and normal/failure behavior need separate
review. An exception invalidates any unqualified all-software/same-path claim.
Ignoring system proxy settings is a coverage gap, not an automatic exception.
VM, WSL, containers and remote computers retain their distinct target boundaries.

Before configuration, the guidance requires disclosure of the actual supported
interception mechanism, such as TUN, its effects on applications, LAN/VPN, DNS
and control connections, precise settings, exceptions, backup and independent
recovery, followed by specific approval. TUN, routing mode and fault blocking are
separate. Choosing the default does not authorize settings, process stops,
restarts, probes or fault injection. PC0, cancellation, denial, target binding,
existing execution gates and unrelated-task boundaries remain in force.

Ordinary target traffic is IPv4-only without IPv6 fallback or an unauthorized
alternate exit. The proxy's outer transport, bootstrap and necessary local/control
traffic require explicit bounded decisions, not inheritance of blanket legacy
exceptions. No broad proxy-process exemption or global IPv6 shutdown is added.
The four layers of declared rules, application loading, process adoption and
end-to-end observation remain separate. Same-chain observations do not guarantee
one public IP. Lifecycle stability, protocol coverage and restoration require
real scoped observations; absent evidence remains unknown, unsupported or not
established. No native whole-device capability or persistent monitor is added.
The unchanged selected-target runtime/reporting outputs cannot certify the new
whole-device intent, and their fields are not relabeled to imply it.

## Whole original clauses and current applicability

### T03 — 403 错误 (L+C)

Full clause: **不直接认定封号；先确认响应来源、认证与权限**.

Both entire retained replies were reread. The first asks separately about response
origin, authentication and permission without requesting secrets. The second keeps
all three unknown despite the reported gateway and presence of a key; it never
turns 403 into an account-suspension finding. The requests specifically forbid
new queries. The changed default applies to network preparation/repair, provides
no response-origin or authentication observation, and preserves PC0 and specific
contact/action gates. It cannot justify a diagnostic retry, configuration change
or replacing the original three questions with a whole-device questionnaire.
The original complete clause remains supported within the retained exercise.

### T05 — VPS 实测正常一周 (L+C)

Full clause: **可记录观察期，不能输出“极低封号率”**.

Both full retained replies were reread. The final observation is expressly user
reported: seven named UTC dates, about twenty minutes daily, local Remote-SSH to
VPS Code, with version, path and other periods unknown. It rejects continuous
uptime, ban-rate estimates, future-account guarantees and inference to other
VPSes. The new guidance explicitly separates same path from fixed public IP and
limited observations from lifecycle/fault protection; it supplies no additional
VPS measurements. Independent target binding and the current basic non-invasive
VPS boundary remain. Neither whole-device intent nor a TUN setting can expand
that week into a guarantee or justify new requests. Both clauses remain supported.

### T09 — 两份完全相同教程 (L+C)

Full clause: **只算一个来源，不当交叉证据**.

The complete active evidence-policy/source-library procedure, source helper and
eleven-file source inventory are unchanged. The actual two-real-S07-copy scenario
was rerun on the current helper and still produces exactly one byte-identity group
with both aliases and `independent_sources: not_established`. Full result,
rejection/no-I/O boundaries and the extracted-package helper are checked. Changed
network guidance and its preserved historical copy are not new independent
sources. A different file, name or network route does not establish independent
provenance. Both original clauses remain supported without new model generation.

### T18 — 申诉事实未确认 (L+C)

Full clause: **使用待补充字段，不能捏造使用地点、本人行为或付款事实**.

Both entire retained drafts were reread. Location, payment and unreported actions
remain placeholders. Only the explicitly supplied 2026-10-16 web-writing event is
added; it is not substituted for the restriction date. The drafts remain unsent,
with submission and current official entry verification separate. Network-scope
intent and future approval requirements provide none of those missing facts and
do not prove any actual configuration, use, save or recovery. The new guidance
preserves unrelated-task and contact boundaries rather than requiring a network
repair before an appeal draft. All original clause components remain supported.

## Executed checks and limits

These scoped commands ran successfully on the current tree, with zero failures,
errors or skips:

- `python -B -m unittest discover -s tests -p 'test_source*.py' -v`:
  **23 tests**, including the complete T09 result and extracted-package helper
- `python -B -m unittest discover -s tests -p 'test_acceptance_diagnostic_evidence.py' -v`:
  **6 tests**, the unchanged retained T03/T05 packet under historical sources
- `python -B -m unittest discover -s tests -p 'test_acceptance_t18_evidence.py' -v`:
  **8 tests**, the unchanged retained T18 packet under historical sources
- `python -B -m unittest discover -s tests -p 'test_acceptance_historical_source.py' -v`:
  **11 tests**, complete historical-source preservation and fail-closed controls
- `python -B -m unittest discover -s tests -p 'test_guides.py' -v`:
  **20 tests**, current prose contracts; no deployed/platform behavior claim
- `python -B -m unittest discover -s tests -p 'test_traffic_policy.py' -v`:
  **27 tests**, the unchanged legacy selected-target policy, not whole-device support
- `python -B -m unittest discover -s tests -p 'test_acceptance_rebuild_ledger.py' -v`:
  **21 tests**, current pins, complete reverse chains, retained evidence and disposition


Before this new review wiring, the unchanged sixteen-test ledger suite was run
on the changed SKILL/routes tree and reported **10 failures**, including subcase
failures. The prior current pins and earlier reverse transitions correctly
rejected the new bytes. That failure is retained here; a later pass does not make
old pins current or erase the invalidation. The review and preservation changes
resolve it without altering any old source or acceptance requirement.

The first whole-repository aggregate on this guidance/evidence tree ran **2,402
tests: 2,393 passed, one failed and eight skipped**. Its sole failure was the
current intake-basics guidance assertion still requiring the obsolete sentence
“A browser-only task does not require Code/Desktop or firewall setup.” The full
first-run log SHA-256 is
`6d7a66960b03d6805a9b99393f54d943f1dfc35b2a728d29971fa077d1d8159e`.
That failure is not hidden or reclassified as a passing whole-repository run.

The additional current regression in `tests/test_acceptance_intake_basics.py`
keeps its exact T01/T02 original specification and tracker assertions. It now
requires no default firewall installation, evaluates protection against the
whole-device coverage goal with supported capability, disclosed effects and
specific approval, and rejects the former unconditional browser-only exemption.
The original test method is retained. Its historical copy was already a pinned
snapshot and remains unchanged; this extra current regression does not restore
T01/T02 acceptance or expand the four-case current review dependency set. The
updated current test-file SHA-256 is
`376f8794095c13c620f3b6fb67e340c2649944334622276ade042fd828ca8c4c`.

`python -B -m unittest discover -s tests -p 'test_acceptance_intake_basics.py' -v`
then ran **13 tests**, all passing with no errors or skips. As a separate negative
control, the updated complete-clause method was run with only its supplied
`ROUTE_GUIDE` replaced by the exact preceding route guide: **one test failed as
expected**, with no errors or skips. No fixture expectations were generated from
current output, no original requirement was edited, and the six frozen guidance/
changelog/test files were not changed by this additional repair. Any subsequent
aggregate result is a separate execution, not a replacement for this first failure.

The renewed ledger suite requires twenty-two exact current source pins, the
unchanged preceding nineteen-pin review and its full reconstruction, both earlier
reviews/transitions, every original clause/layer, historical page/object hashes
and complete source/response inventories. Negative controls reject extra bytes,
changed reverse spans, altered transition proof and symlink proof/source inputs.
The four prior comment evidence objects are hash-checked independently. These
controls support the semantic assessment above; pins and test counts alone do
not establish behavioral acceptance.

No fresh dialogue was generated. Original diagnostic/appeal replies remain
historical, and the review does not claim model behavior on unobserved inputs.
The other 47 historical acceptances remain pending, alongside the previously
pending 167 cases. No new scripts, native configuration changes, service probes,
TUN execution, real failure tests, CI outcome or publication is claimed here.
Further drift in a reviewed source invalidates this limited current applicability.

## Exact current reviewed source pins

| Path | SHA-256 |
|---|---|
| `skills/claude-guardian/SKILL.md` | `4baa187b4c0562cfe23d9dcefe0f51588b4276590a9bbb071640a57982ee4387` |
| `skills/claude-guardian/references/intake.md` | `dba62c7cf1ccf88fb8d435d807c026cc71ba786a138cfc8843ce7bff6f38a04a` |
| `skills/claude-guardian/references/incidents-and-integrations.md` | `37d1f06a3e46a61fd841455ad40ca4081468c0e6b2b4248d23b345c05d93e9d2` |
| `skills/claude-guardian/references/evidence-policy.md` | `8afb262a1d85050a897c6c9a89f54afbc96a653874b7308472dbeec4c3ea1838` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/references/routes-and-platforms.md` | `170668e980a17c756f19f79d2648b8595c306f0040943e556e1107fdcf09f90c` |
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
| `skills/claude-guardian/references/agent-remediation.md` | `b5fb6f00600a3466ba4ab546c86f7665fcea7c6490c01b14b522997b05c7b194` |
| `skills/claude-guardian/references/network-and-remedies.md` | `9606fa9f861ead46f7fd97a730ef6329eae3cad97656fd087ef877e2dfa276fe` |
| `tests/test_guides.py` | `541a799008e576d7f8bc4a5d7d6cb200f3e169e3cad9492cfc224d958bb00553` |
