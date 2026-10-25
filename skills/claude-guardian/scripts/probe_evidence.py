"""Bounded offline projection of HTTPS/STUN/Mihomo DNS output, never an authority source.

All input, including target aliases, timestamps and success, is a declaration.
No transport is imported or invoked. This projection cannot construct workflow
Evidence, authorize a probe, establish host provenance or restore permissions.
"""
from datetime import datetime, timezone
import ipaddress

from guardian import GuardianError

SCHEMA = 'guardian-probe-evidence/0.1'
MAX_SAMPLES = 64
# Closed member vocabulary (ENV-T121): unknown members are rejected, not ignored. These are the members
# the shipped producers emit; provenance/approval/verified-style members are not in any set.
BUNDLE_KEYS = frozenset({'schema_version', 'target_ref', 'samples'})
ITEM_KEYS = frozenset({'result', 'expected_path_kind', 'captured_at', 'context'})
CONTEXT_KEYS = frozenset({'target_ref', 'path_kind'})
# Exactly the members network_probes.py (HTTPS) and stun_probe.py (STUN) emit. path_association and
# browser_path are producer-written constants; their values are never trusted by the projection.
SAMPLE_RESULT_KEYS = {
    'probe_https': frozenset({'endpoint', 'endpoint_id', 'target_ref', 'sample_type', 'path_kind',
                              'expected_address_family', 'observed_address_family', 'observed_ip', 'status',
                              'http_status', 'error', 'path_association', 'browser_path', 'started_at',
                              'finished_at', 'request_count', 'limits', 'retry_after', 'interpretation',
                              'probe_context', 'final_egress_declaration', 'resource_declaration',
                              'coverage', 'probe_binding_status'}),
    'independent_stun': frozenset({'status', 'error', 'sends', 'received', 'rejected', 'polls', 'observed_ip',
                                   'observed_port', 'observed_address_family', 'path_kind', 'path_association',
                                   'browser_path', 'target_path', 'endpoint', 'target_ref', 'sample_type',
                                   'authenticated', 'cleanup'}),
}
DNS_RESULT_KEYS = frozenset({'schema_version', 'operation', 'contact_phase', 'gate_state', 'changes',
                             'execution_status', 'error_code', 'facts', 'requests_attempted', 'coverage',
                             'not_tested'})
PATHS = {'direct_socket_os_route_tun_unknown': '系统路由（TUN 未知）',
         'explicit_proxy': '显式代理（链路关联未知）'}
ENDPOINTS = {'ipify_v4': ('https://api.ipify.org?format=json', 4),
             'ipify_v6': ('https://api6.ipify.org?format=json', 6),
             'ipify_dual': ('https://api64.ipify.org?format=json', None)}
STATUS_LABELS = {'observed': '已记录成功声明', 'response_observed': '已记录响应声明',
                 'context_unknown': '目标或路径上下文未知', 'unknown': '结果未知',
                 'cancelled': '已取消', 'stale': '证据已过期',
                 'target_mismatch': '目标声明不匹配', 'path_mismatch': '路径声明不匹配',
                 'time_invalid': '时间缺失或无效', 'authorization_needed': '授权或权限不足',
                 'timeout': '超时', 'error': '探测未成功'}


def _time(value):
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, OverflowError):
        return None


def _ref(value):
    return type(value) is str and 0 < len(value) <= 128 and value.strip() and not any(ord(c) < 32 for c in value)


MIHOMO_SCHEMA = 'guardian-mihomo-dns-probe/0.1'
MIHOMO_PATH = 'mihomo_dns_query'
MIHOMO_ERRORS = frozenset({'CANCELLED', 'TIMEOUT', 'BUDGET_EXCEEDED',
    'INPUT_OR_RESPONSE_INVALID', 'CONTROLLER_NOT_BOUND', 'AUTHORIZATION_MISSING',
    'AUTHENTICATION_HANDOFF_REQUIRED', 'CONTROLLER_RESPONSE_REJECTED',
    'PERMISSION_DENIED', 'PC0_TARGET_FORBIDDEN', 'RESPONSE_CONTEXT_MISMATCH'})


