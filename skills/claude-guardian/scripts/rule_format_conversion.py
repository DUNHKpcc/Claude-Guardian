"""Pure fixed-profile predicate conversion, never policy or runtime equivalence.

Compatibility targets: Mihomo v1.19.32 and sing-box v1.12.0 source schema v1.
Only canonical lowercase ASCII hosts enter the conditional predicate-set claim.
Source bytes, declared provenance and record traversal order stay private.
"""
from dataclasses import dataclass
import hashlib
import json
import time

import config_edit_plan as config
import rule_source_import as source

EXACT = 'exact-domain-lines/0.1'
MIHOMO_DOMAIN = 'mihomo/1.19.32/provider-domain-yaml'
MIHOMO_CLASSICAL = 'mihomo/1.19.32/provider-classical-yaml'
SING_BOX = 'sing-box/1.12.0/source-rule-set-json-v1'
PROFILES = (EXACT, MIHOMO_DOMAIN, MIHOMO_CLASSICAL, SING_BOX)
MAX_BYTES = source.MAX_BYTES
MAX_RECORDS = source.MAX_RECORDS
MAX_CLIENTS = source.MAX_CLIENTS
MAX_JSON_TOKENS = 20000
MAX_JSON_DEPTH = 48


class ConversionError(ValueError):
    """Fixed non-sensitive code; no partial artifact or caller data in errors."""


def _fail(code):
    raise ConversionError(code) from None


def _canonical_domain(value):
    # A-labels are opaque ASCII, never an IDNA conversion or Unicode equivalence.
    # Numeric-only hosts conservatively reject ambiguous address-like spellings.
    return (type(value) is str and value.isascii() and value == value.lower()
            and config._valid_domain(value)
            and not all(label.isdigit() for label in value.split('.')))


@dataclass(frozen=True, slots=True, repr=False)
class PredicateRecord:
    rule_ref: str
    source_index: int
    source_path: tuple
    source_line: int | None
    original_value: str
    kind: str
    domain: str

    def __repr__(self):
        return '<PredicateRecord: private source data omitted>'

    def __reduce_ex__(self, protocol):
        raise TypeError('private predicate record serialization disabled')


@dataclass(frozen=True, slots=True, repr=False)
class PrivateConversion:
    _source: bytes
    _source_profile: str
    _target_profile: str
    _source_digest: str
    _declared: tuple
    _records: tuple
    _output: bytes
    _output_digest: str

    def __repr__(self):
        return '<PrivateConversion: predicates only; private data omitted>'

    def __reduce_ex__(self, protocol):
        raise TypeError('private conversion serialization disabled')

    def preview(self):
        return {'schema_version': 'guardian-rule-conversion-preview/0.1',
                'status': 'converted_predicates_only', 'record_count': len(self._records),
                'exact_count': sum(row.kind == 'exact_domain' for row in self._records),
                'suffix_count': sum(row.kind == 'suffix_including_apex' for row in self._records),
                'output_bytes_count': len(self._output), 'apply_supported': False,
                'native_acceptance': 'not_run',
                'equivalence_scope': 'canonical_lowercase_ascii_predicates_only',
                'source_authenticity': 'not_established', 'source_freshness': 'not_established',
                'independent_sources': 'not_established', 'effective_priority': 'not_established',
                'authorization': 'not_required_for_offline_conversion'}

    def private_material(self):
        return {'source_bytes': self._source, 'source_sha256': self._source_digest,
                'source_profile': self._source_profile, 'target_profile': self._target_profile,
                'output_bytes': self._output, 'output_sha256': self._output_digest,
                'declared_source': self._declared, 'records': self._records}


def _plain(text, guard):
    if text.startswith('\ufeff'):
        text = text[1:]
    chunks = text.split('\n')
    if chunks[-1] == '':
        chunks.pop()
    entries = []
    for index, chunk in enumerate(chunks):
        guard()
        if len(entries) >= MAX_RECORDS:
            _fail('TOO_MANY_SOURCE_RECORDS')
        terminated = index < len(chunks) - 1 or text.endswith('\n')
        value = chunk[:-1] if terminated and chunk.endswith('\r') else chunk
        if not value:
            _fail('EMPTY_SOURCE_RECORD')
        entries.append((('lines', index), index + 1, value, 'exact_domain', value))
    return entries


