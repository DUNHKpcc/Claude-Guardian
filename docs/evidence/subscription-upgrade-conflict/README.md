# Public T77 / T80 evidence projection

This is a deliberately minimized public projection of retained synthetic acceptance evidence. It replaces the private raw archive in this candidate; it is not byte-identical to that archive and cannot reconstruct or independently authenticate its omitted execution/coordination records. The original archive remains unchanged and private. Its SHA256 and each relevant original record hash are in `projection-map.json` and `projection.json`; no private archive handle is published.

## Contents

- 48 exact fictional user inputs and actually observed assistant outputs: 42 revision3 turns and six fresh revision4 turns, with all 208 answer-unit reviews and four historical failing integrated-turn verdicts
- 186 recorded API calls, including all seven actual failed invocations, normalized to semantic method/arguments/input/output/error plus transactional state commitment
- A 163-call current-source replay selection: ten historical successful trajectories and the two fresh repaired trajectories; historical broken paths remain separately visible
- Original source clauses, original T77/T80 L+C requirements and exact current-source pins
- Full relevant synthetic terminal, exclusion, lifecycle and all-fields-covered conflict proof values; the nine original terminal regression bodies retain all original assertions
- Explicit hash-only provenance mapping, neutral temporary-error and source-drift facts, and honest limits in `CURRENT-REVIEW.md`

`values.json` deduplicates repeated JSON objects. A one-key `$value` reference expands to the object with that canonical SHA256. This changes storage only; tests verify all expanded hashes and reject cycles, unused or missing values. `projection.json` is readable as ordinary JSON. No raw coordination envelope, executor path, task/agent identity, private artifact handle, original source-read orchestration or execution command is included.

The project shim at `tests/test_acceptance_subscription_upgrade_conflict.py` pins the complete public packet manifest before loading test code. Run:

```sh
python -B -m unittest discover -s tests -p 'test_acceptance_subscription_upgrade_conflict.py' -v
```

Checks execute the actual installed helper API and read-only CLI, compare complete returned objects/exact errors, test the original nine terminal cases, validate lifecycle/schema/JSON-roundtrip behavior, and reject evidence/source tampering. Forced cp1252 subprocess execution and Python 3.10 AST parsing are compatibility checks, not native Python 3.10 or Windows/macOS execution. No model is generated during replay. This evidence is project-only and never enters the unchanged 63-member Skill package.
