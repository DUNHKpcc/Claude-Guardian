# Bounded rule-source import: API and offline evidence

Date: 2026-10-18. Scope: complete, already-authorized byte strings and synthetic
configuration fixtures. This is an ENV-06 / original ENV-T40 subgap. It does not
establish full ENV-T40 acceptance or native behavior. No engine, service, source
fetch, live configuration, account or network request is needed by this helper.

## Original conditions and clause-by-clause limits

D-ENV v0.3 §12.1 defines original **ENV-T40** as **纯域名/规则提供方/主规则/JSON
格式转换**, requiring **不可表达的 ASN/匹配/动作语义明确报错，不静默丢失**.
The implementation tracker and rebuild ledger assign **L + R**; the case remains
pending. The full scenario and requirement, rather than a keyword match, imply:

- **纯域名**: the new explicit exact-host grammar consumes a whole byte batch and
  requires a separately selected action. It does not infer exact versus suffix
  semantics from an unidentified source list. The Agent must verify that choice.
- **规则提供方**: provider `payload`, provider downloads, rule-set references and
  expansion are unsupported. They reject; this increment supplies no provider
  conversion acceptance.
- **主规则**: only the already-supported plain three-field DOMAIN/DOMAIN-SUFFIX
  slice, in a sole `rules` mapping, is imported. A complete arbitrary main config
  is not relabeled a fragment or silently stripped down to its rules.
- **JSON**: other-engine JSON transformation is unsupported and rejects. There is
  no new versioned Mihomo/sing-box adapter or claim of lossless interchange.
- **不可表达的 ASN/匹配**: ASN, CIDR, keyword, modifiers, wildcard, IDNA and unknown
  match forms fail atomically. Exact-host and suffix kinds, original ASCII case
  and ordering survive the supported conversion without widening their meaning.
- **动作语义**: each fragment action must equal the explicitly selected group;
  mixed actions, DIRECT, REJECT or another group's action are never discarded or
  rewritten. Actionless lines also require explicit action intent. Built-in
  terminal actions are outside this candidate-prepend binding's action subset.
- **明确报错，不静默丢失**: fixed error codes terminate the entire batch, including a
  bad final record. There is no success with a filtered, sorted, deduplicated or
  partially imported list. Different exact/suffix selectors remain distinct;
  downstream priority checks can still reject their overlap.

This is bounded offline **L supporting evidence**. It does not finish L for all
formats or R for actual configuration/engine behavior. Full **ENV-T40 L + R
remains incomplete**; the accepted original-case count does not increase.

Nearby requirements are preserved rather than claimed complete:

- §5.7: retain rule identity, match/value, purpose, client/feature selection,
  evidence/source/date/version, shared-service declaration, action intent and
  candidate state. A service dependency does not choose a user's outbound action.
  The batch shares immutable source declarations; every record has its own
  reference, position, kind/value and action. These are caller declarations, not
  a complete production dependency registry or validated client catalog.
- §5.8: supported match types/actions and order are explicit; unsupported types
  fail. Existing compiler checks for selected overlap, protected rules, group
  ambiguity, duplicates and version/snapshot changes retain authority. Global
  MATCH, company DNS, subscription data and nodes are not rewritten by import.
- D07 / §5.6: source conversion is only the front of format/reference → conflict
  → ownership/persistent patch → kernel check → app readback → route evidence →
  subscription refresh. This helper cannot skip the later stages or turn
  `candidate_only_blocked` into applied/verified.
- §20.8–20.9: the Agent gets usable private inputs for an existing narrow repair,
  not a new framework or an executor gate on ordinary offline explanation.

The semantic basis is the frozen design and existing config/rules compilers.
This increment deliberately adds no provider or other-engine syntax requiring
unverified external grammar. The format suffix `0.1` versions this local importer
contract; declared source/installed engine versions are not validated by it.

## Public API and exact grammar

Packaged module: `claude-guardian/scripts/rule_source_import.py`.
Add the installed Skill's `scripts` directory to the host's module search path,
then import `import_rule_bindings`. The active Agent procedure, including a
complete synthetic call, is in `references/agent-remediation.md`, section
“ENV-06：把已读取规则来源转换为受限候选输入”. There is no new CLI or file scanner.

```python
import_rule_bindings(source_bytes, format_id, ordered_rule_refs,
                     source_binding, action_intent,
                     *, max_seconds=5, cancelled=lambda: False)
```

Required inputs:

| Input | Contract |
| --- | --- |
| `source_bytes` | Exact built-in immutable bytes, nonempty, at most 1 MiB; UTF-8 |
| `format_id` | Exactly `exact-domain-lines/0.1` or `mihomo-domain-rules-fragment/0.1` |
| `ordered_rule_refs` | Built-in list/tuple of 1–256 unique non-identifying aliases; one per record in supplied order |
| `source_binding` | Exact key set listed below; copied before subsequent callbacks |
| `action_intent` | Exactly `{"kind": "user_selected_egress", "group_name": <alias>}`; DIRECT/REJECT are unsupported targets |
| `max_seconds` | Built-in finite int/float, greater than 0 and at most 60; default 5 |
| `cancelled` | Cooperative callback returning an actual boolean; exception/non-boolean/true stops with fixed CANCELLED |

`source_binding` requires exactly: `schema_version` equal to
`guardian-rule-source-binding/0.1`; opaque aliases `source_ref`, `version_scope`,
`purpose`, `feature_gate`; `expected_sha256` as 64 lowercase hexadecimal characters;
`evidence_kind` in `official_documentation`, `user_supplied`, `reference_material`;
`verified_at` as a valid YYYY-MM-DD date; 1–16 unique aliases in `client_scope`;
actual boolean `shared_service`; and `activation_state` fixed to `candidate`.
Both shared-service values are retained as declarations, without promotion.
Unknown keys, subclass containers and malformed types reject.

Aliases are ASCII `[A-Za-z][A-Za-z0-9_-]{0,63}`. Recognized credential-shaped
aliases are rejected using the existing source-evidence detector; ordinary words
such as `token` and short documentation aliases remain valid. This is not an
arbitrary-secret detector. Private source bytes may contain sensitive content;
the host still owns authorized reads and private handling.

Both grammars accept only the existing ASCII DNS-label subset (at most 253 total
characters, labels at most 63), preserving spelling. Unicode/IDNA labels, root
dots, wildcard forms and literal IP addresses are unsupported. Numeric-only
hosts, including `127.1` and padded `192.000.2.1`, conservatively reject as
ambiguous; ordinary numeric labels such as `123.example.invalid` remain valid.
This is a subset policy, not a universal detector of historical address forms.

| Grammar | Accepted meaning and layout | Explicit exclusions |
| --- | --- | --- |
| `exact-domain-lines/0.1` | One exact host per line; LF/CRLF; optional initial BOM and one final line terminator; requires selected action | Empty/comment/whitespace lines, padding, other separators, suffix guesses or embedded actions |
| `mihomo-domain-rules-fragment/0.1` | Sole `rules` mapping with a block sequence of plain single-line literal `DOMAIN,host,group` or `DOMAIN-SUFFIX,host,group`; source comments retained in full private bytes | Other top-level keys, provider payload, JSON, flow/quoted/multiline scalars, YAML tags/anchors/aliases, extra fields and unsupported match types |

`DOMAIN` means exact host only. `DOMAIN-SUFFIX` retains the existing suffix kind,
including that host and label-boundary descendants; it is not converted to a
wildcard or exact-only rule. Case folding is solely a same-kind duplicate check.
Different kinds can preserve source meaning at import but still be ineligible
for prepend because the downstream compiler rejects overlapping selections.

The expected digest is compared with SHA-256 computed from all supplied bytes.
It is an integrity binding, not source authenticity, freshness or independence.
No supplied timestamp or version scope proves the present installation matches.

## Result, provenance and downstream use

The result and its records are frozen, slotted objects with fixed redacted repr.
Default JSON and pickle serialization reject. This is accidental-disclosure
protection for a trusted host, not a sandbox against arbitrary Python code.

- `preview()` returns only fixed schema/status strings, bounded total/exact/suffix
  counts, `apply_supported=false`, native `not_run`, and authenticity/freshness/
  independence/effective priority `not_established`. Offline conversion itself
  does not require an action approval. No domains, references, group, digest,
  dates or caller metadata appear in this public summary.
- `binding_components()` returns fresh private copies of `rules`, `rule_order`
  and `group_name`. These fit the existing rules-prepend compiler binding. The
  host must compare them with the already selected request; it must not silently
  rewrite that request's intent or omit a source record to force acceptance.
- `private_material()` returns original immutable `source_bytes`, computed
  `source_sha256`, explicit `source_format`, immutable `declared_source`, and
  immutable records. Each record keeps `rule_ref`, zero-based `source_index`,
  one-based `source_line`, `[start,end)` UTF-8 byte offsets, `original_record`,
  `kind`, case-preserved `domain`, `source_action` and selected `action`.
  Record spans exclude separators/YAML list markers/comments; the full source
  retains all such original bytes, including BOM and CRLF.

