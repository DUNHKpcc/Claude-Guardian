"""Pure ordered main-rule conversion under explicit, unverified declarations.

Pinned profiles describe fragments, never installed engines or complete policy.
No filesystem, network, engine execution, authorization, or configuration writes.
"""
from dataclasses import dataclass
import hashlib
import json
import time

import config_edit_plan as config
import rule_format_conversion as predicates
import rule_source_import as source

MIHOMO = 'mihomo/1.19.32/main-rules-yaml'
SING_BOX = 'sing-box/1.12.0/route-rules-json'
PROFILES = (MIHOMO, SING_BOX)
MAX_BYTES = source.MAX_BYTES
MAX_RECORDS = source.MAX_RECORDS
MAX_MAPPINGS = 256
DEFER = 'defer_to_enclosing_configuration'
RESERVED_POLICY_LABELS = frozenset({
    'DIRECT', 'REJECT', 'REJECT-DROP', 'COMPATIBLE', 'PASS', 'PASS-RULE', 'GLOBAL',
})
_BINDING_KEYS = frozenset({'source_label', 'target_label', 'source_kind', 'target_kind',
                           'source_finality', 'target_finality'})


class PolicyConversionError(ValueError):
    """Fixed code only; failures never carry source data or partial output."""


def _fail(code):
    raise PolicyConversionError(code) from None


def _label(value):
    if not source._alias(value):
        _fail('INVALID_OUTBOUND_LABEL')
    if value in RESERVED_POLICY_LABELS:
        _fail('RESERVED_ACTION_COLLISION')
    return value


def _bindings(value):
    if type(value) not in (list, tuple) or not 0 < len(value) <= MAX_MAPPINGS:
        _fail('INVALID_OUTBOUND_BINDINGS')
    rows, sources, targets = [], set(), set()
    for row in value:
        if (type(row) is not dict or any(type(key) is not str for key in row)
                or set(row) != _BINDING_KEYS):
            _fail('INVALID_OUTBOUND_BINDINGS')
        a, b = _label(row['source_label']), _label(row['target_label'])
        if a in sources or b in targets:
            _fail('AMBIGUOUS_OUTBOUND_BINDINGS')
        for key in ('source_kind', 'target_kind'):
            if type(row[key]) is not str or row[key] != 'ordinary_outbound':
                _fail('UNREPRESENTABLE_ACTION')
        for key in ('source_finality', 'target_finality'):
            if type(row[key]) is not str or row[key] != 'terminal_for_tcp_udp':
                _fail('UNKNOWN_OUTBOUND_FINALITY')
        sources.add(a)
        targets.add(b)
        rows.append(tuple((key, row[key]) for key in sorted(_BINDING_KEYS)))
    return tuple(rows)


@dataclass(frozen=True, slots=True, repr=False)
class PolicyOccurrence:
    source_rule_ref: str
    source_rule_index: int
    predicate_index: int
    source_path: tuple
    source_line: int | None
    original_value: str
    kind: str
    domain: str
    source_action: tuple
    target_action: tuple

    def __repr__(self):
        return '<PolicyOccurrence: private data omitted>'

    def __reduce_ex__(self, protocol):
        raise TypeError('private policy occurrence serialization disabled')


@dataclass(frozen=True, slots=True, repr=False)
class PrivatePolicyConversion:
    _source: bytes
    _source_profile: str
    _target_profile: str
    _source_digest: str
    _declared: tuple
    _bindings: tuple
    _records: tuple
    _output: bytes
    _output_digest: str
    _refs: tuple
    _output_map: tuple

    def __repr__(self):
        return '<PrivatePolicyConversion: private data omitted>'

    def __reduce_ex__(self, protocol):
        raise TypeError('private policy conversion serialization disabled')

    def preview(self):
        return {
            'schema_version': 'guardian-policy-conversion-preview/0.1',
            'status': 'converted_ordered_labels_under_declared_preconditions',
            'source_rule_count': len(self._refs), 'predicate_count': len(self._records),
            'outbound_count': len(self._bindings),
            'equivalence_scope': 'canonical_lowercase_ascii_tcp_udp_label_selection',
            'outbound_finality_evidence': 'declared_unverified',
            'no_match_contract': DEFER, 'enclosing_fallback': 'not_established',
            'runtime_behavior': 'not_established',
            'effective_priority': 'not_established', 'actual_egress': 'not_established',
            'source_authenticity': 'not_established', 'source_freshness': 'not_established',
            'independent_sources': 'not_established', 'native_acceptance': 'not_run',
            'apply_supported': False, 'authorization': 'not_required_for_offline_conversion',
        }

    def private_material(self):
        return {
            'source_bytes': self._source, 'source_sha256': self._source_digest,
            'source_profile': self._source_profile, 'target_profile': self._target_profile,
            'declared_source': self._declared, 'outbound_bindings': self._bindings,
            'records': self._records, 'ordered_rule_refs': self._refs,
            'output_bytes': self._output, 'output_sha256': self._output_digest,
            'output_occurrence_map': self._output_map,
            'source_no_match': DEFER, 'target_no_match': DEFER,
        }


