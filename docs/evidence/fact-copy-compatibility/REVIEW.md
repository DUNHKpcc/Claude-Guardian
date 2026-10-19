# Fact-value snapshot compatibility review

Date: 2026-10-19. Scope: the single `_record_fact` change from storing `value` to storing `deepcopy(value)`. This is a new current-runtime compatibility review, not a new model run or a rewrite of earlier approvals. Independent integration review is recorded separately by the coordinator.

The historical runtime SHA-256 is `691aa0b634ba7ff1d26d3d13a3a9c58a6e43924047c63338b41b832529e3ffa9`; the candidate is `9f5237846756759a90e907eebe096f9263c0d938e78aecf4173fafb3912ede25`. The complete candidate file is pinned, and reversing exactly one declared line must reconstruct the complete historical hash. No other runtime difference is accepted.

## Semantic finding

The prior public API could retain the caller's mutable dictionary or nested list as recorded evidence. Later caller mutation could silently change that evidence without a new source, time, target, or question. Copying the incoming value at the shared recording point restores the documented copy-returning API boundary. It covers single and batch recording and their existing internal callers. It does not infer facts, select routes, grant consent, refresh provenance, or open action gates.

For supported normalized JSON values, the added cost is proportional to the incoming value. Arbitrary Python objects with executable copy hooks are outside this review's JSON-input contract. This is not an I/O sandbox or validation of arbitrary Python objects.

## Fresh evidence and full-clause preservation

The receipt records newly executed complete deterministic API replays for thirteen existing suites against both the historical and candidate runtime. Every complete JSON result was identical, including state, questions, assessments, provenance, retained fields, and gate values. The suite input files and their supporting sources are pinned. Compact semantic hashes avoid republishing approximately 26 MB of duplicate traces; tests regenerate both complete outputs and compare the actual objects as well as the retained digest.

The affected ordinary case-page groups are T76/T84, T75/T79, T29/T57, T49/T83, T31/T47, T82, T16, T23, T01/T02, T19/T20/T21/T24, T53/T74/T81 and T34/T43/T48/T78. Their original clauses and guide interpretation remain unchanged. T22/T25 retain all seven original responses and their original provenance limitations. Their helper was not invoked during those conversations; the newly replayed helper evidence remains separate. Unchanged guidance and identical complete outputs preserve the prior scoped reviews without claiming that stochastic dialogue was regenerated.

The unchanged subscription-boundaries adapter separately replays all 15 guarded calls and compares complete arguments, returns, outputs and guard definitions, with no attempted I/O. The upgrade-conflict packet replays all 163 supported calls with recorded clocks, including six expected errors; its live terminal suite, read-only CLI comparison and lifecycle assertions remain enabled. Historical failed trajectories are preserved as failures. No new acceptance row or additional platform layer follows from this compatibility review.

## Historical and current verification are explicit

All three historical evidence packets and the batch33 preservation packet remain byte-identical. Their old manifests, source tuples, reviewers' conclusions, model responses and run records are unchanged. A disposable, explicitly named historical-source view contains real reconstructed old runtime bytes and byte-identical prerequisite copies. Unmodified historical source verifiers inspect that view. No digest is forged, no old receipt is relabeled current, and no repository copy of a historical archive is added.

Current-runtime evidence is checked separately and mandatorily. The installed consumer pins this manifest and verifier before execution. The exact source tuple, every retained packet inventory, thirteen live semantic replays, the 15-call subscription replay, and 163-call upgrade replay are checked. Unknown current bytes, an incorrect reverse transition, missing or altered review/receipt, historical packet drift and changed replay results fail closed. The old verifiers' original mutation controls remain enabled on genuine historical bytes; new controls independently cover current-source drift.

The fixture-embedded source pins in the preserved local-incident replay still describe the original fixture. The enclosing receipt and manifest identify the actual candidate runtime used for this new execution. This is synthetic, offline compatibility evidence, not native, network, payment, service-state, repair, recovery or new model-response acceptance.