def _mihomo_sample(item, target, index, now):
    """Mihomo exports no binding: context is a separate, unverified declaration."""
    raw = item['result']
    facts, error = raw.get('facts'), raw.get('error_code')
    execution = raw.get('execution_status')
    if (raw.get('operation') != 'probe' or raw.get('coverage') != 'mihomo_dns_query_sample_only'
            or raw.get('gate_state') != 'closed' or type(facts) is not list
            or type(raw.get('requests_attempted')) is not int or raw['requests_attempted'] not in (0, 1)
            or execution not in ('completed', 'blocked')
            or (error is not None and (type(error) is not str or error not in MIHOMO_ERRORS))
            or (execution == 'completed' and (error is not None or len(facts) != 1 or raw['requests_attempted'] != 1))
            or (execution == 'blocked' and (facts or error is None))):
        raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
    summary = None
    if facts:
        fact = facts[0]
        if (type(fact) is not dict or fact.get('source_ref') != 'mihomo-dns-query'
                or fact.get('layer') != 'runtime_observed' or type(fact.get('value')) is not dict):
            raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
        value = fact['value']
        classes = value.get('address_class_counts')
        if (type(classes) is not dict or value.get('query_type') not in ('A', 'AAAA')
                or value.get('question_matches') is not True
                or value.get('address_family') != ('IPv4' if value['query_type'] == 'A' else 'IPv6')
                or type(value.get('rcode')) is not int or not 0 <= value['rcode'] <= 4095
                or type(value.get('truncated')) is not bool
                or any(type(value.get(k)) is not int or not 0 <= value[k] <= 256
                       for k in ('answer_count', 'address_count', 'cname_count'))
                or any(type(classes.get(k)) is not int or not 0 <= classes[k] <= 256
                       for k in ('globally_routable', 'non_global'))
                or value['address_count'] + value['cname_count'] != value['answer_count']
                or classes['globally_routable'] + classes['non_global'] != value['address_count']):
            raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
        summary = {key: value[key] for key in ('query_type', 'rcode', 'truncated', 'answer_count', 'address_count', 'cname_count')}
        summary.update(globally_routable=classes['globally_routable'], non_global=classes['non_global'])
        at = _time(fact.get('observed_at'))
    else:
        at = _time(item.get('captured_at'))  # optional receipt time for failures only
    context = item.get('context', {})
    if type(context) is not dict:
        raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
    target_ref, path = context.get('target_ref'), context.get('path_kind')
    target_present = bool(_ref(target_ref))
    target_matches = target_present and target_ref == target
    path_matches = path == MIHOMO_PATH and item.get('expected_path_kind') == MIHOMO_PATH
    time_valid = at is not None and at <= now
    freshness = 'invalid' if not time_valid else 'stale' if (now-at).total_seconds() > 86400 else 'current'
    if error == 'CANCELLED':
        status = 'cancelled'
    elif error in ('CONTROLLER_NOT_BOUND', 'RESPONSE_CONTEXT_MISMATCH') or (target_present and not target_matches):
        status = 'target_mismatch'
    elif (path is not None and path != MIHOMO_PATH) or (item.get('expected_path_kind') is not None and item['expected_path_kind'] != MIHOMO_PATH):
        status = 'path_mismatch'
    elif error in ('AUTHORIZATION_MISSING', 'AUTHENTICATION_HANDOFF_REQUIRED', 'PERMISSION_DENIED'):
        status = 'authorization_needed'
    elif error == 'TIMEOUT':
        status = 'timeout'
    elif error is not None:
        status = 'error'
    elif not target_present or not path_matches:
        status = 'context_unknown'
    elif not time_valid:
        status = 'time_invalid'
    elif freshness == 'stale':
        status = 'stale'
    else:
        status = 'response_observed'  # negative/truncated response is not success
    return dict(index=index, keys=('dns',), status=status,
        target='matching_declaration' if target_matches else 'mismatch' if target_present else 'unknown',
        path=MIHOMO_PATH if path == MIHOMO_PATH else 'unknown', path_matches=path_matches,
        family=(4 if summary['query_type'] == 'A' else 6) if summary else None,
        observed_at=at.isoformat() if at else None, freshness=freshness,
        endpoint='mihomo_dns_query', sample_type='mihomo_dns', provenance='unverified_import', dns=summary)