def _provider(raw, profile, guard):
    try:
        _, root = config._parse(raw)
        top = config._mapping(root)
    except config.EditPlanError as exc:
        if str(exc) in ('PARSER_UNAVAILABLE', 'YAML_BUDGET_EXCEEDED'):
            _fail(str(exc))
        _fail('INVALID_PROVIDER_YAML')
    guard()
    if 'rules' in top:
        _fail('UNREPRESENTABLE_ACTION')
    if set(top) != {'payload'}:
        _fail('UNSUPPORTED_SOURCE_STRUCTURE')
    node = top['payload']
    if not isinstance(node, config.yaml.nodes.SequenceNode) or node.flow_style:
        _fail('UNSUPPORTED_PROVIDER_SYNTAX')
    if len(node.value) > MAX_RECORDS:
        _fail('TOO_MANY_SOURCE_RECORDS')
    entries = []
    for index, item in enumerate(node.value):
        guard()
        if (not isinstance(item, config.yaml.nodes.ScalarNode)
                or item.tag != 'tag:yaml.org,2002:str' or item.style not in (None, "'", '"')
                or item.start_mark.line != item.end_mark.line):
            _fail('UNSUPPORTED_PROVIDER_SYNTAX')
        value = item.value
        if profile == MIHOMO_DOMAIN:
            if value.startswith('+.'):
                kind, domain = 'suffix_including_apex', value[2:]
            elif value.startswith(('.', '*', '+')) or ',' in value:
                _fail('UNREPRESENTABLE_MATCH')
            else:
                kind, domain = 'exact_domain', value
        else:
            fields = value.split(',')
            if len(fields) > 2:
                _fail('UNREPRESENTABLE_ACTION')
            if len(fields) != 2 or fields[0] not in ('DOMAIN', 'DOMAIN-SUFFIX'):
                _fail('UNREPRESENTABLE_MATCH')
            kind = 'exact_domain' if fields[0] == 'DOMAIN' else 'suffix_including_apex'
            domain = fields[1]
        entries.append((('payload', index), item.start_mark.line + 1, value, kind, domain))
    return entries


def _json_budget(text, guard):
    # Count structural tokens outside strings before decoding. No raw input in
    # parser errors; bounds supplement (not replace) the complete-byte limit.
    depth = tokens = 0
    quoted = escaped = False
    for index, char in enumerate(text):
        if index % 4096 == 0:
            guard()
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '{}[],:':
            tokens += 1
            if char in '{[':
                depth += 1
            elif char in '}]':
                depth -= 1
            if depth > MAX_JSON_DEPTH or tokens > MAX_JSON_TOKENS:
                _fail('JSON_BUDGET_EXCEEDED')


def _json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _json_constant(_):
    _fail('INVALID_RULE_SET_JSON')


def _rule_set(text, guard):
    _json_budget(text, guard)
    try:
        root = json.loads(text, object_pairs_hook=_json_pairs, parse_constant=_json_constant)
    except ConversionError:
        raise
    except (ValueError, TypeError, RecursionError):
        _fail('INVALID_RULE_SET_JSON')
    guard()
    if type(root) is not dict or set(root) != {'version', 'rules'}:
        _fail('UNSUPPORTED_SOURCE_STRUCTURE')
    if type(root['version']) is not int or root['version'] != 1:
        _fail('UNSUPPORTED_SCHEMA_VERSION')
    rules = root['rules']
    if type(rules) is not list or not rules:
        _fail('UNSUPPORTED_SOURCE_STRUCTURE')
    if len(rules) > MAX_RECORDS:
        _fail('TOO_MANY_SOURCE_RECORDS')
    entries = []
    for index, rule in enumerate(rules):
        guard()
        if type(rule) is not dict or not rule:
            _fail('UNSUPPORTED_SOURCE_STRUCTURE')
        if {'action', 'outbound'} & set(rule):
            _fail('UNREPRESENTABLE_ACTION')
        if set(rule) - {'domain', 'domain_suffix'}:
            _fail('UNHANDLED_CONDITION')
        for key, values in rule.items():
            if type(values) is not list or not values:
                _fail('UNSUPPORTED_SOURCE_STRUCTURE')
            kind = 'exact_domain' if key == 'domain' else 'suffix_including_apex'
            for item_index, value in enumerate(values):
                guard()
                if len(entries) >= MAX_RECORDS:
                    _fail('TOO_MANY_SOURCE_RECORDS')
                entries.append((('rules', index, key, item_index), None, value, kind, value))
    return entries


