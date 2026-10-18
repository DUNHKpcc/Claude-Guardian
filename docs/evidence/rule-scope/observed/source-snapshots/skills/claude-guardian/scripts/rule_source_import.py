"""Pure, bounded import of explicitly selected domain-rule source bytes.

Only the two declared grammars below are supported. This is not a provider or
other-engine converter, trusted-source verifier, file reader or execution grant.
No source is fetched, expanded, sorted, filtered or deduplicated. Metadata is a
caller declaration; all configuration/ownership/priority gates remain downstream.
"""
from dataclasses import dataclass
from datetime import date
import hashlib
import ipaddress
import re
import time

import config_edit_plan as config
from source_evidence import _CREDENTIAL_ALIAS

FORMATS = ('exact-domain-lines/0.1', 'mihomo-domain-rules-fragment/0.1')
BINDING_SCHEMA = 'guardian-rule-source-binding/0.1'
MAX_BYTES = 1024 * 1024
MAX_RECORDS = 256
MAX_CLIENTS = 16
_ALIAS = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}\Z')
_DIGEST = re.compile(r'[a-f0-9]{64}\Z')
_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}\Z')


class SourceImportError(ValueError):
    """Fixed code only; supplied bytes, references and metadata are never echoed."""


def _fail(code):
    raise SourceImportError(code) from None


def _alias(value):
    return (type(value) is str and _ALIAS.fullmatch(value) is not None
            and _CREDENTIAL_ALIAS.search(value) is None)


def _domain(value):
    # Numeric-only hosts are an explicitly unsupported ambiguous subset, not
    # a complete detector or normalizer for historical address spellings.
    # No IDNA, root-dot, wildcard or literal-address interpretation is added.
    if (not value.isascii() or not config._valid_domain(value)
            or any(label.lower().startswith('xn--') for label in value.split('.'))
            or all(label.isdigit() for label in value.split('.'))):
        return False
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return True
    return False


def _references(value, maximum, invalid, duplicate):
    if type(value) not in (list, tuple) or not 0 < len(value) <= maximum:
        _fail(invalid)
    if any(not _alias(item) for item in value):
        _fail(invalid)
    if len(set(value)) != len(value):
        _fail(duplicate)
    return tuple(value)


def _source_binding(value):
    fields = {'schema_version', 'source_ref', 'expected_sha256', 'evidence_kind',
              'verified_at', 'version_scope', 'purpose', 'client_scope',
              'feature_gate', 'shared_service', 'activation_state'}
    if (type(value) is not dict or any(type(key) is not str for key in value)
            or set(value) != fields):
        _fail('INVALID_SOURCE_BINDING')
    if (type(value['schema_version']) is not str or value['schema_version'] != BINDING_SCHEMA
            or not all(_alias(value[key]) for key in ('source_ref', 'version_scope', 'purpose', 'feature_gate'))
            or type(value['expected_sha256']) is not str
            or not _DIGEST.fullmatch(value['expected_sha256'])
            or type(value['evidence_kind']) is not str
            or value['evidence_kind'] not in ('official_documentation', 'user_supplied', 'reference_material')
            or type(value['shared_service']) is not bool
            or type(value['activation_state']) is not str or value['activation_state'] != 'candidate'):
        _fail('INVALID_SOURCE_BINDING')
    stamp = value['verified_at']
    if type(stamp) is not str or not _DATE.fullmatch(stamp):
        _fail('INVALID_SOURCE_BINDING')
    try:
        date.fromisoformat(stamp)
    except ValueError:
        _fail('INVALID_SOURCE_BINDING')
    clients = _references(value['client_scope'], MAX_CLIENTS,
                          'INVALID_SOURCE_BINDING', 'INVALID_SOURCE_BINDING')
    # Immutable copies retain all supplied declarations without promoting them.
    return tuple((key, clients if key == 'client_scope' else value[key])
                 for key in sorted(fields))


