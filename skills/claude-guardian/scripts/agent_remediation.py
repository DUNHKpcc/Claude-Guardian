#!/usr/bin/env python3
"""Offline action selection for Agent-led remediation; never an execution grant.

Only fixed catalog templates leave this module. Imported findings are untrusted
observations, not proof of native capability, consent, or successful repair.
"""
import argparse
import copy
import json
import re
import sys

import guardian

SCHEMA = 'guardian-remediation-selection/0.1'
INPUT_SCHEMA = 'guardian-remediation-findings/0.1'


def action(kind, module, summary, steps, evidence, verify, command=None):
    return dict(kind=kind, module_id=module, summary=summary, steps=steps,
                required_evidence=evidence, verification=verify,
                command_template=command, target_mutation_supported=False)


CATALOG = {
    'stop': action('stop', 'ENV-01', '用户已取消；停止相关操作',
                   ['等待用户重新提出或明确恢复任务，不自动重试'], [], ['重新开始时重新采集和授权']),
    'bind-target': action('clarify', 'ENV-01', '先确认目标设备、当前用户和执行位置',
                         ['核对 Agent 所在主机与用户指定设备', '只补缺失信息；云端结果不得代替本机'],
                         ['当前设备/用户/命名空间'], ['在正确目标重新检测']),
    'reaudit': action('read_only_script', 'ENV-01', '重新获取当前限定元数据，不能沿用失效快照',
                     ['确认本次只读范围', '调用内置会话；保留采集失败原因'],
                     ['可信本机宿主', '当前只读授权'], ['比较同一目标的新旧证据，不因采集成功判网络通过'],
                     ['python', 'scripts/diagnostic_session.py', '--target-ref', '<target-alias>']),
    'collect-proxy': action('read_only_script', 'ENV-02', '补充选定代理实例及配置证据',
                           ['先查看实际支持范围', '仅对获准精确文件使用 static-audit；版本不支持则Agent通过已核实的宿主只读接口读取必要字段'],
                           ['产品/版本', '活动配置/端口归属', '精确文件读取授权'],
                           ['分别记录文件声明、OS开关、运行时；不互相补值'],
                           ['python', 'scripts/inventory_cli.py', 'capabilities']),
    'proxy-port': action('agent_investigation', 'ENV-02', '系统代理端口与选定实例不一致',
                        ['核实当前活动网络服务、代理类型、监听实例及端口',
                         '记录原开关/主机/端口/绕过列表；向用户展示仅该服务该代理类型的差异和恢复值',
                         '取得具体修改授权后，Agent使用实际环境支持的设置接口或经过审阅的限定脚本，仅修改已核实的端口',
                         '保留PAC、绕过列表、其他服务、TUN及Codex控制路径；异常时恢复本次原值'],
                        ['新鲜P06/P09/P11/P12', '监听者归属', '活动网络服务', '控制通道保护'],
                        ['重读同一服务代理端口', '另获授权后检验同一程序的中性HTTPS路径']),
    'plan-rules': action('candidate_only', 'ENV-06', '生成已拥有扩展中的有限规则候选',
                        ['仅在已确认的问题确为规则选择/优先级时使用',
                         '已有DOMAIN/DOMAIN-SUFFIX policy更换用merge-policy；空prepend插入用rules-prepend',
                         '展示精确diff、影响、保留项、备份恢复范围；execute仍须原生适配及本次授权，当前未开放'],
                        ['规则根因', '精确文件/版本/活动扩展归属', '请求与binding', '合并优先级'],
                        ['候选解析→合并解释→内核校验→GUI读回→实际路径→订阅更新复验'],
                        ['python', 'scripts/repair_cli.py', 'preflight', '--request', '<private-request.json>',
                         '--target-path', '<owned-extension>', '--target-ref', '<target-alias>']),
    'probe-plan': action('host_library_only', 'ENV-03', '准备指定程序和路径的中性探测',
                         ['选定中性端点、地址族、程序、预算与披露范围',
                          '只有可信宿主满足network_probes.py契约并取得本次授权才能探测；无通用网络CLI',
                          'PC0不接触Claude；失败不自动换节点、重试或清理'],
                         ['目标/运行时绑定', '端点核验', '精确网络授权'],
                         ['区分连接、DNS、TLS、HTTP及路径证据；一次HTTPS不证明DNS/UDP']),
    'dns': action('agent_investigation', 'ENV-04', '定位具体DNS责任层后再改最小设置',
                  ['分别核对系统DNS、代理核心DNS、浏览器DoH与内网分流',
                   '以os_dns_probe.py/windows_dns_probe.py和mihomo_dns_probe.py宿主库补充获准样本；不可从JSON恢复授权',
                   '确认责任层后展示该层精确键、原值、目标值及恢复值，由Agent按该环境已核实的接口修改；没有工具或许可才交接用户'],
                  ['系统/核心/浏览器分层证据', '内网与节点引导解析保护'],
                  ['同一名称/类型/程序复测；解析成功不等于无泄漏']),
    'ipv6': action('agent_investigation', 'ENV-04', '区分IPv6旁路与单纯不可用',
                   ['确认同一程序的IPv4/IPv6路径', '确有旁路才提出应用/TUN范围的修复；不整机禁用IPv6',
                    '保留节点外层IPv6；具体差异与恢复值确认后在对应客户端设置中调整'],
                   ['同程序双栈对照', '外层节点依赖'], ['复测同一地址族和路径；超时不能证明阻断']),
    'udp': action('agent_investigation', 'ENV-04', '分开处理应用UDP、STUN和隧道外层UDP',
                  ['核对规则命中与节点能力', '仅调整已证实错误的应用规则；保留Hysteria2/TUIC外层UDP',
                   'stun_probe.py仅为获准宿主库；无结果保留未知'],
                  ['应用协议/路径', '节点能力', '隧道外层依赖'], ['同范围UDP/STUN复测，不把HTTPS成功当UDP成功']),
    'browser': action('agent_investigation', 'ENV-05', '核实实际浏览器/Profile/origin的有效策略',
                      ['核对版本、受管状态、策略接受/冲突与作用域',
                       '对Chrome/Edge仅提出受支持的非代理UDP限制及媒体影响；确认后由Agent通过已核实的接口改该项',
                       'Safari/Firefox无内置写入适配；继续调查该环境支持的设置方式，不套用Chrome策略'],
                      ['实际浏览器/Profile/origin', '有效策略', '公网候选路径证据'],
                      ['同Profile/origin复测候选及必要媒体；无候选不是无泄漏']),
    'launcher': action('agent_investigation', 'ENV-07', '查明具体程序与子进程采用的代理方式',
                       ['核对启动入口、GUI/终端差异和该版本支持的配置',
                        '只提出该启动入口的修改，展示环境变量作用域和恢复值；不输出秘密',
                        'PC0不启动Claude；真实客户端验证需独立接触交接'],
                       ['启动方式/版本', '子进程覆盖', '认证类别'], ['逐程序复测；变量存在不证明采用']),
    'clock': action('agent_investigation', 'ENV-08', '按用户真实目标分开处理时钟、时区和语言',
                    ['先确认是否存在时钟误差或用户明确设置目标',
                     '记录原值并展示单项影响；用户确认后由Agent在实际系统支持的接口修改',
                     '不按出口地区改时区，不把NTP路由当时区设置'],
                    ['用户目标', '当前设置/管理权限'], ['重读被修改项；语言生效/注销另行确认']),
    'cleanup': action('agent_investigation', 'ENV-09', '先盘点精确清理对象与保留项',
                      ['列出选中对象、影响及可读备份/恢复方法',
                       '保护项目、CLI、凭据、历史、skills/hooks/plugins与控制通道',
                       '未实现内置清理执行器；Agent调查精确对象的安全处理方式；不运行上游整目录清理；删除需独立具体确认'],
                      ['清理目的', '精确对象', '保留清单', '恢复验证'], ['核对选中对象与保留内容；不宣称解除停用']),
    'fault': action('agent_investigation', 'ENV-10', '故障阻断需要独立平台实现与真实演练',
                    ['明确保护程序、地址族、故障与控制通道',
                     '准备独立离线恢复；当前无内置系统故障注入/防火墙修复执行器'],
                    ['平台出站能力', '独立恢复', '具体演练授权'], ['正常/停止/重启/更新逐场景验收，当前记not_run']),
    'dependency': action('agent_investigation', 'ENV-01', '补足明确缺失的运行时或解析器',
                         ['核对缺失的是Python运行时、PyYAML还是系统工具',
                          '展示官方来源、版本和安装范围，取得需要的安装许可后按官方流程安装',
                          '不静默安装，不因解析失败改配置'], ['依赖名称/来源/目标环境'], ['重跑原失败命令']),
    'permission': action('clarify', 'ENV-01', '缺少对应动作授权或访问权限',
                         ['说明确切目标、数据与用途，向用户请求该动作授权', '尊重拒绝，不换路径绕过系统拒绝'],
                         ['确切范围许可'], ['许可后重新执行原限定检查']),
    'unsupported': action('agent_investigation', 'ENV-01', '当前适配器不支持该操作或版本',
                          ['记录具体产品/版本/操作缺口', 'Agent继续检查实际环境支持的接口，提出独立最小修复；不改版本声明、不替换门禁回调'],
                          ['匹配操作的原生适配与验收'], ['未支持项保持blocked，不阻断无关只读工作']),
    'input': action('clarify', 'ENV-01', '输入或采集失败，尚不能诊断为配置故障',
                    ['核对私有本地输入格式、限定路径和原始错误类别', '修正输入后有界重试；不输出秘密或扩大扫描'],
                    ['有效输入', '失败原因'], ['重跑原检查；失败保留unknown']),
    'incident': action('clarify', 'M12', '先区分连通、认证、额度、支付与账号事故',
                       ['只收集必要脱敏错误类别与当前任务', '账号停用走官方处理分支；不自动清理、换号或改网络'],
                       ['事故类别', '当前状态'], ['故障处理完成不等于账号恢复']),
    'runtime': action('agent_investigation', 'ENV-01', '运行时路径不满足严格会话要求',
                      ['查看固定runtime_path_diagnostic字段以区分executable/cwd/prefix/base_prefix',
                       '核对已有可信运行时的真实目录与权限；需要安装时另取许可',
                       '保留部分元数据；不放松链接检查或伪造上下文句柄'],
                      ['受影响路径字段及原因', '可信本机运行时'], ['在合规运行时重跑诊断；DNS授权仍需单独满足']),
    'keep': action('no_change', 'ENV-04', '现有证据不足以要求修改',
                   ['保留当前配置并解释证据边界', '仅补与用户目标有关的缺口'], [], ['没有新问题不制造修复']),
}

