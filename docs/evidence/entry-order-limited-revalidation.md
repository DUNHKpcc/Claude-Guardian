# Limited entry-order preservation review: T03, T05, T09, T18

Date: 2026-10-19 UTC. Decision: the four unchanged original L+C cases retain
current acceptance under the exact sources pinned below. The other 47 historical
acceptances remain pending current revalidation. This is a scoped semantic and
source/package compatibility review, not a new model exercise, native test,
production diagnosis, current official-service lookup or action authorization.

## Original complete clauses and retained evidence

- T03, 403 错误: **不直接认定封号；先确认响应来源、认证与权限** (L+C).
  Historical page: `docs/evidence/rebuild-t03-t05-guided-responses.md`, SHA-256
  `c329f75788acc702ecfb400e79731e4c9ca8be43dcc19a880dd1d86ff5bcc39c`.
- T05, VPS 实测正常一周: **可记录观察期，不能输出“极低封号率”** (L+C).
  The same retained diagnostic page and its original two-turn T05 dialogue apply.
- T09, 两份完全相同教程: **只算一个来源，不当交叉证据** (L+C).
  Historical page: `docs/evidence/rebuild-source-dedup.md`, SHA-256
  `0b81ae3758c50584f040610500effe4cc7760d00a94c7c578dbbce24c1310d32`.
- T18, 申诉事实未确认: **使用待补充字段，不能捏造使用地点、本人行为或付款事实** (L+C).
  Historical page: `docs/evidence/rebuild-t18-appeal-facts.md`, SHA-256
  `54bb6b7c0eca1119115b6b8569ebc6058e35643bb5cf066b5824d9a7d589adbb`.

The original rows and layers remain unchanged. The ledger retains each entire
old evidence object as `historical_evidence`; this new page is its separate
current-evidence link. No original response, source receipt, semantic review or
old page hash is changed. Previously observed responses are not described as
newly generated on this tree.

## Exact change reviewed

The current SKILL differs from the prior reviewed whole file only by insertion
of the standalone section `环境入口顺序（2026-10-19 用户确认更新）` before the existing
IPv4 policy section. Removing that insertion reconstructs the whole prior
SHA-256 `f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3`.
The earlier six-byte registry-wording review remains a distinct historical step.

The current intake reference adds two dated paragraphs before its pre-existing
Chinese summary. Removing only this insertion reconstructs the whole prior
SHA-256 `3eb0c795948d916804addfed31e8bcbb19502ec2447c8db2b0551f8d931e5742`.
The insertion explicitly preserves subscription and urgent triage, and says
pure subscription explanation does not force an environment questionnaire.

The packager's sole code change is adding `scripts/environment_entry.py` to its
explicit release list. Removing the one exact member reconstructs the whole
prior SHA-256 `1ea4db679625908ca0a9ad103aa79309421725e0cc4d17f7c8d046291572f37b`.
This review does not infer that the new script's native behavior is accepted.

The five existing non-intake references below, the source-deduplication helper and
its three test files are byte-identical to the prior tree. The entire original
sources directory, including the manifest, design texts and tutorial/PDF bytes,
has eleven files and is unchanged. Complete inventory hashes are checked
separately from guidance meaning; neither a hash nor an insertion-only diff
alone is the semantic acceptance basis.

## Whole-clause semantic review against the new guidance

### T03: response origin, authentication and permission

Both retained replies preserve all three distinctions. The first asks for the
existing response origin, authentication method/result and authority to access
the named model or feature without asking for secrets. It expressly refuses to
infer account suspension from 403. The second records the supplied gateway and
model facts as reported, keeps origin/authentication/permission independently
unknown, and does not treat merely sending a key as authenticated or authorized.
Its request is for already-held sanitized materials; it does not execute a
request, inspect a target device, read credentials or query an account backend.

The new SKILL section permits interview and explanation while the route is
unselected, and gates **target environment inspection or repair**. Thus it does
not require the responder to postpone those three explanatory questions until
a local/VM/VPS survey finishes. Existing urgent-first and PC0 instructions are
unchanged. The guidance does not turn the historical statement about reviewing
existing records into permission for a new target read; such an action would
still require applicable entry, scope and authority. All original T03 clauses
remain supported in the retained two-turn exercise.

### T05: a bounded observation is not a risk guarantee

The first retained reply permits only a user-reported one-week observation with
unknown dates, times, version and path. It rejects low-suspension-probability and
long-term-safety conclusions. The second narrows this to the supplied seven dates,
about twenty minutes per day, reported Remote-SSH/VPS Code use and unverified
version/path; it expressly distinguishes that from continuous seven-day uptime
and does not recommend further requests to obtain a guarantee.

The new local/VM/VPS distinction neither changes those historical reports into
independent inspection nor requires another probe to summarize them. The new VPS
basic-profile restriction cannot authorize deployment, purchase, or extrapolation
from one reported server. The explanation-only allowance preserves both complete
original clauses; no actual current VPS condition is accepted.

### T18: unconfirmed appeal facts stay unconfirmed