def _mihomo(raw, guard):
    # SafeLoader is optional and already used by the existing offline tooling.
    # Inspect events before composition to reject anchors/tags and bound work.
    yaml = config.yaml
    if yaml is None:
        _fail('PARSER_UNAVAILABLE')
    depth = count = documents = 0
    try:
        for event in yaml.parse(raw.decode('utf-8'), Loader=yaml.SafeLoader):
            guard()
            count += 1
            if count > config.MAX_NODES:
                _fail('YAML_BUDGET_EXCEEDED')
            if (isinstance(event, yaml.events.AliasEvent)
                    or getattr(event, 'anchor', None) or getattr(event, 'tag', None)):
                _fail('UNSUPPORTED_YAML')
            if isinstance(event, yaml.events.DocumentStartEvent):
                documents += 1
                if documents != 1 or event.version is not None or event.tags:
                    _fail('UNSUPPORTED_YAML')
            if isinstance(event, (yaml.events.SequenceStartEvent, yaml.events.MappingStartEvent)):
                depth += 1
                if depth > 48:
                    _fail('YAML_BUDGET_EXCEEDED')
            if isinstance(event, (yaml.events.SequenceEndEvent, yaml.events.MappingEndEvent)):
                depth -= 1
        guard()
        root = yaml.compose(raw.decode('utf-8'), Loader=yaml.SafeLoader)
        guard()
    except (UnicodeError, yaml.YAMLError, ValueError, TypeError, RecursionError) as exc:
        if isinstance(exc, PolicyConversionError):
            raise
        _fail('INVALID_MAIN_RULE_YAML')
    if (not isinstance(root, yaml.nodes.MappingNode) or root.flow_style
            or len(root.value) != 1):
        _fail('UNSUPPORTED_SOURCE_STRUCTURE')
    key, node = root.value[0]
    if (not isinstance(key, yaml.nodes.ScalarNode) or key.tag != 'tag:yaml.org,2002:str'
            or key.value != 'rules' or not isinstance(node, yaml.nodes.SequenceNode)
            or node.flow_style):
        _fail('UNSUPPORTED_SOURCE_STRUCTURE')
    if not node.value:
        _fail('EMPTY_SOURCE_BATCH')
    if len(node.value) > MAX_RECORDS:
        _fail('TOO_MANY_SOURCE_RULES')
    entries = []
    for index, item in enumerate(node.value):
        guard()
        if (not isinstance(item, yaml.nodes.ScalarNode) or item.tag != 'tag:yaml.org,2002:str'
                or item.style not in (None, "'", '"')
                or item.start_mark.line != item.end_mark.line):
            _fail('UNSUPPORTED_MAIN_RULE_SYNTAX')
        fields = item.value.split(',')
        if len(fields) != 3:
            _fail('UNREPRESENTABLE_ACTION')
        if fields[0] not in ('DOMAIN', 'DOMAIN-SUFFIX'):
            _fail('UNREPRESENTABLE_MATCH')
        kind = 'exact_domain' if fields[0] == 'DOMAIN' else 'suffix_including_apex'
        entries.append((index, 0, ('rules', index), item.start_mark.line + 1,
                        item.value, kind, fields[1], _label(fields[2])))
    return len(node.value), entries


def _sing_box(text, guard):
    try:
        predicates._json_budget(text, guard)
        root = json.loads(text, object_pairs_hook=predicates._json_pairs,
                          parse_constant=predicates._json_constant)
    except predicates.ConversionError as exc:
        code = str(exc)
        _fail('INVALID_ROUTE_JSON' if code == 'INVALID_RULE_SET_JSON' else code)
    except PolicyConversionError:
        raise
    except (ValueError, TypeError, RecursionError):
        _fail('INVALID_ROUTE_JSON')
    guard()
    if type(root) is not list or not root:
        _fail('UNSUPPORTED_SOURCE_STRUCTURE')
    if len(root) > MAX_RECORDS:
        _fail('TOO_MANY_SOURCE_RULES')
    entries = []
    for index, rule in enumerate(root):
        guard()
        if type(rule) is not dict:
            _fail('UNSUPPORTED_SOURCE_STRUCTURE')
        if type(rule.get('action')) is not str or rule['action'] != 'route':
            _fail('UNREPRESENTABLE_ACTION')
        label = _label(rule.get('outbound'))
        if set(rule) - {'action', 'outbound', 'domain', 'domain_suffix'}:
            _fail('UNHANDLED_CONDITION')
        if not {'domain', 'domain_suffix'} & set(rule):
            _fail('UNREPRESENTABLE_MATCH')
        predicate_index = 0
        for key, values in rule.items():
            if key not in ('domain', 'domain_suffix'):
                continue
            if type(values) is not list or not values:
                _fail('UNSUPPORTED_SOURCE_STRUCTURE')
            kind = 'exact_domain' if key == 'domain' else 'suffix_including_apex'
            for item_index, value in enumerate(values):
                guard()
                if len(entries) >= MAX_RECORDS:
                    _fail('TOO_MANY_PREDICATES')
                if not predicates._canonical_domain(value):
                    _fail('NONCANONICAL_DOMAIN')
                entries.append((index, predicate_index, (index, key, item_index), None,
                                value, kind, value, label))
                predicate_index += 1
    return len(root), entries


