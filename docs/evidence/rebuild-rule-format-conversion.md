# Fixed-profile predicate conversion: API and evidence

Date: 2026-10-18. Implementation: `rule_format_conversion.py`, a pure supplied-byte
host library. It returns complete private bytes or a fixed error, never writes a
file, fetches a provider, installs/runs an engine or touches host configuration.
This is a bounded ENV-06 / original ENV-T40 increment, not full-case acceptance.

## Original requirement and layer review

Original D-ENV v0.3 §12.1 **ENV-T40**: **纯域名/规则提供方/主规则/JSON 格式转换** →
**不可表达的 ASN/匹配/动作语义明确报错，不静默丢失**. The tracker assigns **L + R**:
L is pure logic/dialogue/fixtures; R is controlled write-and-restore. Combined
layers are cumulative. R is not shorthand for a regression suite or engine run.

Clause-by-clause coverage in this increment:

- **纯域名**: explicit exact-domain lines convert in both directions where every
  predicate is exact. No suffix meaning is inferred from a plain source; a suffix
  cannot be serialized as an exact line.
- **规则提供方**: fixed Mihomo v1.19.32 YAML domain/classical provider subsets now
  convert. Domain bare, `+.` apex-inclusive suffix, descendants-only `.` and
  single-label wildcard `*.` are not conflated; only the first two are supported.
  Provider declarations, remote retrieval, nested references, MRS/text and other
  behavior/encoding combinations are excluded.
- **主规则**: main policy tables are deliberately rejected by this predicate-only
  API. It neither removes a third action token nor infers the policy at a provider
  reference. The earlier action-preserving main-fragment importer is unchanged.
- **JSON**: fixed sing-box v1.12.0 source rule-set schema v1 domain-family inputs
  and outputs are supported. Route/action rules, compiled SRS, unknown schemas
  including v5, and mixed extra conditions are rejected.
- **不可表达的 ASN/匹配**: ASN/CIDR/keyword/regex, modifiers, logical/invert and
  unsupported wildcard forms cause whole-batch failure. Exact and apex-inclusive
  suffix meaning survives only inside the explicitly canonical-host model below.
- **动作语义**: every successful profile is actionless. DIRECT, REJECT, another
  outbound tag, continuing actions, route/reject/drop distinctions and outbound
  maps are not synthesized, stripped or approximated. Action-bearing input fails.
- **明确报错，不静默丢失**: invalid first or last records, duplicate keys/selectors,
  unsupported conditions and loss-prone targets return no output object. There is
  no silent filter, sort, deduplication, partial export or policy default.

This page provides bounded **L supporting evidence**. The separate
[controlled conversion transaction evidence](rebuild-rule-conversion-transaction.md)
exercises unchanged transaction primitives on dedicated synthetic files. It is a
separate R supporting composition, not a production converter writer, device
restore certification or completion of all ENV-T40 conditions. **Original
ENV-T40 L + R remains pending; the accepted original-case count does not change.**

D-ENV §5.7 still requires client/feature/source/version provenance and separates
a dependency from a selected egress. The converter retains those declarations
but does not build a complete dependency catalog. §5.8 still requires priority,
protected organization/rescue rules, version/field checks, idempotence and
preservation of global MATCH, company DNS, tokens and nodes. This library changes
none of them: it cannot prove enclosing-policy order, GUI ownership, installed
capability, actual routing or subscription persistence. D07's later preflight,
precise diff, permission, readback and verification stages remain independent.

## Versioned primary-source basis

The accompanying research was performed on 2026-10-18 UTC. Its SHA-256 is
`cf60a7bf2045af46058c825a1a452d4d075235eea148babd0983194103aa1bda`. Compatibility targets are deliberate fixed review pins, **not**
“latest”, a supported installation claim, or permission to install an engine.