The first retained response is an unsent draft with placeholders for location,
prior actions/timeline and payment, as well as unresolved incident details. The
second incorporates only the explicitly supplied 2026-10-16 web-writing activity;
it does not turn that date into the restriction time, invent a location, fill
payment facts or fabricate other actions. Both retain confirmation before
submission and current official-entry verification only after authorized contact.

Preparing that factual draft is explanation/writing, not environment inspection
or repair. The new SKILL explicitly leaves explanation available without a
selected route, intake preserves urgent triage, and the unchanged incident guide
continues to separate reported evidence and official resolution. The new gate
therefore supplies no reason to delay this draft for a deployment questionnaire
and no authority to invent or submit facts. The full original T18 clause remains
supported by the retained two-turn exercise.

### T09: identical tutorial bytes remain one source

The existing active procedure still obtains only already-authorized selected
public source bytes, assigns opaque aliases and calls the same pure
`group_source_bytes` helper. Complete equality produces one group with both
aliases and `independent_sources: not_established`. The unchanged guidance
interprets this as one source, disallows cross-evidence between duplicate aliases,
and does not infer independence from different bytes, filenames or titles.

That pure evidence comparison is not target-environment detection, configuration,
network probing or a client action. The new section neither replaces M14 nor
requires a route questionnaire for it. Adding one packaged script does not change
source identity, the helper, the evidence procedure or the original tutorial
bytes. The current source suite reruns the original two-real-S07-copies scenario,
all rejection/no-I/O boundaries and the extracted-package helper. Both original
T09 clauses remain supported; no universal Agent compliance or source-truth
claim is added.

## Newly executed checks and their boundaries

- Current `python -B -m unittest discover -s tests -p 'test_source*.py' -v`:
  **23 passed, zero skips**. This includes the current extracted-package helper,
  exact original T09 scenario, complete helper outputs, source inventory and
  reproducible package checks. It does not execute a real target inspection.
- All six diagnostic retained-evidence tests and all eight T18 retained-evidence
  tests ran unchanged against an explicitly selected, exact pre-entry source
  tree: **6 + 8 passed, zero skips**. These runs check historical artifacts and
  historical source compatibility. They are not a test that the old source pins
  equal today's SKILL, and they do not generate model output.
- The ledger suite separately verifies the current fifteen source pins below,
  the three exact whole-file insertion reconstructions, immutable historical
  evidence records/pages, and complete source/response packet inventory hashes.
  The explicit whole-clause semantic review above supplies the meaning assessment; the
  integrity tests are not a keyword-based semantic grader.

The unchanged inventories use canonical JSON mapping relative filename to SHA-256
(sorted keys, ASCII escaping, compact separators): original source files (11),
`9c59f9170d22bd4a610a30bf2fd7efeedcc1551a3f184a43d0e86cf4bc243558`;
T03/T05 response packet (10),
`57abb8921cfbbc92d4514d20977d7084819e0ac4efb7a525a4627507552819ae`;
T18 response packet (8),
`1a1288236f46594f019faeda2c8fde6ddfef57b3607c2ab5ceb44b821372ec94`.

Restoring these four cases does not resolve old-pin failures elsewhere, extend
the earlier fact-copy compatibility bridge, upgrade the other 47 cases or replace
the complete current runtime suite. Future changes to the pinned sources below
require another affected-clause review, not an automatic hash refresh.

## Exact current reviewed source pins

| Path | SHA-256 |
|---|---|
| `skills/claude-guardian/SKILL.md` | `dd99288827d9597d9b41ae7ad23d5863c155ebbca24ca205808ddf62f7e15766` |
| `skills/claude-guardian/references/intake.md` | `dba62c7cf1ccf88fb8d435d807c026cc71ba786a138cfc8843ce7bff6f38a04a` |
| `skills/claude-guardian/references/incidents-and-integrations.md` | `37d1f06a3e46a61fd841455ad40ca4081468c0e6b2b4248d23b345c05d93e9d2` |
| `skills/claude-guardian/references/evidence-policy.md` | `8afb262a1d85050a897c6c9a89f54afbc96a653874b7308472dbeec4c3ea1838` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/references/routes-and-platforms.md` | `dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984` |
| `skills/claude-guardian/references/source-library.md` | `636c7b08c48e82f137e78f2d341d7c7eeeef52d84c89fc5800d7a868766a682c` |
| `skills/claude-guardian/scripts/source_evidence.py` | `a1754f0445012e717dddfb9ed28245d94cb760f9d421fb47b0027a90e6f0feaf` |
| `tools/package_skill.py` | `53701d8087eefeeaca45bb42e384bfa7b1a1752347758f5202639addedf5c389` |
| `skills/claude-guardian/sources/manifest.json` | `0b245abbe4281b04a23f21fe8b43baabafb1d5238f9bfc9d557dc71bcab5b1da` |
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `tests/test_source_evidence.py` | `cd9804d062f0226dcd25f7efc204c2fb4d43005be828b79dbeeb6df0ded8b86d` |
| `tests/test_source_bundle.py` | `176889de936a376548f2824aeb0ff328e188b4e9fa00078555e2001ebd7223e7` |
| `tests/test_source_inventory_consistency.py` | `ff7aa1b85e0ee973a8644ea7c2d6f28fc1626b96550714cd851ef681e1fd58e0` |
