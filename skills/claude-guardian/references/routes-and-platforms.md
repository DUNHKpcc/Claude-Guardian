# M01/M06–M09: independent environment routes

中文执行摘要：本机默认建议须获得接受，VM/VPS 为独立可选方案。完整覆盖准备、接入、配置规划、后续交接、日常使用、更新、排障和恢复；本版不自动执行部署。Mac/Windows 是本机范围，Linux 客机/远端不被删除。宿主、客机、远端、容器和出口分别记录。

All three routes cover preparation, existing-environment intake, proposed setup, later contact handoff, ordinary use, update rechecks, diagnosis, and recovery planning. In 0.1.0 these are guidance and plans; automated provisioning, installation, network configuration, fault injection, and restoration are unavailable.

## Common concepts

The execution host runs Guardian; the target runs the future Claude workflow; an egress is where traffic leaves a network. An editor displayed locally can execute remotely. VPS ownership or using a VPS proxy does not make a local client a remote workspace. IP/ASN describe a sampled network, DNS resolves names, and SSH/OAuth/API keys perform different roles. Product subscription and developer API billing are separate; verify current eligibility after a permitted handoff.

## R-LOCAL / local (recommended, never silently selected)

Scope: macOS and Windows 10/11. Identify OS/version, Edition or relevant architecture, chosen client, installation metadata, proxy boundaries, and data protections. A browser-only task does not require Code/Desktop or firewall setup. Linux desktop and mobile-only users receive clearly limited general guidance; do not claim a native adapter or force a VM/VPS migration.

1. Interview and authorized native metadata reads; plan only necessary changes
2. Identify network/browser evidence gaps and post-contact compatibility checks
3. Explain PC-G1 and scoped handoff requirements; do not open the service to fill a PC0 gap
4. Later validated releases/manual approved workflows may install the chosen client and perform real PC-G2 checks; this preview does not do so
5. Record a repeatable startup plan and recheck after relevant app/core/profile/network updates
6. Diagnose by component; plan exact recovery with project/CLI/history protection

Windows: distinguish Home from Home Single Language. Display-language licensing does not prove timezone controls are disabled. Diagnose automatic versus manual timezone, user privileges, policy, and a value reverting separately. Do not use registry hacks or unofficial Home policy-editor installs. Distinguish UI language, keyboard, regional format, app/browser language, timezone, and actual clock. Record Windows 10 maintenance arrangements when relevant; do not upgrade the OS automatically. Windows sandbox/WSL metadata is not necessarily the desktop user's configuration.

macOS: identify actual version/architecture and application versus system settings. A translated process does not establish native architecture support. Permission denial is unknown/blocked, never an automatic sudo request. Built-in incoming firewall settings do not prove per-process outbound isolation. No default timezone, language, or identity changes.

## R-VM / vm (optional)

Existing/new VM → separate host/guest resource and architecture inventory → guest network/OS plan → shared-directory/clipboard/credential boundaries → scoped preparation evidence → explicit handoff → client compatibility/authentication plan → startup/update/backup/recovery plan.

Use the user's chosen hypervisor; do not force recreation. Record NAT/bridged/other mode and actual host-versus-guest proxy reachability; guest loopback is not host loopback. Check guest compatibility independently. Snapshots may include secrets and mounted data may be outside their scope. Do not copy credentials, create snapshots, install a guest, or restore anything in preview. A snapshot cannot reverse remote account enforcement. Keep host evidence separate from guest results.

WSL and containers are runtime layers, not interchangeable VM products. Record machine, namespace, networking, mounts, process location, and browser location. A container inside a VPS remains part of that VPS task. Preview adapters may be unavailable even when the conceptual route is supported.

## R-VPS / vps (optional)

First confirm workspace versus exit-only role. For a workspace: existing/new server → project/local-dependency fit → region/resource/cost plan → SSH and independent rescue → least-privilege development user/firewall plan → network preparation → scoped handoff → required client/authentication plan → terminal/Remote-SSH/tmux operation → optional temporary browser closure → monitoring/backups/update checks.

Label every step local versus server. Reuse existing machines; do not assume an empty server, reimage, benchmark production, or purchase resources. A Linux remote server remains in scope conceptually; it does not extend the native desktop collector matrix. No SSH secrets in reports. Cloud firewall and guest firewall are separate; network modifications require a working independent rescue path. Temporary GUI access needs authentication and restricted transport, never public/no-password VNC. A remote browser is optional according to actual login needs. OAuth redirects and local callbacks must match the actual approved flow; never transfer tokens through chat.

If the task depends on local GUI/software/hardware or data cannot leave the machine, flag feasibility before deployment. Extra egress is an optional requirement to assess, not a mandatory purchase. Costs, legal terms, region support, and vendors remain pending current verification. Exit changes are not proof of service eligibility or a cure for suspension.