OS_DNS_SCHEMAS = {
    'guardian-os-dns-probe/0.1': ('macos_system_resolution_sample_only',
        'os-system-resolution', 'macos_getaddrinfo', 'macOS 系统解析 getaddrinfo'),
    'guardian-windows-dns-probe/0.1': ('windows_system_dns_sample_only',
        'windows-system-dns', 'windows_Resolve-DnsName_DnsOnly', 'Windows 系统解析 Resolve-DnsName -DnsOnly'),
}
OS_DNS_ERRORS = frozenset({'INPUT_INVALID', 'UNSUPPORTED_PLATFORM', 'PC0_TARGET_FORBIDDEN',
    'TARGET_NOT_BOUND', 'RUNTIME_NOT_TRUSTED', 'AUTHORIZATION_MISSING', 'CANCELLED', 'TIMEOUT',
    'OUTPUT_INVALID', 'OUTPUT_LIMIT', 'RESOLUTION_FAILED', 'PROCESS_FAILED', 'CLEANUP_FAILED',
    'PERMISSION_DENIED'})


def _os_dns_sample(item, target, index, now):
    """Final system-resolution counts, distinct from DNS packets/Mihomo replies."""
    raw = item['result']
    coverage, source, resolver, label = OS_DNS_SCHEMAS[raw['schema_version']]
    errors = OS_DNS_ERRORS | {'DEPENDENCY_MISSING'} if raw['schema_version'] == 'guardian-windows-dns-probe/0.1' else OS_DNS_ERRORS
    facts, error, execution = raw.get('facts'), raw.get('error_code'), raw.get('execution_status')
    if (raw.get('operation') != 'probe' or raw.get('coverage') != coverage
            or raw.get('gate_state') != 'closed' or type(facts) is not list
            or type(raw.get('requests_attempted')) is not int or raw['requests_attempted'] not in (0, 1)
            or execution not in ('completed', 'blocked')
            or (error is not None and (type(error) is not str or error not in errors))
            or (execution == 'completed' and (error is not None or len(facts) != 1 or raw['requests_attempted'] != 1))
            or (execution == 'blocked' and (facts or error is None))):
        raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
    summary = None
    if facts:
        fact = facts[0]
        if (type(fact) is not dict or fact.get('source_ref') != source
                or fact.get('layer') != 'runtime_observed' or type(fact.get('value')) is not dict):
            raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
        value = fact['value']
        classes = value.get('address_class_counts')
        if (value.get('resolver_api') != resolver or value.get('query_type') not in ('A', 'AAAA')
                or value.get('address_family') != ('IPv4' if value['query_type'] == 'A' else 'IPv6')
                or type(value.get('address_count')) is not int or not 0 <= value['address_count'] <= 128
                or type(classes) is not dict
                or any(type(classes.get(k)) is not int or not 0 <= classes[k] <= 128
                       for k in ('globally_routable', 'non_global'))
                or classes['globally_routable'] + classes['non_global'] != value['address_count']
                or value.get('dns_rcode') is not None or value.get('dns_packet_observed') is not False):
            raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
        summary = dict(query_type=value['query_type'], address_count=value['address_count'],
                       globally_routable=classes['globally_routable'], non_global=classes['non_global'])
        at = _time(fact.get('observed_at'))
    else:
        at = _time(item.get('captured_at'))
    context = item.get('context', {})
    if type(context) is not dict:
        raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
    target_ref, path = context.get('target_ref'), context.get('path_kind')
    target_present = bool(_ref(target_ref))
    target_matches = target_present and target_ref == target
    path_matches = path == resolver and item.get('expected_path_kind') == resolver
    time_valid = at is not None and at <= now
    freshness = 'invalid' if not time_valid else 'stale' if (now-at).total_seconds() > 86400 else 'current'
    if error == 'CANCELLED':
        status = 'cancelled'
    elif error == 'TARGET_NOT_BOUND' or (target_present and not target_matches):
        status = 'target_mismatch'
    elif (path is not None and path != resolver) or (item.get('expected_path_kind') is not None and item['expected_path_kind'] != resolver):
        status = 'path_mismatch'
    elif error in ('AUTHORIZATION_MISSING', 'PERMISSION_DENIED'):
        status = 'authorization_needed'
    elif error == 'TIMEOUT':
        status = 'timeout'
    elif error is not None:
        status = 'error'
    elif not target_present or not path_matches:
        status = 'context_unknown'
    elif not time_valid:
        status = 'time_invalid'
    elif freshness == 'stale':
        status = 'stale'
    else:
        status = 'response_observed'
    return dict(index=index, keys=('dns',), status=status,
        target='matching_declaration' if target_matches else 'mismatch' if target_present else 'unknown',
        path=resolver if path == resolver else 'unknown', path_matches=path_matches,
        family=(4 if summary['query_type'] == 'A' else 6) if summary else None,
        observed_at=at.isoformat() if at else None, freshness=freshness,
        endpoint=resolver, sample_type='os_dns', provenance='unverified_import', dns=summary,
        source_label=label, error_code=error)


