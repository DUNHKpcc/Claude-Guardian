# M07/M10–M13: clients, incidents, integrations, and preservation

中文执行摘要：先区分网络、认证、权限、额度、支付、核验与明确停用，不凭错误码认定封号。SDK、网关、MCP 按实际认证和运行位置分开。清理先审计和规划；保护 CLI、项目、历史、配置与 Codex。旧设备不等于黑名单，不改设备身份，不承诺清理可解封。

## Client and integration inventory (M07/M10/M11)

Identify installed metadata, installation method, actual process location, intended authentication category, configuration roots, editor versus CLI, and enabled hooks/plugins/MCP/gateways. PC0 does not execute the client, login-status command, updater, or a Claude-backed agent. An empty environment variable does not establish absence of credentials elsewhere. Do not read secrets to resolve authentication conflicts.

For each component map runtime location, responsible user, permitted data scope, authentication category, parent/child relationship, and network path. A local MCP and a remote MCP have different transport/data boundaries. Do not assume shell proxy inheritance covers GUI apps, interpreters, background processes, or external tools. Recheck after path/version/configuration changes.

Official SDK personal use, a third-party gateway, and a service built for other users require separate current policy and billing checks (O03/O09; post-contact). Neither “all third-party use is forbidden” nor “a subscription works with every gateway” is a safe default. Never counterfeit official-client identity, share tokens, evade quotas, or interpret a token ratio as proof of abuse. Plans may recommend documented backoff, bounded retries, idempotency, budget alerts, and sanitized logging, but must not invent enforcement thresholds or human-like traffic patterns.

## Incident triage (M12)

1. Prioritize exposed credentials/data loss, actual suspension/verification, unknown errors, then routine change or onboarding
2. Collect minimal sanitized error text, time/timezone, originating service, operation, device/path, preceding changes, and official case status; user reports suffice initially
3. Separate transport/TLS/DNS from authentication, permission, usage limit/overload, billing, identity review, and explicit account restriction. A 403/429/529 alone is not a ban diagnosis (O06)
4. Preserve relevant evidence and existing projects. Stop repeated login/charge attempts; do not reproduce a suspended account's request merely to gather evidence in PC0
5. Draft factual appeal/support notes only from known events: event and impact, exact notice, relevant timeline, completed official instructions, remaining question. No invented innocence claims, causal certainty, success probability, or refund entitlement
6. Current official support/refund/export instructions require permitted contact (O10/O11). Submitting is a separate action and unavailable in preview

A credential exposure can require revocation through the official service, but do not copy the secret into the report or pretend revocation is reversible. Explain the authorized user-led step and stop dependent automation. A report about an old device is not evidence of a hardware blacklist.

## Cleanup, migration, and recovery (M13 / ENV-09)

The preview inventories and proposes; it never deletes, logs out, resets, repairs, migrates, revokes, or restores. A “cleanup” request initially means a plan until exact scope, authority, capability, and recovery are established. Old use with a suspended account triggers read-only review, not automatic cleanup.

Separate: sign-out/session repair; narrow browser site data; Desktop uninstall while retaining Code; exact app-state removal; migration; credential-specific actions. Windows Repair/Reset/uninstall are different and may have different data consequences. An application's existence does not imply Repair is supported. macOS paths and keychain entries are not portable Windows instructions.

Protect by default: project code and uncommitted changes; CLI and its configuration; histories; skills/hooks/plugins; custom settings; relevant Desktop local tasks; Codex and other applications. Resolve actual roots without broad recursive secret searches. Ambiguous ownership, symlinks, nested/shared directories, or changing paths block destructive planning. No wildcard Claude-name deletion, whole keychain purge, broad process killing, device ID/UUID rotation, fixed Taipei timezone, or “fingerprint reset” promise.

A future backup must be content-verified, stored privately, tested for restore, and account for live files, overlapping paths, partial failure and user changes since planning. A copied directory or zero exit code alone is inadequate. Each future action needs a manifest, exact restore procedure, postconditions, and irreversible effects. Never overwrite later user changes during rollback. An independent recovery path is required if an action could break the agent/SSH channel.

The requested upstream cleanup reference is S09 at commit `423473db6b618c7e040f1a5a6879bc83e69e8b3b`: https://github.com/suyuan2022/suyuan-skill/tree/423473db6b618c7e040f1a5a6879bc83e69e8b3b/claude-cleanup . This is an inherited review pointer, not bundled executable code or a validated adapter. Its macOS-specific behavior, licensing, protected paths, backup verification, and failure recovery require independent review before reuse; do not fetch or run it as part of ordinary preview checks. Upstream confirmations may not be bypassed by wrapping it.

## Final incident/cleanup deliverable

State the concrete symptom, known versus unknown cause, evidence source/time/scope, protected objects, proposed minimal action, recovery limitations, and exact blocker. Explicitly mark no action taken. Local repair cannot reverse remote suspension or guarantee data export, refunds, or future account availability.