@dataclass(frozen=True, slots=True, repr=False)
class RuleRecord:
    rule_ref: str
    source_index: int
    source_line: int
    start: int
    end: int
    original_record: bytes
    kind: str
    domain: str
    source_action: str | None
    action: str

    def __repr__(self):
        return '<RuleRecord: private source data omitted>'

    def __reduce_ex__(self, protocol):
        raise TypeError('private rule record serialization disabled')


@dataclass(frozen=True, slots=True, repr=False)
class PrivateRuleImport:
    _source: bytes
    _digest: str
    _format: str
    _declared: tuple
    _records: tuple
    _group: str

    def __repr__(self):
        return '<PrivateRuleImport: candidate only; private source data omitted>'

    def __reduce_ex__(self, protocol):
        raise TypeError('private rule import serialization disabled')

    def preview(self):
        return {'schema_version': 'guardian-rule-source-preview/0.1',
                'status': 'imported_candidate_only', 'record_count': len(self._records),
                'exact_count': sum(row.kind == 'DOMAIN' for row in self._records),
                'suffix_count': sum(row.kind == 'DOMAIN-SUFFIX' for row in self._records),
                'apply_supported': False, 'native_acceptance': 'not_run',
                'source_authenticity': 'not_established', 'source_freshness': 'not_established',
                'independent_sources': 'not_established', 'effective_priority': 'not_established',
                'authorization': 'not_required_for_offline_conversion'}

    def binding_components(self):
        """Fresh mutable copies for a separately validated private repair binding."""
        return {'rules': {row.rule_ref: {'kind': row.kind, 'domain': row.domain}
                          for row in self._records},
                'rule_order': [row.rule_ref for row in self._records],
                'group_name': self._group}

    def private_material(self):
        """Explicit private host review only; never public logs or default exports."""
        return {'source_bytes': self._source, 'source_sha256': self._digest,
                'source_format': self._format, 'declared_source': self._declared,
                'records': self._records}


def _plain_records(text, guard):
    # Only LF/CRLF separators and one optional final terminator are grammar.
    # splitlines() would silently accept Unicode separators and other controls.
    chunks = text.split('\n')
    if chunks[-1] == '':
        chunks.pop()
    offset = 0
    records = []
    for index, chunk in enumerate(chunks):
        guard()
        terminated = index < len(chunks) - 1 or text.endswith('\n')
        value = chunk[:-1] if terminated and chunk.endswith('\r') else chunk
        if not value:
            _fail('EMPTY_SOURCE_RECORD')
        if len(records) >= MAX_RECORDS:
            _fail('TOO_MANY_SOURCE_RECORDS')
        if not _domain(value):
            _fail('UNSUPPORTED_DOMAIN')
        records.append((index + 1, offset, offset + len(value), value, 'DOMAIN', value, None))
        offset += len(chunk) + (1 if terminated else 0)
    return records


def _fragment_records(raw, guard):
    try:
        text, root = config._parse(raw)
        top = config._mapping(root)
    except config.EditPlanError as exc:
        if str(exc) in ('PARSER_UNAVAILABLE', 'YAML_BUDGET_EXCEEDED'):
            _fail(str(exc))
        _fail('INVALID_RULE_FRAGMENT')
    guard()
    if set(top) != {'rules'}:
        _fail('UNSUPPORTED_RULE_FRAGMENT')
    node = top['rules']
    if not isinstance(node, config.yaml.nodes.SequenceNode) or node.flow_style:
        _fail('UNSUPPORTED_RULE_FRAGMENT')
    if len(node.value) > MAX_RECORDS:
        _fail('TOO_MANY_SOURCE_RECORDS')
    records = []
    for item in node.value:
        guard()
        if (not isinstance(item, config.yaml.nodes.ScalarNode)
                or item.tag != 'tag:yaml.org,2002:str' or item.style is not None
                or item.start_mark.line != item.end_mark.line):
            _fail('UNSUPPORTED_RULE_FRAGMENT')
        match = config._RULE.fullmatch(item.value)
        if not match or not _domain(match.group(2)):
            _fail('UNSUPPORTED_RULE_RECORD')
        if not _alias(match.group(3)):
            _fail('INVALID_SOURCE_ACTION')
        start, end = item.start_mark.index, item.end_mark.index
        if text[start:end] != item.value:
            _fail('UNSUPPORTED_RULE_FRAGMENT')
        records.append((item.start_mark.line + 1, start, end, item.value,
                        match.group(1), match.group(2), match.group(3)))
    return text, records


