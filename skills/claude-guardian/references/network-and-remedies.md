# M04/M05/M10: network evidence and offline remedies

中文执行摘要：按程序、路径、协议、地址族和时间解释证据。系统代理/TUN 与 rule/global/direct 分开；配置存在不代表生效。DNS、IPv6、UDP/WebRTC 超时不是阻断证明。先定位问题，再给最小修改计划，保留内网、隧道与 Codex 通道；已有须经可信宿主核验与逐次授权的有限 HTTPS/STUN/DNS 探测库；尚无通用主动网络 CLI，也未完成端到端原生验收。

Read only for relevant network/client tasks. Every method below is a diagnostic interpretation or future validation requirement, not permission to run a probe or apply settings. The preview is offline except explicitly authorized local metadata reads. Bounded HTTPS/STUN/DNS host libraries exist, but require their specific trusted-host binding, endpoint/scope checks and fresh approval; they are not a general active-network CLI or completed end-to-end native acceptance. This reference grants no probe authorization.

See [sanitized macOS DNS/IPv6/Tailscale case lessons](macos-dns-case-lessons.md) for a derived single-device example and its evidence limits. Configuration drift invalidates conclusions about the new state; process-bound direct checks do not establish stop/restart lifecycle behavior, and UDP/TCP DNS coverage must be evaluated separately.

<a id="claude-target-ipv4-only"></a>
## PRODUCT-IPV4-20261018: selected Claude traffic is IPv4-only

中文执行要求：2026-10-18 已确认所选 Claude 目标／应用流量只允许 IPv4，不得在失败时回退 IPv6。即使尚未观察到旁路，也要在网络准备中规划并核对此要求；不能因为暂时连通或没有报错就省略。历史 D05 的双栈优先推荐在这个范围内由新产品选择取代，原规格／验收行和历史案例不改写。无需重新询问协议偏好；只补实际目标范围、能力与证据缺口。

Keep three layers separate: the product policy is `IPv4_ONLY`; scoped enforcement support may be unknown or unsupported; compliance is not established without current same-scope verification. This batch's pure policy/planning/reporting interfaces cannot certify enforcement or grant execution. Imported JSON claims, saved approvals, G2 planning readiness and successful independent rule edits cannot promote that status. Lack of a supported mechanism does not change the policy to dual stack.

1. Enumerate the selected application, profile, target/function flows and participating subprocesses. A parent proxy environment variable is not child-process enforcement. For a proxy path, identify the application-to-proxy path and the proxy-to-target address-family decision separately; an IPv4 loopback listener does not prove the target leg is IPv4-only
2. Preserve the proxy's outer node transport, including necessary IPv6/UDP, separately from the target leg. Also preserve loopback, Codex and independent recovery channels, organization rules, VPN/private DNS, other applications, system interface IPv6 and all unselected flows. A global switch or browser-wide restriction is not an acceptable silent substitute for selected-scope control
3. If the target leg cannot be isolated, report the unresolved or unsupported scope and propose concrete alternatives. A broader mechanism requires its own disclosed scope, impact and approval; do not treat the product choice as host-change authorization. Do not silently drop an uncovered child/profile from the promised scope. If IPv4 is unavailable, report that workflow unavailable under the policy, without IPv6 fallback
4. Build a minimal version-specific plan with exact before/after settings, preserved objects, backup, independent restoration and future verification. When the mechanism is still unknown, identify the next bounded inspection needed instead of inventing a command. Do not run Claude or target-domain DNS/HTTPS to investigate in PC0; neutral probes and any later target contact still require their existing separate gates and approval
5. After any future approved change, verify the same application/profile/target leg and relevant subprocess, literal-IPv6, separate resolver and WebRTC paths, including failure, restart and configuration-update behavior. Retain each untested path as unknown; neither a configuration key nor one sample proves comprehensive enforcement. Establish control-channel recovery before fault tests, and obtain their distinct approval

