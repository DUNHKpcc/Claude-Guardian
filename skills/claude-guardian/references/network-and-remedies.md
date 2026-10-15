# M04/M05/M10: network evidence and offline remedies

中文执行摘要：按程序、路径、协议、地址族和时间解释证据。系统代理/TUN 与 rule/global/direct 分开；配置存在不代表生效。DNS、IPv6、UDP/WebRTC 超时不是阻断证明。先定位问题，再给最小修改计划，保留内网、隧道与 Codex 通道；本版所有主动网络测试均未开放。

Read only for relevant network/client tasks. Every method below is a diagnostic interpretation or future validation requirement, not permission to run a probe or apply settings. The preview is offline except explicitly authorized local metadata reads; neutral network probes remain unavailable.

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
| IPv6 bypass observed | Repair application/TUN scope or propose explicit workflow-limited IPv4-only behavior; preserve IPv6-dependent outer proxy transport |
| IPv4 works, IPv6 times out | Record unavailable/unknown IPv6; do not report a working kill switch or globally disable IPv6 |
| Browser WebRTC bypass confirmed | Propose supported origin-scoped non-proxied-UDP restriction; disclose media effects and preserve other origins |
| Policy exists but browser ignores it | Check key/type/version/profile/management precedence and refresh requirements; do not overwrite the entire policy tree |
| HTTPS succeeds, STUN fails | Preserve the HTTPS finding and investigate STUN-specific path/endpoint uncertainty; no automatic account cleanup or node cycling |
| TUN UDP route uses wrong rule/node | Propose a limited rule/node-capability correction; preserve Hysteria2/TUIC outer UDP and other applications |
| Timezone/language differs from egress label | No automatic remedy; ask the actual user setting goal and distinguish clock accuracy from display |

ENV-06 plan families are: keep current configuration with narrow rule repair; explicit proxy plus rules; TUN plus rules; explicitly scoped compatibility fallback. Do not publish an unvalidated universal Clash YAML. Account for GUI/extension merge priority, effective runtime, subscription updates, first-match ordering, internal exceptions, Codex connectivity, and rollback conflicts.

## Future probe/validation design, not shipped capability

The inherited design names ipify (ENV-SPEC:E53) and Cloudflare STUN (E54) as candidates, not approved endpoints. A future endpoint registry must include scheme/host/port/path, purpose, disclosure, request limits, redirects, parsing, and no paid model calls. DNS and HTTPS contacts still need authorization. Do not follow a report's URL automatically.

Future WebRTC sampling should use the user's actual chosen browser/profile and an audited local-origin page without remote scripts, media permissions, TURN, or account data. STUN traffic means it is not offline. Record origin, version, effective policy, candidate classes, completion/errors, and unobserved media path. A local page does not test the Claude origin. Do not manufacture a pass by silently restricting candidates before the baseline sample.

Browser policy details are historical source statements, not tested support: E57/E58 describe Chrome URL/global keys; E11/E59 describe Edge and profile limitations. Verify actual version, policy acceptance, origin matching, and scope before any later write. Safari/Firefox retain a manual planning branch. A global fallback needs separate scope approval; never silently log out of a browser profile or remove sync.

ENV-10 validation must eventually cover proxy/core stop, restart, path updates, child processes, dual stack, relevant UDP, and restoring control-channel access on real target platforms. An unchanged rule count, current connectivity, or failed test request proves none of those. Preserve independent offline recovery before future fault tests.

## Report format

For each finding provide: stable module ID; result; target/program/profile/path/family; observation and source/time; unknowns; proposed minimal change; preserved objects; expected future observation; next module; authorization/capability blocker. Avoid risk scores. Deduplicate shared root causes instead of proposing repeated network rewrites.
