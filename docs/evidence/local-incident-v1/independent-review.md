# Independent T22/T25 acceptance review

Reviewed: 2026-10-19. Verdict: **PASS for original T22 and T25 at their unchanged L+C evidence scope**, with the limits below. This review does not accept adjacent cases, native platforms, network behavior, current official procedures, repair, or recovery. No substantive failure was found in the seven retained responses; none was rewritten or replaced for this review.

## Original requirements

- **T22:** “L4 只处理本机 Code” → “留在 `R-LOCAL`，缩减基础解释，不自动推荐 VM/VPS 迁移”
- **T25:** “本机出现错误或账号受限” → “先在原方案进行专项诊断，不自动购买 VPS、重建 VM 或迁移账号”

These are D-SPEC-v0.1.10 §11 rows T22/T25 (lines 1081/1084), not similarly numbered ENV cases. `docs/implementation-tracker.md` §8 assigns both L+C. Supporting requirements reviewed: D-SPEC §§3.1–3.3, 5.0–5.7 and D.3; D-ENV §6.5, ENV-T57 and §§18.5–18.6. The current IPv4-only product choice is separately stated in the shipped Skill and network reference; it does not rewrite these original acceptance rows.

## Seven complete responses, in conversation order

### expert-local-code: T22 PASS

**Turn 1: PASS.** The reply retains mac-local and independent local-terminal Code, without treating SDK expertise as a remote-workspace choice. Its six compact difference-checklist entries concern installation/launch identity, possible authentication overrides, shell/proxy adoption, route/DNS separation, the current scoped IPv4 requirement, and failure/preservation boundaries. These are relevant checks, not a generic beginner course or a demand for new products. API-key/gateway mentions are conditional override checks, not allegations that either exists. Existing OAuth, Pro, OS and architecture remain reported facts; all inspection outcomes remain unverified. The next missing facts are installation/version, proxy/core version and configuration layers. It neither runs Code for version information nor recommends VM/VPS migration.

**Turn 2: PASS.** The requested two topics receive exactly two sentences each. Candidate proxy variables are expressly version-dependent; inheritance and actual network-library adoption remain separate. The process-environment explanation is appropriately qualified and does not claim an inspected process. A depth-only question causes no route, subscription, installation or permission change. No unrelated tutorial or deployment proposal is introduced.

Sources: `references/routes-and-platforms.md` lines 7–24, 67, 78–110; `references/incidents-and-integrations.md` lines 46–89, 93–104; `references/network-and-remedies.md` lines 10–22, 41–52; `references/contact-and-safety.md` phase contract. All reference paths in this review are relative to `skills/claude-guardian/`.

### local-proxy-error: T25 PASS

**Turn 1: PASS.** The diagnostic priority is the component that generated the 403, with the same-day proxy-group change treated as a lead rather than a proven cause. It distinguishes CONNECT/local-proxy failures from upstream authentication/permission errors and does not treat Pro as proof of a valid session. Active configuration, rule/group selection and proxy adoption are plausible bounded next checks. It correctly separates startup environment from later proxy-internal changes and warns that stopping interaction does not prove background processes stopped. IPv4-only is an independent preparation requirement, explicitly not an explanation of the 403. The immediate request is only for already-held minimal sanitized text; no reproduction, live account check or repair is requested.

**Turn 2: PASS.** The interpretation follows the user's explicitly identified local log: this one CONNECT was locally policy-denied before an upstream attempt. It does not upgrade that report to verified host evidence, infer upstream account health, identify an unknown rule/node, or infer whole-device silence. The useful next step is to identify the effective configuration and denying local policy, including rule/group/priority/merge relationships. The short questions about proxy software and the remembered change are relevant to that step. Re-login, cleanup and node rotation are not used as diagnostic shortcuts.

**Turn 3: PASS.** The refusal to provide more logs/configuration is respected without re-asking. It preserves the observed local denial and unknown upstream status, gives a bounded future inspection plan on the original target, and reserves a minimal change for an identified discrepancy. The statement about account status is scoped to explaining this already-recorded local refusal; it does not declare the upstream account healthy or rule out a separate account problem. Whole-config rollback is avoided; backup, independent recovery and separate later operation/network approval remain required. “Remain paused” is an appropriate present next step under the user's explicit no-action instruction, not a claim that the incident is resolved.

Sources: D-ENV §6.5; `references/incidents-and-integrations.md` lines 13–22, 118–159, 183–188; `references/network-and-remedies.md` lines 10–22, 41–52; `references/routes-and-platforms.md` lines 101–110. All three responses remain on the original local route, with no purchase, VM reconstruction or account migration proposal.

### current-restriction: T25 PASS

**Turn 1: PASS.** The explicitly current official-notice report activates account-restriction handling rather than historical-ban speculation or a new onboarding/payment flow. It preserves uncommitted work, existing screenshot/notice, histories and custom configuration. It correctly refuses to attribute cause to the proxy, OS, OAuth or a device blacklist, and does not present local cleanup as a remedy for remote suspension. Stopping repeated login is consistent with the already-paused state; stopping other running automation remains subject to identifying its impact. Current support/appeal/export/refund instructions are deferred to authorized official verification, with no invented address, entitlement, response deadline, success probability or innocence claim. Asking whether a case/instruction already exists is the relevant remaining process fact.

**Turn 2: PASS.** With no case and only an existing screenshot, it provides a concrete present task: review a minimal in-conversation incident summary. The observation time is explicitly distinguished from the unknown actual suspension onset, and Code's onset, cause, wider impact and official steps stay unknown. It records that the screenshot has not been inspected. No invented case number, inspection, saved evidence package or submission is claimed. The summary preserves the same device, local Code route, reported Pro/OAuth context and user's no-access/no-send boundary.