AAAA absence only describes that resolver result. `dns.ipv6: false` describes its own configuration scope; `curl -4` constrains that client request and does not establish a proxy's target-leg choice. A successful IPv4 HTTPS sample, failed IPv6 request, no ICE candidates or single STUN response also cannot prove IPv6 fallback is excluded. Generic IPv6 samples may describe preserved outer transport or unrelated flows; do not automatically label them policy violations. Bind evidence to the actual target, path, configuration revision and time.

## ENV modules and evidence boundaries

| Stable ID | Purpose and required distinction |
|---|---|
| ENV-01 | Bind actual target, OS/Edition/architecture, namespace, and collector authority |
| ENV-02 | Inventory proxy/core/GUI/file/runtime/OS sources separately; configuration is not effective behavior |
| ENV-03 | IP/HTTPS observations scoped to process, path, target, time, and address family |
| ENV-04 | DNS layers, IPv6 paths, and UDP evidence kept separate |
| ENV-05 | Actual browser/profile/origin WebRTC and policy scope |
| ENV-06 | Minimal configuration plan preserving current subscriptions, rules, and control paths |
| ENV-07 | Launcher, GUI/terminal differences, interpreter and child-process coverage |
| ENV-08 | Clock, timezone, locale, language, and synchronization as independent facts |
| ENV-09 | Exact cleanup inventory/protection/backup/recovery plan |
| ENV-10 | Fault-blocking design and later real regression matrix; no fault injection in preview |

Collector failures are unknown/blocked, not bad configuration. Do not run the Claude binary to determine its version. No broad process command-line dumps, subscriptions, controller secrets, cookies, or raw logs in model output. Local/controller APIs require a real method/path whitelist, confirmed instance ownership and source, and sanitized responses; GET alone does not mean safe. Never scan controller ports or execute a configuration's JavaScript.

## Layered interpretation

A future approved check proceeds from selected proxy entry → scoped HTTPS sample → actual browser sample → DNS responsibilities → IPv4/IPv6 → relevant WebRTC/UDP → minimal remedy. Stop at missing target binding or approved endpoint. Do not make novices choose low-level protocol settings when the facts can be read safely.

- System/explicit proxy/TUN is an interception axis; rule/global/direct is a routing axis. TUN does not imply global routing
- A request reaching a proxy listener can still match DIRECT. A generic IP site need not follow the target service's route
- Distinguish network failure, DNS failure, TLS failure, HTTP error, invalid response, and unknown route. Keep certificate validation enabled
- Local DNS configuration, an actual system resolver answer, proxy-core DNS behavior, browser DoH, and authoritative correlation are different evidence levels. Fake-IP is not automatically a leak. A DNS answer/geolocation flag cannot locate the full recursive path
- IPv6 has at least four scopes: local interface, outer node transport, node-to-destination, and WebRTC candidates. AAAA absence and IPv6 timeout do not prove blocking
- HTTP CONNECT does not establish generic UDP proxying. SOCKS5 UDP support must be explicitly supported and observed; environment variables do not route arbitrary UDP sockets
- WebRTC host/private/link-local/mDNS candidates differ from public candidates. A different public candidate requires path/family analysis. ICE 701, no candidates, or timeout is inconclusive, not proof of no leakage
- A child's inherited proxy variable does not prove adoption. MCP subprocesses, external interpreters, plugins, background clients, and update paths require their own later evidence

## Finding → minimal plan

