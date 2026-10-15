"""Bounded offline projection of HTTPS/STUN output, never an authority source.

All input, including target aliases, timestamps and success, is a declaration.
No transport is imported or invoked. This projection cannot construct workflow
Evidence, authorize a probe, establish host provenance or restore permissions.
"""
from datetime import datetime, timezone
import ipaddress

from guardian import GuardianError

SCHEMA = 'guardian-probe-evidence/0.1'
MAX_SAMPLES = 64
PATHS = {'direct_socket_os_route_tun_unknown': '系统路由（TUN 未知）',
         'explicit_proxy': '显式代理（链路关联未知）'}
ENDPOINTS = {'ipify_v4': ('https://api.ipify.org?format=json', 4),
             'ipify_v6': ('https://api6.ipify.org?format=json', 6),
             'ipify_dual': ('https://api64.ipify.org?format=json', None)}
STATUS_LABELS = {'observed': '已记录成功声明', 'unknown': '结果未知',
                 'cancelled': '已取消', 'stale': '证据已过期',
                 'target_mismatch': '目标声明不匹配', 'path_mismatch': '路径声明不匹配',
                 'time_invalid': '时间缺失或无效', 'authorization_needed': '授权或权限不足',
                 'timeout': '超时（不证明阻断）', 'error': '探测未成功'}


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
            or len(bundle['samples']) > MAX_SAMPLES):
        raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
    output = []
    for index, item in enumerate(bundle['samples'], 1):
        if type(item) is not dict or type(item.get('result')) is not dict:
            raise GuardianError('DASHBOARD_PROBE_REPORT_INVALID')
        raw = item['result']
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
    return '样本 %d：%s；%s；%s；%s；%s；UTC %s；时效：%s' % (
        sample['index'], STATUS_LABELS[sample['status']],
        'HTTPS ' + sample['endpoint'] if sample['sample_type'] == 'probe_https' else (
            'STUN 本地测试夹具' if sample['endpoint'] == 'owned-loopback-fixture' else '独立 STUN'),
        'IPv%d' % sample['family'] if sample['family'] else '地址族未知',
        PATHS.get(sample['path'], '路径未知') + ('' if sample['path_matches'] else '（声明不匹配）'),
        '目标声明一致（未核验）' if sample['target'] == 'matching_declaration' else '目标声明不匹配',
        sample['observed_at'] or '未知', {'current': '当前声明', 'stale': '过期', 'invalid': '无效'}[sample['freshness']])