def _render(records, profile, guard):
    values = []
    for row in records:
        guard()
        suffix = row.kind == 'suffix_including_apex'
        label = row.target_action[1]
        if profile == MIHOMO:
            values.append(('DOMAIN-SUFFIX,' if suffix else 'DOMAIN,') + row.domain + ',' + label)
        else:
            values.append({'domain_suffix' if suffix else 'domain': [row.domain],
                           'action': 'route', 'outbound': label})
    if profile == MIHOMO:
        output = ('rules:\n' + ''.join("  - '" + value + "'\n" for value in values)).encode('ascii')
    else:
        output = (json.dumps(values, ensure_ascii=True, separators=(',', ':')) + '\n').encode('ascii')
    guard()
    if len(output) > MAX_BYTES:
        _fail('OUTPUT_BUDGET_EXCEEDED')
    return output


def convert_policy_rules(source_bytes, source_profile, target_profile,
                         ordered_rule_refs, source_binding, outbound_bindings, *,
                         source_no_match=DEFER, target_no_match=DEFER,
                         max_seconds=5, cancelled=lambda: False):
    """Return all converted private bytes, or raise a fixed diagnostic atomically.

    No-match arguments declare a fragment boundary; they do not describe or verify
    the actual enclosing engine fallback. Both must explicitly retain deferral.
    Finality declarations cover TCP and UDP including group/member resolution;
    this API cannot verify that the caller's classification is true.
    """
    if type(max_seconds) not in (int, float) or not 0 < max_seconds <= 60:
        _fail('INVALID_DEADLINE')
    deadline = time.monotonic() + max_seconds
    if (type(source_profile) is not str or source_profile not in PROFILES
            or type(target_profile) is not str or target_profile not in PROFILES
            or source_profile == target_profile):
        _fail('UNSUPPORTED_PROFILE')
    if (type(source_no_match) is not str or source_no_match != DEFER
            or type(target_no_match) is not str or target_no_match != DEFER):
        _fail('INCOMPATIBLE_NO_MATCH_SEMANTICS')
    if type(source_bytes) is not bytes or not 0 < len(source_bytes) <= MAX_BYTES:
        _fail('INVALID_OR_OVERSIZED_SOURCE')
    # Snapshot every caller-owned declaration before invoking any callback.
    try:
        refs = source._references(ordered_rule_refs, MAX_RECORDS,
                                  'INVALID_RULE_REFERENCES', 'DUPLICATE_RULE_REFERENCE')
        declared = source._source_binding(source_binding)
    except source.SourceImportError as exc:
        _fail(str(exc))
    bindings = _bindings(outbound_bindings)
    mapping = {dict(row)['source_label']: dict(row)['target_label'] for row in bindings}

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
    digest = hashlib.sha256(source_bytes).hexdigest()
    if digest != dict(declared)['expected_sha256']:
        _fail('SOURCE_DIGEST_MISMATCH')
    try:
        text = source_bytes.decode('utf-8')
    except UnicodeError:
        _fail('INVALID_SOURCE_ENCODING')
    guard()
    count, entries = (_mihomo(source_bytes, guard) if source_profile == MIHOMO
                      else _sing_box(text, guard))
    if count != len(refs):
        _fail('RULE_REFERENCE_COUNT_MISMATCH')
    records, used = [], set()
    for index, pred_index, path, line, original, kind, domain, label in entries:
        guard()
        if not predicates._canonical_domain(domain):
            _fail('NONCANONICAL_DOMAIN')
        if label not in mapping:
            _fail('INCOMPLETE_OUTBOUND_BINDINGS')
        used.add(label)
        records.append(PolicyOccurrence(refs[index], index, pred_index, path, line,
                        original, kind, domain, ('route_to_named_outbound', label),
                        ('route_to_named_outbound', mapping[label])))
    if used != set(mapping):
        _fail('UNUSED_OUTBOUND_BINDINGS')
    output = _render(records, target_profile, guard)
    output_digest = hashlib.sha256(output).hexdigest()
    output_map = tuple((i, row.source_rule_index, row.predicate_index)
                       for i, row in enumerate(records))
    result = PrivatePolicyConversion(source_bytes, source_profile, target_profile,
                digest, declared, bindings, tuple(records), output, output_digest, refs, output_map)
    guard()
    return result