| Observation | Proposed remedy and preserved scope |
|---|---|
| Selected proxy entry unavailable | Check chosen instance, listener and stale configured port; do not silently install or restart it |
| IP endpoint matched DIRECT | Retain as a natural-route sample; propose a narrowly scoped neutral-domain route for a future authorized comparison |
| Explicit proxy ignored by a program | Identify supported transport/launcher configuration for that exact version; do not claim ALL_PROXY covers everything |
| Unexpected target DNS route | Separate bootstrap, ordinary, split/internal, and proxy-node resolution; repair only the responsible layer and preserve internal domains |
| Browser DoH conflicts with intended DNS | Compare effective browser policy and core responsibilities; propose narrow applicable changes rather than disabling all secure DNS |
| Fake-IP answer with working HTTPS | Explain the mapping and retain configuration unless additional evidence shows a fault |
| Claude IPv4-only scope or enforcement evidence missing | Plan selected-scope IPv4-only even without an observed bypass; keep support unknown/unsupported and compliance not_established, preserve outer/control traffic and obtain exact approval before changes |
| IPv6 bypass observed | Locate the actual target leg and repair its scoped IPv4-only enforcement under the current product policy; preserve IPv6-dependent outer proxy transport and unrelated traffic |
| IPv4 works, IPv6 times out | Record unavailable/unknown IPv6; do not report a working kill switch or globally disable IPv6 |
| Browser WebRTC bypass confirmed | Propose supported origin-scoped non-proxied-UDP restriction; disclose media effects and preserve other origins |
| Policy exists but browser ignores it | Check key/type/version/profile/management precedence and refresh requirements; do not overwrite the entire policy tree |
| HTTPS succeeds, STUN fails | Preserve the HTTPS finding and investigate STUN-specific path/endpoint uncertainty; no automatic account cleanup or node cycling |
| TUN UDP route uses wrong rule/node | Propose a limited rule/node-capability correction; preserve Hysteria2/TUIC outer UDP and other applications |
| Timezone/language differs from egress label | No automatic remedy; ask the actual user setting goal and distinguish clock accuracy from display |

ENV-06 plan families are: keep current configuration with narrow rule repair; explicit proxy plus rules; TUN plus rules; explicitly scoped compatibility fallback. Do not publish an unvalidated universal Clash YAML. Account for GUI/extension merge priority, effective runtime, subscription updates, first-match ordering, internal exceptions, Codex connectivity, and rollback conflicts.

The current IPv4-only policy is evaluated separately from these four legacy semantic plans. Do not inject networking changes into an unrelated rule edit or remove the older compatibility planner's outer-transport protection. A legacy intent to preserve target-leg IPv6 conflicts with the current product policy and must be disclosed; it is not silently reinterpreted as an instruction to block. Completing an independent plan does not satisfy the policy.

## Guarded host libraries and remaining native validation

The inherited design names ipify (ENV-SPEC:E53) and Cloudflare STUN (E54) as candidates, not approved endpoints. Existing bounded HTTPS/STUN and controller/system DNS libraries do not provide standing approval or a general probe CLI. A trusted host must enforce the applicable target, endpoint and request scope, disclosure, budgets and response checks; do not infer native integration or real-device acceptance from the libraries or synthetic tests. Endpoint review must cover scheme/host/port/path, purpose, disclosure, request limits, redirects, parsing, and no paid model calls. DNS and HTTPS contacts still need authorization. Do not follow a report's URL automatically.

Future WebRTC sampling should use the user's actual chosen browser/profile and an audited local-origin page without remote scripts, media permissions, TURN, or account data. STUN traffic means it is not offline. Record origin, version, effective policy, candidate classes, completion/errors, and unobserved media path. A local page does not test the Claude origin. Do not manufacture a pass by silently restricting candidates before the baseline sample.

Browser policy details are historical source statements, not tested support: E57/E58 describe Chrome URL/global keys; E11/E59 describe Edge and profile limitations. Verify actual version, policy acceptance, origin matching, and scope before any later write. Safari/Firefox retain a manual planning branch. A global fallback needs separate scope approval; never silently log out of a browser profile or remove sync.

ENV-10 validation must eventually cover proxy/core stop, restart, path updates, child processes, dual stack, relevant UDP, and restoring control-channel access on real target platforms. An unchanged rule count, current connectivity, or failed test request proves none of those. Preserve independent offline recovery before future fault tests.

## Report format

For each finding provide: stable module ID; result; target/program/profile/path/family; observation and source/time; unknowns; proposed minimal change; preserved objects; expected future observation; next module; authorization/capability blocker. Avoid risk scores. Deduplicate shared root causes instead of proposing repeated network rewrites.