CATALOG['plan-prepend'] = copy.deepcopy(CATALOG['plan-rules'])
CATALOG['plan-prepend']['command_template'] += [
    '--candidate-kind', 'rules-prepend', '--app-info', '<authorized-Info.plist>',
    '--profile-index', '<authorized-profiles.yaml>', '--extension-uid', '<selected-rules-uid>',
    '--base-path', '<authorized-base-profile>']

GROUPS = {
    'stop': 'USER_CANCELLED CANCELLED DECLINED CONSENT_TIMEOUT',
    'bind-target': 'TARGET_NOT_BOUND TARGET_USER_CONTEXT_MISMATCH ROUTE_OR_TARGET_NEEDS_CLARIFICATION CONTEXT_CHANGED CONTEXT_EXPIRED CONTEXT_FOREIGN CONTEXT_INACTIVE CONTEXT_INACTIVE_OR_REMOTE CONTEXT_UNKNOWN CONSOLE_ACCOUNT_EQUALITY_UNPROVEN',
    'reaudit': 'STALE_EVIDENCE_REAUDIT_REQUIRED SNAPSHOT_CHANGED_DURING_AUDIT PLAN_REQUIRES_STABLE_SNAPSHOT_AND_ROUTE_FACTS',
    'collect-proxy': 'LIMITED_METADATA_ONLY MINIMAL_METADATA_ONLY MISSING_ENVIRONMENT_EVIDENCE',
    'proxy-port': 'PROXY_PORT_ASSOCIATION_CONFLICT',
    'plan-rules': 'RULE_POLICY_MISMATCH',
    'plan-prepend': 'RULE_PREPEND_REQUIRED',
    'probe-plan': 'NETWORK_EFFECTIVENESS_NOT_TESTED PROXY_ENTRY_UNAVAILABLE HTTPS_PATH_UNKNOWN',
    'dns': 'DNS_PATH_CONFLICT BROWSER_DOH_CONFLICT',
    'ipv6': 'IPV6_BYPASS_OBSERVED',
    'udp': 'UDP_RULE_MISMATCH STUN_INCONCLUSIVE',
    'browser': 'WEBRTC_BYPASS_OBSERVED BROWSER_POLICY_IGNORED',
    'launcher': 'PROGRAM_PROXY_IGNORED',
    'clock': 'CLOCK_SETTING_REQUESTED TIMEZONE_LANGUAGE_GOAL',
    'cleanup': 'CLEANUP_REQUESTED',
    'fault': 'FAIL_CLOSED_UNVERIFIED',
    'dependency': 'RUNTIME_OR_PARSER_UNAVAILABLE',
    'permission': 'AUTHORIZATION_MISSING PERMISSION_DENIED PRECONTACT_ACTION_REJECTED LIVE_TERMINAL_REQUIRED PC0_TARGET_FORBIDDEN ENDPOINT_NEUTRALITY_UNVERIFIED RUNTIME_NOT_TRUSTED HOST_INTEGRATION_INVALID',
    'unsupported': 'HOST_CAPABILITY_UNAVAILABLE UNSUPPORTED_PRODUCT_OR_VERSION NATIVE_REPAIR_ADAPTER_UNAVAILABLE NATIVE_CONTROLLER_HOST_ADAPTER_UNAVAILABLE DNS_HOST_INTEGRATION_REQUIRED WINDOWS_SESSION_DNS_UNAVAILABLE UNSUPPORTED_PLATFORM',
    'input': 'INPUT_OR_RESPONSE_INVALID UNSAFE_OR_OFFLINE_PATH BUDGET_EXCEEDED FILE_NOT_FOUND_IN_APPROVED_SCOPE INVENTORY_CALLBACK_FAILED OS_QUERY_FAILED OUTPUT_SAVE_FAILED COLLECTOR_INTERNAL_FAILURE INPUT_INVALID INVALID_ARGUMENTS_OR_SAVE_FAILED SESSION_FAILED TIMEOUT CLEANUP_FAILED',
    'incident': 'INCIDENT_PRIORITY',
    'runtime': 'RUNTIME_PATH_INVALID',
    'keep': 'FAKE_IP_WITH_WORKING_HTTPS IPV6_TIMEOUT_ONLY EGRESS_TIMEZONE_DIFFERENCE',
}
REPAIR_PREREQUISITES = {
    'AUTHORIZATION_SCOPE_MISMATCH', 'ACTION_AUTHORIZATION_PENDING', 'CONTEXT_MISMATCH',
    'BACKUP_DIRECTORY_NOT_PRIVATE', 'BACKUP_SCOPE_MISMATCH', 'CANDIDATE_SCOPE_MISMATCH',
    'EXPLICIT_RULES_SOURCE_SCOPE_REQUIRED', 'INVALID_EXPECTED_DIGEST', 'INVALID_RETAINED_PLAN',
    'INVALID_SOURCE_IDENTITY', 'PLAN_CHANGED', 'PLAN_DIGEST_MISMATCH',
    'PLAN_DIRECTORY_NOT_PRIVATE', 'PLAN_READBACK_FAILED', 'POST_WRITE_VERIFY_FAILED',
    'REQUEST_CHANGED', 'SOURCE_SCOPE_MISMATCH', 'SOURCE_SNAPSHOT_CHANGED', 'STALE_FILE',
    'TARGET_MISMATCH', 'NATIVE_ADAPTER_FAILURE',
}
CATALOG['repair-prerequisites'] = action('clarify', 'ENV-06',
    '修复授权、快照或恢复前提不成立，先检查当前状态',
    ['检查精确计划/目标/权限/备份冲突；重新读取并展示更新的差异',
     '可能已有写入时先检查保留回执与当前文件，按独立恢复契约处理，不重复写入',
     '不能用Agent分支绕过拒绝、失效计划或恢复冲突'],
    ['当前目标与修复状态', '精确范围许可', '可用备份恢复'], ['前提解决后重新计划与复测'])