def _render(records, profile, guard):
    values = []
    for row in records:
        guard()
        suffix = row.kind == 'suffix_including_apex'
        if profile == EXACT:
            if suffix:
                _fail('UNREPRESENTABLE_MATCH')
            values.append(row.domain)
        elif profile == MIHOMO_DOMAIN:
            values.append(('+.' if suffix else '') + row.domain)
        elif profile == MIHOMO_CLASSICAL:
            values.append(('DOMAIN-SUFFIX,' if suffix else 'DOMAIN,') + row.domain)
        else:
            values.append({'domain_suffix' if suffix else 'domain': [row.domain]})
    if profile == SING_BOX:
        output = (json.dumps({'version': 1, 'rules': values}, ensure_ascii=True,
                             separators=(',', ':')) + '\n').encode('ascii')
    elif profile == EXACT:
        output = ('\n'.join(values) + '\n').encode('ascii')
    else:
        output = ('payload:\n' + ''.join("  - '" + value + "'\n" for value in values)).encode('ascii')
    if len(output) > MAX_BYTES:
        _fail('OUTPUT_BUDGET_EXCEEDED')
    return output


def convert_rule_format(source_bytes, source_profile, target_profile,
                        ordered_rule_refs, source_binding, *, max_seconds=5,
                        cancelled=lambda: False):
    """Convert a whole predicate batch or raise a fixed code without an artifact.

    Profiles never guess an installed version. Order is provenance traversal,
    not first-match policy. No action is inferred, added, removed or executed.
    """
    if type(max_seconds) not in (int, float) or not 0 < max_seconds <= 60:
        _fail('INVALID_DEADLINE')
    deadline = time.monotonic() + max_seconds
    def guard():
        try:
            stopped = cancelled()
        except Exception:
            _fail('CANCELLED')
        if type(stopped) is not bool or stopped:
            _fail('CANCELLED')
        if time.monotonic() >= deadline:
            _fail('DEADLINE_EXCEEDED')
    guard()
    if (type(source_profile) is not str or source_profile not in PROFILES
            or type(target_profile) is not str or target_profile not in PROFILES):
        _fail('UNSUPPORTED_PROFILE')
    if type(source_bytes) is not bytes or not 0 < len(source_bytes) <= MAX_BYTES:
        _fail('INVALID_OR_OVERSIZED_SOURCE')
    try:
        refs = source._references(ordered_rule_refs, MAX_RECORDS, 'INVALID_RULE_REFERENCES',
                                  'DUPLICATE_RULE_REFERENCE')
        declared = source._source_binding(source_binding)
    except source.SourceImportError as exc:
        _fail(str(exc))
    digest = hashlib.sha256(source_bytes).hexdigest()
    if digest != dict(declared)['expected_sha256']:
        _fail('SOURCE_DIGEST_MISMATCH')
    try:
        text = source_bytes.decode('utf-8')
    except UnicodeError:
        _fail('INVALID_SOURCE_ENCODING')
    guard()
    if source_profile == EXACT:
        entries = _plain(text, guard)
    elif source_profile == SING_BOX:
        entries = _rule_set(text, guard)
    else:
        entries = _provider(source_bytes, source_profile, guard)
    if not entries:
        _fail('EMPTY_SOURCE_BATCH')
    if len(entries) != len(refs):
        _fail('RULE_REFERENCE_COUNT_MISMATCH')
    records, seen = [], set()
    for index, (ref, entry) in enumerate(zip(refs, entries)):
        guard()
        path, line, original, kind, domain = entry
        if not _canonical_domain(domain):
            _fail('NONCANONICAL_DOMAIN')
        selector = kind, domain
        if selector in seen:
            _fail('DUPLICATE_PREDICATE')
        seen.add(selector)
        records.append(PredicateRecord(ref, index, path, line, original, kind, domain))
    output = _render(records, target_profile, guard)
    output_digest = hashlib.sha256(output).hexdigest()
    guard()
    return PrivateConversion(source_bytes, source_profile, target_profile, digest,
                             declared, tuple(records), output, output_digest)