def project_samples(bundle, now):
    """Return only fixed labels/enums/counts/parsed dates; reject malformed envelopes.

    Envelope: schema_version, target_ref, samples[{result, expected_path_kind,
    captured_at?}]. HTTPS uses its own started_at/finished_at, not captured_at.
    STUN lacks wall-clock timestamps: captured_at is an explicit host-recorded
    receipt-time declaration, never populated with the rendering time. JSON
    provenance/approval/verified fields are ignored, never upgraded to authority.
    """
    if (type(bundle) is not dict or bundle.get('schema_version') != SCHEMA
            or not _ref(bundle.get('target_ref')) or type(bundle.get('samples')) is not list
            or len(bundle['samples']) > MAX_SAMPLES or set(bundle) - BUNDLE_KEYS):
        raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
    output = []
    for index, item in enumerate(bundle['samples'], 1):
        if (type(item) is not dict or type(item.get('result')) is not dict or set(item) - ITEM_KEYS
                or (type(item.get('context')) is dict and set(item['context']) - CONTEXT_KEYS)):
            raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
        raw = item['result']
        known = (DNS_RESULT_KEYS if raw.get('schema_version') in OS_DNS_SCHEMAS or raw.get('schema_version') == MIHOMO_SCHEMA
                 else SAMPLE_RESULT_KEYS.get(raw.get('sample_type')))
        if known is not None and set(raw) - known:
            raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
        if type(raw.get('schema_version')) is str and raw['schema_version'] in OS_DNS_SCHEMAS:
            output.append(_os_dns_sample(item, bundle['target_ref'], index, now))
            continue
        if raw.get('schema_version') == MIHOMO_SCHEMA:
            output.append(_mihomo_sample(item, bundle['target_ref'], index, now))
            continue
        kind = raw.get('sample_type')
        if kind not in ('probe_https', 'independent_stun'):
            raise GuardianError('DASHBOARD_PROBE_REPORT_UNSUPPORTED')
        path = raw.get('path_kind')
        expected_path = item.get('expected_path_kind')
        family = raw.get('observed_address_family')
        family = family if type(family) is int and family in (4, 6) else None
        endpoint = raw.get('endpoint_id') if kind == 'probe_https' else raw.get('endpoint')
        if kind == 'probe_https':
            if type(endpoint) is not str or endpoint not in ENDPOINTS or raw.get('endpoint') != ENDPOINTS[endpoint][0]:
                raise GuardianError('DASHBOARD_PROBE_ENDPOINT_INVALID')
            expected_family = ENDPOINTS[endpoint][1]
            if raw.get('expected_address_family') != expected_family or isinstance(raw.get('expected_address_family'), bool):
                raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
            at, start = _time(raw.get('finished_at')), _time(raw.get('started_at'))
            time_valid = at is not None and start is not None and start <= at <= now
            keys = ('ipv4',) if expected_family == 4 else ('ipv6',) if expected_family == 6 else (
                ('ipv4',) if family == 4 else ('ipv6',) if family == 6 else ('ipv4', 'ipv6'))
        else:
            if endpoint not in ('stun:stun.cloudflare.com:3478', 'owned-loopback-fixture'):
                raise GuardianError('DASHBOARD_PROBE_ENDPOINT_INVALID')
            expected_family = None
            at = _time(item.get('captured_at'))
            time_valid = at is not None and at <= now
            keys = ('stun',)  # Never certify UDP generally, IPv6 layers or WebRTC.
        target_matches = _ref(raw.get('target_ref')) and raw['target_ref'] == bundle['target_ref']
        path_matches = (type(path) is str and path in PATHS and type(expected_path) is str
                        and path == expected_path and (kind == 'probe_https' or path == 'direct_socket_os_route_tun_unknown'))
        error = raw.get('error')
        status = 'unknown'
        if error == 'cancelled':
            status = 'cancelled'
        elif error == 'target_changed' or not target_matches:
            status = 'target_mismatch'
        elif not path_matches:
            status = 'path_mismatch'
        elif not time_valid:
            status = 'time_invalid'
        elif (now - at).total_seconds() > 86400:
            status = 'stale'
        elif error in ('approval_required', 'permission_denied'):
            status = 'authorization_needed'
        elif error == 'timeout':
            status = 'timeout'
        elif error is not None:
            status = 'error'
        elif raw.get('status') == 'observed':
            try:
                value = raw.get('observed_ip')
                address = ipaddress.ip_address(value) if type(value) is str and '%' not in value else None
                valid = address is not None and address.version == family
                if kind == 'probe_https':
                    valid = valid and address.is_global and raw.get('http_status') == 200 and type(raw.get('http_status')) is int
                    valid = valid and (expected_family is None or family == expected_family)
                else:
                    valid = valid and raw.get('cleanup') == 'closed' and type(raw.get('observed_port')) is int and 1 <= raw['observed_port'] <= 65535
                if valid:
                    status = 'observed'
            except ValueError:
                pass
        # Keep independent facets even when e.g. cancellation takes precedence.
        output.append(dict(index=index, keys=keys, status=status,
            target='matching_declaration' if target_matches else 'mismatch',
            path=path if type(path) is str and path in PATHS else 'unknown',
            path_matches=bool(path_matches), family=family,
            observed_at=at.isoformat() if at else None,
            freshness='invalid' if not time_valid else 'stale' if (now-at).total_seconds() > 86400 else 'current',
            endpoint=endpoint, sample_type=kind, provenance='unverified_import'))
    return output