GROUPS['repair-prerequisites'] = ' '.join(sorted(REPAIR_PREREQUISITES))
FINDING_ACTIONS = {code: key for key, codes in GROUPS.items() for code in codes.split()}


def select(report, target_ref):
    guardian.alias(target_ref)
    if (type(report) is not dict or type(report.get('schema_version')) is not str
            or report.get('schema_version') not in {
            INPUT_SCHEMA, 'guardian-report/0.1', 'env-inventory/0.2'}):
        raise guardian.GuardianError('INPUT_OR_RESPONSE_INVALID')
    if report.get('target_ref') != target_ref:
        raise guardian.GuardianError('TARGET_NOT_BOUND')
    findings = report.get('findings', [])
    if type(findings) is not list or len(findings) > 128:
        raise guardian.GuardianError('INPUT_OR_RESPONSE_INVALID')
    codes = []
    for item in findings:
        code = item.get('code') if type(item) is dict else None
        if type(code) is not str or not re.fullmatch('[A-Z][A-Z0-9_]{0,95}', code):
            raise guardian.GuardianError('INPUT_OR_RESPONSE_INVALID')
        codes.append(code)
    if report.get('missing_fields'):
        codes.append('MISSING_ENVIRONMENT_EVIDENCE')
    if report.get('execution_status') == 'interrupted':
        codes.append('USER_CANCELLED')
    # Cancellation wins over every pending proposal, including modifications.
    if any(code in GROUPS['stop'].split() for code in codes):
        codes = ['USER_CANCELLED']
    selected = {}
    for code in codes:
        key = FINDING_ACTIONS.get(code, 'unsupported')
        if key not in selected:
            selected[key] = dict(action_id=key, **copy.deepcopy(CATALOG[key]), finding_codes=[])
        # Do not echo unrecognized codes: they may contain private data.
        selected[key]['finding_codes'].append(code if code in FINDING_ACTIONS else 'UNRECOGNIZED_FINDING')
    barriers = sorted(set(codes) & ({
        'AUTHORIZATION_MISSING', 'PERMISSION_DENIED', 'PRECONTACT_ACTION_REJECTED',
        'TARGET_NOT_BOUND', 'TARGET_USER_CONTEXT_MISMATCH', 'UNSAFE_OR_OFFLINE_PATH',
        'USER_CANCELLED', 'CANCELLED', 'DECLINED', 'CONSENT_TIMEOUT',
        'PC0_TARGET_FORBIDDEN', 'ENDPOINT_NEUTRALITY_UNVERIFIED', 'RUNTIME_NOT_TRUSTED',
        'HOST_INTEGRATION_INVALID', 'CONTEXT_CHANGED', 'CONTEXT_EXPIRED', 'CONTEXT_FOREIGN',
        'CONTEXT_INACTIVE', 'CONTEXT_INACTIVE_OR_REMOTE', 'CONTEXT_UNKNOWN',
        'CONSOLE_ACCOUNT_EQUALITY_UNPROVEN', 'LIVE_TERMINAL_REQUIRED',
        'STALE_EVIDENCE_REAUDIT_REQUIRED', 'SNAPSHOT_CHANGED_DURING_AUDIT',
        'PLAN_REQUIRES_STABLE_SNAPSHOT_AND_ROUTE_FACTS', 'ROUTE_OR_TARGET_NEEDS_CLARIFICATION'} | REPAIR_PREREQUISITES))
    for item in selected.values():
        item['builtin_execution'] = 'not_available_for_target_mutation'
        item['agent_fallback'] = ('investigate_scoped_repair' if not barriers and item['kind'] in {'agent_investigation', 'candidate_only', 'host_library_only'} else 'none')
        item['fallback_requirements'] = (['inspect_actual_target_and_supported_interface',
            'explain_exact_diff_impact_backup_and_recovery', 'obtain_required_specific_approval',
            'execute_only_reviewed_minimal_operation', 'read_back_and_redetect_same_scope',
            'never_bypass_denial_or_builtin_gate'] if item['agent_fallback'] != 'none' else [])
    return dict(schema_version=SCHEMA, target_ref=target_ref,
                status='stopped' if 'stop' in selected else 'selected' if selected else 'insufficient_evidence',
                actions=list(selected.values()), prerequisite_blockers=barriers, changes=[], authority='none',
                native_acceptance='not_established', environment_pass=False,
                next_phase='stop' if 'stop' in selected else 'resolve_prerequisites' if barriers else 'agent_review',
                completion='no_repair_performed')


class PrivateParser(argparse.ArgumentParser):
    def error(self, message):
        raise guardian.GuardianError('INPUT_OR_RESPONSE_INVALID')


def main(argv=None):
    parser = PrivateParser(description=__doc__)
    parser.add_argument('command', choices=['catalog', 'select'])
    parser.add_argument('--input')
    parser.add_argument('--target-ref')
    try:
        args = parser.parse_args(argv)
        if args.command == 'catalog':
            result = dict(schema_version=SCHEMA, actions=CATALOG, findings=FINDING_ACTIONS,
                          authority='none', target_mutation_supported=False)
        else:
            if not args.input or not args.target_ref:
                raise guardian.GuardianError('INPUT_OR_RESPONSE_INVALID')
            result = select(guardian.load_json(args.input), args.target_ref)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    except guardian.GuardianError as exc:
        print(json.dumps(dict(status='blocked', code=exc.code, changes=[], authority='none')))
        return 2
    except KeyboardInterrupt:
        print('{"status":"stopped","code":"USER_CANCELLED","changes":[]}')
        return 130


if __name__ == '__main__':
    sys.exit(main())