- Mihomo **v1.19.32**, commit **88dcbf7f1614a67c3b36b848ee3592dfa92ada36**:
  [exact predicate](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/rules/common/domain.go),
  [suffix predicate](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/rules/common/domain_suffix.go),
  [provider pattern validation](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/component/trie/domain.go),
  [domain provider](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/rules/provider/domain_strategy.go),
  [classical provider](https://raw.githubusercontent.com/MetaCubeX/mihomo/88dcbf7f1614a67c3b36b848ee3592dfa92ada36/rules/provider/classical_strategy.go).
- sing-box **v1.12.0**, resolved release commit
  **2dcb86941f5db01bbe296acae555a3b1f38c0441**; source reads used the v1.12.0 tag:
  [source schema](https://raw.githubusercontent.com/SagerNet/sing-box/v1.12.0/option/rule_set.go),
  [domain item](https://raw.githubusercontent.com/SagerNet/sing-box/v1.12.0/route/rule/rule_item_domain.go),
  [rule construction](https://raw.githubusercontent.com/SagerNet/sing-box/v1.12.0/route/rule/rule_default.go),
  [condition matching](https://raw.githubusercontent.com/SagerNet/sing-box/v1.12.0/route/rule/rule_abstract.go).
  Its declared matcher dependency is sing **v0.7.0-beta.2**:
  [matcher](https://raw.githubusercontent.com/SagerNet/sing/v0.7.0-beta.2/common/domain/matcher.go).
  The research recorded cache misses for full-SHA sing-box raw URLs, so those are
  not misrepresented as successfully read immutable URLs.

The source-derived deductions are narrower than a runtime measurement. Main
Mihomo constructors lowercase configured patterns, while their match functions
and provider/other-engine candidate normalization differ. sing-box configured
patterns are not universally lowercased at the same boundary. Therefore silently
lowercasing an uppercase source pattern can change meaning. Leading-dot suffixes,
terminal dots and Unicode/A-label equivalence likewise cannot be guessed.

The pinned sing-box parser supports more source versions than this converter.
Only actual integer **1** is selected here; source versions 2, 3 or 5 are rejected
rather than treated as equivalent. Mutable online examples cannot update this
contract accidentally. Source semantics expansion needs a fresh versioned review.

## Profiles and canonical-host boundary

```python
convert_rule_format(source_bytes, source_profile, target_profile,
                    ordered_rule_refs, source_binding,
                    *, max_seconds=5, cancelled=lambda: False)
```

The only profile constants are:

| Constant | Exact profile identifier | Predicate syntax |
| --- | --- | --- |
| `EXACT` | `exact-domain-lines/0.1` | One exact host per LF/CRLF line |
| `MIHOMO_DOMAIN` | `mihomo/1.19.32/provider-domain-yaml` | Sole `payload` block sequence; bare exact or `+.host` suffix |
| `MIHOMO_CLASSICAL` | `mihomo/1.19.32/provider-classical-yaml` | Sole `payload` block sequence; exactly `DOMAIN,host` or `DOMAIN-SUFFIX,host` |
| `SING_BOX` | `sing-box/1.12.0/source-rule-set-json-v1` | Exact root `version`/`rules`; nonempty domain/domain_suffix arrays only |

No file-extension guessing, schema fallback, action binding or route configuration
is accepted. Exact lines allow an initial BOM and one optional terminal newline;
empty/comment/whitespace records reject. YAML permits plain, single-quoted or
double-quoted single-line string scalars; flow lists, multiline values, anchors,
aliases, explicit tags, duplicate keys and multiple documents reject. Escaping a
string is serialization, not permission to normalize its decoded host. The full
original source remains retained privately even when output formatting changes.
JSON is strict UTF-8 JSON without BOM/comments/non-finite constants. Duplicate
keys, including escape-equivalent keys, reject at any object level. Rule objects
may contain either or both domain families, but no additional condition or action.

Patterns must already be lowercase ASCII DNS labels: total length at most 253,
labels at most 63, no empty labels, padding, underscores, root dot, Unicode,
ports/paths or wildcards. Numeric-only host spellings conservatively reject;
`123.example.invalid` remains accepted. Lowercase `xn--` A-labels remain opaque
ASCII strings, with no decoding or Unicode equivalence claim. This differs from
the older importer, which preserves ASCII host case and excludes IDNA-looking
labels. Neither earlier behavior is changed or silently reused as a conversion.

Predicate meaning for canonical candidate `h` and stored domain `d`:

- exact: `h == d`
- suffix including apex: `h == d or h.endswith('.' + d)`

For `d = example.invalid`, a suffix includes `example.invalid`,
`a.example.invalid` and `a.b.example.invalid`; it excludes
`badexample.invalid`, `bad-example.invalid`, `example.invalid.evil` and unrelated
hosts. Exact includes only `d`. A hyphen never becomes a label boundary.

**Equivalence applies only to canonical lowercase ASCII candidate strings too.**
An uppercase, terminal-dot or Unicode incoming host is outside this proof scope,
not a passed cross-engine sample. No actual ingress-normalization or engine
matching has been measured. Source pattern validation alone cannot prove runtime
metadata is canonical.

All profiles are predicate OR collections. Order is preserved as provenance
traversal, not effective first-match policy. JSON preserves input rule order,
then actual object-key order and each list's order; one record is emitted for
one predicate. It never groups noncontiguous entries or sorts by specificity.
Same-kind/domain duplicates reject; exact and suffix overlap remain separate.
An unknown port/network/logical field cannot be discarded while extracting a
known domain, because that would widen the original predicate.

## Input, output and privacy contract

`source_bytes` must be exact built-in immutable bytes, nonempty and at most 1 MiB.
`ordered_rule_refs` is a list/tuple of 1–256 unique opaque aliases, one per flattened
predicate in traversal order. The exact source-binding schema is reused unchanged
from `rule_source_import`: `schema_version=guardian-rule-source-binding/0.1`,
`source_ref`, `expected_sha256`, `evidence_kind`, `verified_at`, `version_scope`,
`purpose`, `client_scope`, `feature_gate`, boolean `shared_service`, and fixed
`activation_state=candidate`. Unknown keys/subclass containers reject.

The complete source SHA-256 is computed and compared with `expected_sha256`.
Metadata and client references are immutably copied before later cancellation
callbacks. Both shared-service values remain declarations. Aliases use the existing
non-identifying ASCII/recognized-credential-shape boundary, not arbitrary secret
detection. Dates, source labels and compatibility profiles do not prove source
authenticity, freshness, independence, installed version or authorization.

Success returns a frozen/slotted `PrivateConversion` and immutable records:

- `preview()` exposes fixed status `converted_predicates_only`, bounded counts,
  `apply_supported=false`, `native_acceptance=not_run`,
  `equivalence_scope=canonical_lowercase_ascii_predicates_only`, and
  authenticity/freshness/independence/effective priority `not_established`.
  Source/body/domain/reference/digest/metadata values are absent. Offline
  explanation does not require action authorization.
- `private_material()` explicitly returns original `source_bytes`, computed
  `source_sha256`, fixed source/target profiles, complete `output_bytes`, computed
  `output_sha256`, immutable `declared_source` and ordered `records`.
- Each `PredicateRecord` retains `rule_ref`, flat zero-based `source_index`,
  `source_path`, optional one-based `source_line`, decoded `original_value`,
  `kind` (`exact_domain` or `suffix_including_apex`) and unchanged `domain`.
  Paths are `('lines', index)`, `('payload', index)` or
  `('rules', rule_index, field, array_index)`. JSON has no guessed line number;
  full original bytes plus the structural path preserve its provenance.
- Fixed repr and rejected default JSON/pickle export reduce accidental disclosure.
  A trusted host can explicitly inspect private output; this is not a Python
  sandbox. Returned mapping changes do not mutate private records or evidence.

Serialization is deterministic and complete, using LF and no sorting:

```text
example.invalid
```

```yaml
payload:
  - 'api.example.invalid'
  - '+.example.invalid'
```

```yaml
payload:
  - 'DOMAIN,api.example.invalid'
  - 'DOMAIN-SUFFIX,example.invalid'
```

```json
{"version":1,"rules":[{"domain":["api.example.invalid"]},{"domain_suffix":["example.invalid"]}]}
```

Each output ends with exactly one LF. JSON uses compact separators and singleton
objects in record order. Output contains predicates only; no enclosing policy,
provider retrieval path or default DIRECT is invented. Suffix → exact output
returns `UNREPRESENTABLE_MATCH`, even after preceding exact records are valid.

Defaults/bounds: input and output each at most 1 MiB, 256 predicates, 16 client
aliases, 5 seconds per original call (finite positive maximum 60). JSON additionally
has 48 nesting levels and 20,000 structural tokens; YAML reuses the existing bounded
safe parser. Checks occur initially, during parsing/records/rendering and just
before returning. Cancellation exceptions/non-booleans/true fail closed. Budget
checks are cooperative and do not preempt a parser mid-call. Exact and JSON work
without optional PyYAML; provider YAML returns `PARSER_UNAVAILABLE` without it.

`ConversionError` contains only a fixed code, never an output or private input.
Examples: `UNSUPPORTED_PROFILE`, `SOURCE_DIGEST_MISMATCH`,
`UNSUPPORTED_SCHEMA_VERSION`, `DUPLICATE_JSON_KEY`, `UNHANDLED_CONDITION`,
`NONCANONICAL_DOMAIN`, `DUPLICATE_PREDICATE`, `UNREPRESENTABLE_MATCH`,
`UNREPRESENTABLE_ACTION`, parser/input/reference/budget errors, `CANCELLED` and
`DEADLINE_EXCEEDED`. Failure is atomic: no partial bytes escape. A caller must
leave destinations untouched on conversion failure, and must independently
review any later write, readback and restore operation.

## Genuine before/after reproduction

The missing API test ran before the module existed and failed with
`ModuleNotFoundError: No module named 'rule_format_conversion'`. It subsequently
passes. The frozen eighth importer also rejects a provider as unsupported; this
is an intentional older capability boundary, not observed source corruption.

The same standalone reproducer below ran against eighth and ninth bytes without
using local Git HEAD as a content label. Both keep the older importer's
`UNSUPPORTED_RULE_FRAGMENT`. Eighth reports `converter_api_unavailable`; ninth
produces the exact JSON fixture above with source preservation and the conditional
public status. Its suffix→exact, added REJECT action and ASN examples return,
respectively, `UNREPRESENTABLE_MATCH`, `UNREPRESENTABLE_ACTION` and
`UNREPRESENTABLE_MATCH`. No real configuration or engine is involved.

Run with `PYTHONDONTWRITEBYTECODE=1 python -B /tmp/reproduce.py /path/to/tree`:

```python
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

repo = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(repo / 'skills/claude-guardian/scripts'))
raw = b"payload:\n  - 'DOMAIN,api.example.invalid'\n  - 'DOMAIN-SUFFIX,example.invalid'\n"
source = {'schema_version': 'guardian-rule-source-binding/0.1', 'source_ref': 'source-a',
    'expected_sha256': hashlib.sha256(raw).hexdigest(), 'evidence_kind': 'user_supplied',
    'verified_at': '2026-10-18', 'version_scope': 'pinned-v1', 'purpose': 'repair',
    'client_scope': ['client-a'], 'feature_gate': 'selected-feature',
    'shared_service': False, 'activation_state': 'candidate'}
refs = ['rule-exact', 'rule-suffix']
import rule_source_import as old
try:
    old.import_rule_bindings(raw, 'mihomo-domain-rules-fragment/0.1', refs, source,
                            {'kind': 'user_selected_egress', 'group_name': 'approved-group'})
except old.SourceImportError as exc:
    print(json.dumps({'case': 'existing_importer_on_provider', 'error': str(exc)}, sort_keys=True))
if importlib.util.find_spec('rule_format_conversion') is None:
    print(json.dumps({'case': 'provider_conversion', 'status': 'converter_api_unavailable'}, sort_keys=True))
    raise SystemExit(0)
import rule_format_conversion as converter
result = converter.convert_rule_format(raw, converter.MIHOMO_CLASSICAL, converter.SING_BOX, refs, source)
private = result.private_material()
print(json.dumps({'case': 'provider_conversion', 'preview': result.preview(),
    'source_preserved': private['source_bytes'] == raw,
    'output': private['output_bytes'].decode('ascii')}, sort_keys=True))
for target, changed in ((converter.EXACT, raw),
        (converter.SING_BOX, raw.replace(b'DOMAIN,api.example.invalid', b'DOMAIN,api.example.invalid,REJECT')),
        (converter.SING_BOX, raw.replace(b'DOMAIN,api.example.invalid', b'IP-ASN,64512'))):
    declared = dict(source, expected_sha256=hashlib.sha256(changed).hexdigest())
    try:
        converter.convert_rule_format(changed, converter.MIHOMO_CLASSICAL, target, refs, declared)
    except converter.ConversionError as exc:
        print(json.dumps({'case': 'loss_rejection', 'error': str(exc)}, sort_keys=True))
```

## Tests, maintenance and remaining work

The converter tests freeze serialized bytes across all sixteen exact-only profile
pairs and the three suffix-capable profiles; verify apex/deep descendants and
lookalike negatives; retain field/list/source-reference order and provenance;
and cover schema lookalikes/v5, duplicate keys, unsupported conditions/actions,
noncanonical patterns, whole-batch failure in both orders, immutable/private
boundaries, no I/O, resource limits, cancellation/deadline, and detached packaged
use without site packages. These are source-derived canonical predicate fixtures,
not native-engine certification. Independent transaction-composition evidence is
kept separate as linked above.

Recorded final cloud Linux checks on 2026-10-18:

| Check | Actual result |
| --- | --- |
| New converter suite | 47 passed |
| Existing source importer suite | 45 passed |
| Source/package suites | 23 passed |
| Accepted-case ledger integrity | 3 passed |
| Full Python aggregate, including separate transaction composition | 1,342 run: 1,334 passed, 8 skipped |
| Compilation and new-file Python 3.10 syntax | Passed |
| WebRTC lifecycle Node suite | 8 synthetic scenarios passed |
| Dashboard protocol Node suite | Passed, synthetic only |
| Two independent Skill builds | Byte-identical; SHA-256 `574e4334b003794752103cdb4121c36a237a48b60a7e9306f0f04cea1940eb4b` |

Exact owned-file hashes, scoped replayable patch, failing-first/before-after logs
and final test logs accompany the batch receipt. Skipped platform cases are not
passed, and these results provide no engine/browser/user-device certification.

Only a new module, its tests, one package allowlist entry and active Agent
procedure are added here. Existing parsers/importer/compiler/execution semantics
remain unchanged. The package entry is pinned by accepted T09 evidence, requiring
independent source/package re-review and a current page/ledger pin; no source
independence or new original-case acceptance follows from that maintenance.

The tradeoff is deliberate: useful fixed-profile predicate conversion without
new dependencies, engine install, scanners, services or a broad policy framework.
Unsupported patterns/actions need explanation or a separately reviewed future
adapter. A host still must select feature scope, preserve provenance, re-read
changed sources and verify the actual target version and surrounding configuration.
A rollback of this increment removes the helper/test/package entry/guidance;
there is no configuration migration or user-device restoration required by the
pure function itself.
