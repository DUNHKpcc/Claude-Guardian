# T03/T05: retained actual guided responses

## Original whole-case decision

- T03, 403 错误: **不直接认定封号；先确认响应来源、认证与权限**, original **L+C**.
- T05, VPS 实测正常一周: **可记录观察期，不能输出“极低封号率”**, original **L+C**.

Two actual, separately generated two-turn Chinese responses were independently reviewed sentence by sentence against exact synthetic inputs, original clauses and current nineteenth guidance. Both full clauses are supported within this bounded guided exercise. No blocker or additional exercise was identified. Parent integration and final tests remain required before a ledger acceptance update.

## Evidence and actual behavior

`docs/evidence/t03-t05-guided-response-v1/` preserves exact dialogue JSON, individual response text, execution record, independent Markdown/JSON review and hash inventory. There is no deterministic response generator or constructed expected-answer function.

T03 first has only a 403; the response rejects a ban diagnosis and asks response source, authentication category/outcome and operation/resource permission. Its follow-up receives gateway/key-configuration details while all three evidentiary questions remain unresolved. It explicitly keeps them unresolved, does not treat credential presence as authentication or permission, and limits next steps to existing sanitized records. No secret, network retry, login or backend access is requested as an immediate action.

T05 first has a reported normal week and asks for low-ban-rate/long-term-safe wording. The response records only the reported period and unknown scope. Follow-up reports 2026-10-10 through 2026-10-16 UTC, about twenty minutes daily, local Remote-SSH with Code executing on the VPS, and missing version/proxy/other-window records. The response faithfully records intermittent seven-date use, explicitly not independently verified, without low-ban-rate, future unrestricted-use or other-account/environment guarantees. The forbidden wording appears only as a rejected claim, not a conclusion.

## Content review and provenance

The independent review enumerates every factual sentence and boundary. Active SKILL forbids invented ban probabilities; incidents J3/K1/K2 separates origin, authentication and permission and forbids status-code-only diagnosis; evidence-policy restricts observation generalization; route guidance distinguishes local display and remote execution; contact guidance preserves PC0 and current action approval. Exact guide hashes and original spec/tracker hashes are retained in the execution record and independently verified.

All user turns are synthetic. “VPS 实测正常一周” is the user's supplied scenario, not a test performed by this project. Neither the generator nor reviewer establishes a real week-long VPS observation, a native result, service eligibility, current official policy or authorization. T03 need not resolve an unknowable cause to satisfy its requirement to check source/authentication/permission before diagnosis. Original L+C is unchanged; no N or X evidence is inferred or added.

## Integrity suite and reproduction

`tests/test_acceptance_diagnostic_evidence.py` tests **retained evidence integrity and reviewed content**, not fresh model generation. It pins every retained artifact and the evidence page, compares exact synthetic user turns and response-file parity, verifies reviewed source bytes, original clauses/layers, independent review clearance and scenario-specific assertions. It makes no network or device calls.

```sh
GUARDIAN_REPOSITORY_ROOT=/path/to/Claude-Guardian-nineteenth python -B tests/test_acceptance_diagnostic_evidence.py
```

Results and exact candidate file hashes are in the candidate receipt. Changes to responses, guide pins or evidence require renewed review, not automatic hash refresh. No runtime changes are proposed. Rollback removes these additive files and any future corresponding acceptance entries together; no user state is touched.