Sources: `references/incidents-and-integrations.md` lines 13–38, 124–188; `references/contact-and-safety.md` phase contract and permissions; D-SPEC §5.5 and D.3. Neither response introduces VPS purchases, VM reconstruction, account replacement or migration.

## Separate normalized logic evidence

Reviewed all assertions in `tests/test_acceptance_local_incident_cases.py` and its synthetic fixture. Independent command: `PYTHONDONTWRITEBYTECODE=1 python tests/test_acceptance_local_incident_cases.py -v`. Result: **9 passed, 0 skipped**.

The substantive evidence is exact state/question/assessment comparison: reported local-route and depth retention; depth-only state orthogonality; incident priority without rebinding; preservation of original facts and unknown/declined outcomes; deferred ordinary gaps; blocked action gates; no inferred incident resolution; persistence/export boundaries; and repeat-stable projections. I/O-attempt sentinels cover runtime calls but are not an OS sandbox. Module/fixture loading happens outside that boundary.

The helper consumes normalized inputs and generates neither these seven answers nor the natural-language interpretation. It was not invoked in the observed conversations. The fixture's Mac/Windows labels and identity-review case establish normalized logic only; they do not establish Windows dialogue/native coverage, T04 acceptance or current identity-verification procedures. Helper counts alone do not establish either full original row: the whole-response and source review above supplies the complementary semantic evidence.

## Projection integrity and privacy

The public dialogue projection contains exactly the frozen seven user turns and seven captured response payloads, in the correct three-conversation order. Every response was compared as an exact string against its captured original and its SHA-256 recomputed. All five projection source hashes match their frozen source files. Its content and key set were reviewed for private metadata: it contains synthetic facts and ordinary project guidance, with no private task handles, absolute workspace paths, coordination records, Library identifiers, credentials or real personal/account evidence.

Projection SHA-256: `be04d06826c162ecb7e2fc68c71342bb849374bc20eb8555f60685a206f2157e`.

## Provenance and acceptance limits

- Source-reading reports are responder-reported from retained records, not an independently exported complete tool transcript. Successful source identity checks do not prove every section was read.
- The local-proxy-error source read reported an explicit **329-token omission in cleanup material**, and the omitted material was not reread. The report does not establish exact omitted bytes. This is retained as a read-completeness limitation, not silently repaired by this review. It is not material to original T22/T25 acceptance: the relevant route, incident and evidence guidance is available; the outputs do not propose cleanup, and their preservation/deferred-mutation advice is supported elsewhere. This does not accept any cleanup-operation case.
- The source-access boundary was instruction-enforced, not physical/process isolation. No independent sandbox or whole-process no-I/O claim is made.
- Device/account facts and logs are fictional user reports. No actual Mac, current account/service state, version-specific proxy support, IPv4 enforcement, real client behavior, official support route, repair or recovery was verified.
- Seven observed outputs demonstrate the bounded frozen scenarios, not every possible phrasing or future stochastic response. No N/X/R evidence has been added as a condition of these unchanged L+C rows.

## Verified SHA-256 pins

### Original requirements and active sources

- `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md`: `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562`
- `skills/claude-guardian/sources/design/D-ENV-v0.3.md`: `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4`
- `docs/implementation-tracker.md`: `8056f8d999a73a66dcdb7960dd724cd9e0c7404d769b00650e6936f21703fd50`
- `skills/claude-guardian/SKILL.md`: `f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3`
- `skills/claude-guardian/references/contact-and-safety.md`: `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c`
- `skills/claude-guardian/references/intake.md`: `3eb0c795948d916804addfed31e8bcbb19502ec2447c8db2b0551f8d931e5742`
- `skills/claude-guardian/references/routes-and-platforms.md`: `dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984`
- `skills/claude-guardian/references/incidents-and-integrations.md`: `37d1f06a3e46a61fd841455ad40ca4081468c0e6b2b4248d23b345c05d93e9d2`
- `skills/claude-guardian/references/network-and-remedies.md`: `a13f51b7b996bd2a2c3f920b3a944d8b3f8a059e6a28cb921be5cd84b3f6d48b`
- `skills/claude-guardian/scripts/interview_flow.py`: `691aa0b634ba7ff1d26d3d13a3a9c58a6e43924047c63338b41b832529e3ffa9`

### Helper evidence

- `tests/test_acceptance_local_incident_cases.py`: `22c13c0a917bcf9c9aadae3e3aee4e8a66509bf3837f0e44a5d0d0c2bc82b2e1`
- `tests/fixtures/acceptance-local-incident-cases.json`: `f021362b207a6ec29eea7e62a8cf6a7ebbc70eb1797fc2eef5dceeb6d2aed4bc`

### Exact response text

- expert-local-code, turn 1: `4d4be99f4f69dfb45224fbe7840c1a312007ebeeb6fb65ee709d1316dab0b302`
- expert-local-code, turn 2: `5d76604a56e0d980b3fa9470692284fc2c25556d96a610e0ceb4563fb75f8469`
- local-proxy-error, turn 1: `aabb641a21c7442258a829db2d0768216436804ee372c1f7610effb67f4eaa03`
- local-proxy-error, turn 2: `8ebb68cb2e142b45101c8b4dd1dbda4672800a7f22c182564a7c24e7002b073a`
- local-proxy-error, turn 3: `3831f56b0755ce2268c3f0f9ec919a3554e8b880a482bee6c4db15d25e5b9959`
- current-restriction, turn 1: `66c4424310b9672e358f68aabc60a896162d9ba7589980ce895475cd633fff7d`
- current-restriction, turn 2: `aac06e8767886a3b4c1fe445b12af85579982d2783d2615bce3030daed06081b`