def import_rule_bindings(source_bytes, format_id, ordered_rule_refs, source_binding,
                         action_intent, *, max_seconds=5, cancelled=lambda: False):
    """Import a complete supplied batch, atomically, without reading or writing.

    exact-domain-lines explicitly means exact-host-only matching. DOMAIN-SUFFIX
    retains the existing compiler's suffix selector, not a wildcard conversion.
    Names retain their original ASCII case. Case folding is used only to reject
    duplicate selectors. Hashes bind supplied bytes, not authenticity/freshness.
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
    if type(format_id) is not str or format_id not in FORMATS:
        _fail('UNSUPPORTED_SOURCE_FORMAT')
    if type(source_bytes) is not bytes or not 0 < len(source_bytes) <= MAX_BYTES:
        _fail('INVALID_OR_OVERSIZED_SOURCE')
    refs = _references(ordered_rule_refs, MAX_RECORDS, 'INVALID_RULE_REFERENCES',
                       'DUPLICATE_RULE_REFERENCE')
    declared = _source_binding(source_binding)
    if (type(action_intent) is not dict or any(type(key) is not str for key in action_intent)
            or set(action_intent) != {'kind', 'group_name'}
            or type(action_intent['kind']) is not str or action_intent['kind'] != 'user_selected_egress'
            or not _alias(action_intent['group_name'])
            or action_intent['group_name'] in ('DIRECT', 'REJECT')):
        _fail('EXPLICIT_ACTION_REQUIRED')
    group = action_intent['group_name']
    guard()
    digest = hashlib.sha256(source_bytes).hexdigest()
    if digest != dict(declared)['expected_sha256']:
        _fail('SOURCE_DIGEST_MISMATCH')
    try:
        text = source_bytes.decode('utf-8')
    except UnicodeError:
        _fail('INVALID_SOURCE_ENCODING')
    if format_id == FORMATS[0]:
        # Preserve a supplied BOM in source_bytes and byte offsets, not the host.
        bom = 1 if text.startswith('\ufeff') else 0
        entries = _plain_records(text[bom:], guard)
        entries = [(line, start + bom, end + bom, record, kind, domain, action)
                   for line, start, end, record, kind, domain, action in entries]
    else:
        text, entries = _fragment_records(source_bytes, guard)
    if not entries:
        _fail('EMPTY_SOURCE_BATCH')
    if len(entries) != len(refs):
        _fail('RULE_REFERENCE_COUNT_MISMATCH')
    rows, seen = [], set()
    for index, (ref, entry) in enumerate(zip(refs, entries)):
        guard()
        line, start_char, end_char, original, kind, domain, source_action = entry
        if source_action is not None and source_action != group:
            _fail('SOURCE_ACTION_CONFLICT')
        selector = (kind, domain.lower())
        if selector in seen:
            _fail('DUPLICATE_RULE_SELECTOR')
        seen.add(selector)
        start = len(text[:start_char].encode('utf-8'))
        end = len(text[:end_char].encode('utf-8'))
        raw_record = source_bytes[start:end]
        if raw_record != original.encode('utf-8'):
            _fail('SOURCE_OFFSET_MISMATCH')
        rows.append(RuleRecord(ref, index, line, start, end, raw_record,
                               kind, domain, source_action, group))
    guard()
    return PrivateRuleImport(source_bytes, digest, format_id, declared, tuple(rows), group)