def sample_text(sample):
    """Render only the adapter's finite projection, never raw result fields."""
    if sample['sample_type'] == 'os_dns':
        value = sample['dns']
        response = ('查询 %s / IPv%d；地址 %d；全局单播地址类 %d / 非全局地址类 %d' % (
            value['query_type'], sample['family'], value['address_count'],
            value['globally_routable'], value['non_global'])) if value else '无解析事实'
        return '样本 %d：%s；%s；%s；%s；%s；UTC %s；时效：%s；原因：%s。系统解析样本，没有 DNS 报文/RCODE 证据；缓存来源、服务器和上游路径还要另查泄露' % (
            sample['index'], STATUS_LABELS[sample['status']], sample['source_label'], response,
            '解析 API 路径声明一致（未核验）' if sample['path_matches'] else '解析 API 路径声明未知或不匹配',
            {'matching_declaration': '目标声明一致（未核验）', 'mismatch': '目标声明不匹配', 'unknown': '目标上下文未知'}[sample['target']],
            sample['observed_at'] or '未知', {'current': '当前声明', 'stale': '过期', 'invalid': '无效'}[sample['freshness']],
            sample['error_code'] or '无错误声明')
    if sample['sample_type'] == 'mihomo_dns':
        value = sample['dns']
        response = ('查询 %s / IPv%d；rcode %d；截断 %s；答案 %d / 地址 %d / CNAME %d；全局单播地址类 %d / 非全局地址类 %d' % (
            value['query_type'], sample['family'], value['rcode'], '是' if value['truncated'] else '否',
            value['answer_count'], value['address_count'], value['cname_count'],
            value['globally_routable'], value['non_global'])) if value else '无响应事实'
        return '样本 %d：%s；Mihomo DNS 查询；%s；%s；%s；UTC %s；时效：%s。仅响应摘要；缓存来源、Fake-IP 和上游路径还要另查泄露' % (
            sample['index'], STATUS_LABELS[sample['status']], response,
            '控制器查询路径声明一致（未核验）' if sample['path_matches'] else '控制器查询路径声明未知或不匹配',
            {'matching_declaration': '目标声明一致（未核验）', 'mismatch': '目标声明不匹配', 'unknown': '目标上下文未知'}[sample['target']],
            sample['observed_at'] or '未知', {'current': '当前声明', 'stale': '过期', 'invalid': '无效'}[sample['freshness']])
    return '样本 %d：%s；%s；%s；%s；%s；UTC %s；时效：%s' % (
        sample['index'], STATUS_LABELS[sample['status']],
        'HTTPS ' + sample['endpoint'] if sample['sample_type'] == 'probe_https' else (
            'STUN 本地测试夹具' if sample['endpoint'] == 'owned-loopback-fixture' else '独立 STUN'),
        'IPv%d' % sample['family'] if sample['family'] else '地址族未知',
        PATHS.get(sample['path'], '路径未知') + ('' if sample['path_matches'] else '（声明不匹配）'),
        '目标声明一致（未核验）' if sample['target'] == 'matching_declaration' else '目标声明不匹配',
        sample['observed_at'] or '未知', {'current': '当前声明', 'stale': '过期', 'invalid': '无效'}[sample['freshness']])