All supplied records are validated before a result escapes. Returned mutable
copies cannot mutate the private result. The complete source batch and copied
metadata remain bound even if the caller later changes input containers.
There is no persistence or automatic source-file reread: when the source changes,
obtain fresh authorized bytes, reimport and rerun the existing preflight. The
current CLI does not acquire a new execution-time source-file gate from this
helper, and the documentation does not claim one.

Bounds are fixed at 1 MiB, 256 records and 16 client aliases. The existing safe
YAML parser also bounds events/depth and rejects aliases/tags. Cancellation and
one original monotonic deadline are checked initially, after parsing, during
record work and immediately before return. They are cooperative: a parser call
is not preempted mid-call, and a bounded input is not a hard real-time guarantee.
No timeout or cancellation returns a partial candidate. Oversized/unreadable/
unknown inputs need a precise gap report, never skipping, extra scans or a
silent dependency installation. Plain exact lines need no PyYAML; the fragment
returns `PARSER_UNAVAILABLE` if the optional existing parser is absent.

Errors are fixed-code `SourceImportError` values. Important categories include
`UNSUPPORTED_SOURCE_FORMAT`, `INVALID_OR_OVERSIZED_SOURCE`,
`INVALID_SOURCE_BINDING`, `INVALID_RULE_REFERENCES`, `DUPLICATE_RULE_REFERENCE`,
`EXPLICIT_ACTION_REQUIRED`, `SOURCE_DIGEST_MISMATCH`, `INVALID_SOURCE_ENCODING`,
`UNSUPPORTED_DOMAIN`, `UNSUPPORTED_RULE_FRAGMENT`, `UNSUPPORTED_RULE_RECORD`,
`SOURCE_ACTION_CONFLICT`, `DUPLICATE_RULE_SELECTOR`,
`RULE_REFERENCE_COUNT_MISMATCH`, `PARSER_UNAVAILABLE`, `YAML_BUDGET_EXCEEDED`,
`CANCELLED`, `INVALID_DEADLINE` and `DEADLINE_EXCEEDED`. Supplied values are not
included in error strings. Exact failure codes for the grammar and integration
boundaries are exercised in the new test suite.

## Reproducible before/after workflow

The frozen seventh tree has no source-import entry point. It already accepts
manually prepared bindings; this is not a claim that an old Agent lost source
semantics or that its compilers were permissive. The same reproducer below was
run on seventh and eighth file bytes, independently of their local Git HEAD.
It demonstrates the missing source-to-binding step and the added actual
import-to-existing-compiler workflow. It uses only synthetic fixtures.

Seventh output:

```json
{"case": "source_to_candidate", "status": "importer_api_unavailable"}
```

Eighth output:

```json
{"apply_supported": false, "case": "source_to_candidate", "native_acceptance": "not_run", "ordered_additions": [["rule-z", "DOMAIN-SUFFIX,Other.example,approved-group"], ["rule-a", "DOMAIN,Example.test,approved-group"]], "record_count": 2, "source_bytes_preserved": true, "source_hash_computed": true, "status": "candidate_only_blocked"}
{"case": "mixed_action_batch", "error": "SOURCE_ACTION_CONFLICT"}
{"case": "mixed_action_batch", "error": "SOURCE_ACTION_CONFLICT"}
{"case": "mixed_action_batch", "error": "SOURCE_ACTION_CONFLICT"}
```

The three rejection rows replace the second source action with REJECT, DIRECT
and another group respectively. All fail atomically. No real rule was applied.
Save the following synthetic script and run
`PYTHONDONTWRITEBYTECODE=1 python -B /tmp/reproduce.py /path/to/tree`:

```python
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

repo = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(repo / 'tests'), str(repo / 'skills/claude-guardian/scripts')]
if importlib.util.find_spec('rule_source_import') is None:
    print(json.dumps({'case': 'source_to_candidate', 'status': 'importer_api_unavailable'}, sort_keys=True))
    raise SystemExit(0)
import rule_source_import as source
import rules_extension_plan as rules
from test_rules_extension_plan import RAW, BASE, inputs
raw = (b'rules:\n  - DOMAIN-SUFFIX,Other.example,approved-group\n'
       b'  - DOMAIN,Example.test,approved-group\n')
metadata = {'schema_version': source.BINDING_SCHEMA,
    'source_ref': 'source-a', 'expected_sha256': hashlib.sha256(raw).hexdigest(),
    'evidence_kind': 'user_supplied', 'verified_at': '2026-10-18',
    'version_scope': 'declared-v1', 'purpose': 'repair', 'client_scope': ['client-a'],
    'feature_gate': 'selected-feature', 'shared_service': False, 'activation_state': 'candidate'}
intent = {'kind': 'user_selected_egress', 'group_name': 'approved-group'}
imported = source.import_rule_bindings(raw, source.FORMATS[1], ['rule-z', 'rule-a'], metadata, intent)
request, binding = inputs()
components = imported.binding_components()
binding.update(components)
request['intent']['rule_refs'] = components['rule_order'][:]
request['intent']['egress_group_ref'] = components['group_name']
candidate = rules.compile_rules_extension(RAW, BASE, request, binding)
private = imported.private_material()
public = candidate.preview()
print(json.dumps({'case': 'source_to_candidate', 'status': public['status'],
    'apply_supported': public['apply_supported'], 'native_acceptance': public['native_acceptance'],
    'record_count': imported.preview()['record_count'],
    'source_bytes_preserved': private['source_bytes'] == raw,
    'source_hash_computed': private['source_sha256'] == hashlib.sha256(raw).hexdigest(),
    'ordered_additions': candidate.private_material()['ordered_additions']}, sort_keys=True))
for replacement in (b'REJECT', b'DIRECT', b'other-group'):
    mixed = raw.replace(b'DOMAIN,Example.test,approved-group', b'DOMAIN,Example.test,' + replacement)
    changed_metadata = dict(metadata, expected_sha256=hashlib.sha256(mixed).hexdigest())
    try:
        source.import_rule_bindings(mixed, source.FORMATS[1], ['rule-z', 'rule-a'], changed_metadata, intent)
    except source.SourceImportError as exc:
        print(json.dumps({'case': 'mixed_action_batch', 'error': str(exc)}, sort_keys=True))
```

## Regression matrix and delivery checks

`tests/test_rule_source_import.py` covers both grammars; exact/suffix/case/order;
BOM/CRLF and UTF-8 comment byte offsets; selected action and metadata declarations;
malformed/unknown formats; unsupported records in either order; duplicate
selectors/references; credential-shaped aliases and ordinary alias positives;
byte/record/client bounds; missing parser; fixed private errors; immutable
records/copy isolation; no I/O; cancellation/deadline including the final return
boundary; and detached extracted-package use without site packages.

Actual imported bindings also run through the unchanged `compile_rules_extension`:
ordered additions and native blockers are retained; exact/suffix overlap,
protected MATCH/suffix/unknown provider rule, absent/duplicate group, an existing
selector, stale snapshots, version mismatch and cancellation remain blocked.
This is synthetic compiler evidence, not engine execution or actual routing.

Delivery runs the importer, all source/package suites and ledger integrity;
full Python aggregate; script compilation; both Node synthetic suites; and two
independent reproducible Skill packages. Recorded on 2026-10-18 in the cloud Linux workspace:

| Check | Actual result |
| --- | --- |
| New importer suite | 45 passed, including extracted-package smoke |
| Source/package suites (`test_source*.py`) | 23 passed |
| Accepted-case ledger integrity | 3 passed |
| Complete Python aggregate | 1,285 run: 1,277 passed, 8 explicitly skipped |
| `compileall` and new-file Python 3.10 syntax parse | Passed |
| WebRTC lifecycle Node suite | 8 synthetic scenarios passed |
| Dashboard interaction Node suite | Passed, synthetic only |
| Two independent Skill packages | Byte-identical; SHA-256 `8ccd1e7ec763445ffdbace66f9b73f5618fe8408d2b1d707e4e879de8ac18692` |

Logs and owned-file hashes are retained with the batch receipt. Skipped cases
are not passed or native acceptance; these checks do not use a real browser,
proxy engine or user device.

The package allowlist adds exactly the importer module. Because the packager is
pinned by accepted original T09 evidence, its existing pin requires independent
re-review and page/ledger hash refresh. This does not reclassify ENV-T40 or make
copied sources independent. T09 source-helper behavior and original source bytes
remain unchanged.

## Tradeoffs and rollback

This small host library removes repetitive hand-building of rule dictionaries
while retaining source evidence. It reuses the existing safe parser and private
binding contract, adds no service/CLI/dependency/engine and keeps all native
execution restrictions. Its deliberate cost is a conservative syntax subset:
ambiguous/unrepresentable inputs need explicit Agent explanation or a later
versioned adapter with primary-source review. It does not attempt a broad merger,
semantic source discovery, provider resolution or automatic policy selection.

Rollback removes the helper/test, its one package entry and this guidance/evidence
increment; existing manually prepared bindings and compilers keep their behavior.
No user configuration migration, restoration or real-device rollback is needed.
