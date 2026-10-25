# Conservative inventory entrypoint

`skills/claude-guardian/scripts/inventory_cli.py` reads a Clash configuration you
point it at (static audit) and lists what the CLI can do. It writes nothing,
scans nothing and opens no network connection; output goes to stdout.

```sh
python skills/claude-guardian/scripts/inventory_cli.py capabilities
```

Network checks are in `network_check.py`.

## Static audit, on the intended Mac only

Before invoking this command, the host must independently establish the target
Mac, desktop user, filesystem namespace, and permissions. Both request and
configuration files must already be local and hydrated. The CLI cannot verify
mount locality or prevent a blocked filesystem syscall; a host process timeout
is still required. Never run this on a cloud/remote environment to represent a
user's Mac. Native application compatibility acceptance is still `not_run`.

Create an explicit private JSON request, using exact canonical absolute paths
with no symlink ancestors. Do not insert credentials, URLs, raw configuration,
authorization objects, or saved grants. Example uses invented paths:

```json
{
  "schema_version": "guardian-static-cli-request/1",
  "target_ref": "device-1",
  "target_binding": {
    "target_ref": "device-1",
    "binding_state": "bound",
    "declared_os": "macos",
    "execution_location": "native_local",
    "desktop_user_relation": "same",
    "filesystem_namespace": "host_desktop"
  },
  "application": {
    "product": "clash-verge-rev",
    "gui_version": "2.5.5",
    "core_version": "1.19.0"
  },
  "files": [
    {"source_ref": "profile-1", "kind": "profile", "path": "/approved-local-directory/profile.yaml"}
  ]
}
```

```sh
python skills/claude-guardian/scripts/inventory_cli.py static-audit \
  --request /approved-local-directory/request.json --target-ref device-1
```

The request itself is read when explicitly named. Only after bounded strict JSON
and complete scope validation does the CLI display the exact configuration paths
on the local terminal and require a fresh `READ` response. Configuration bytes
are not read before that response. stdin and stderr must both be terminals;
there is no `--yes`, approval token, environment-variable bypass, or noninteractive
grant. EOF, a different response or interruption cancels. Paths are JSON-escaped
in the prompt and are omitted from the report. Do not copy private local prompts
into shared logs. Fixed errors never echo parser errors or raw configuration.

**Trust boundary:** a terminal response is a caller assertion, not authenticated
human consent and not host/OS approval. A pseudo-terminal can be automated. The
request's target and locality fields are also assertions. Host permission and
identity checks remain mandatory and cannot be inferred from a passing report.
A noninteractive host may call the libraries directly using separately obtained
genuine approvals and verified identity; it must not convert model-generated
flags into approvals or treat this CLI as an OS isolation mechanism.

The static collector returns whitelist fields only, retains provenance limits,
and leaves contact gates closed. It does not establish active profile, runtime
routing, extension merge semantics or environment readiness. Windows static
reads fail closed; the CLI request-reader is POSIX-only. No dependencies are
installed automatically. PyYAML is optional; missing parsing support is reported.

## Output and validation

Help (`--help` on the root or any subcommand) also returns one JSON object,
with `status=help` and a `help` string, on the selected output stream. It returns
0 without raising `SystemExit` through the callable `run` API.

Output is one `guardian-inventory-cli-result/1` JSON object with fixed metadata
and the component result. Exit codes: 0 = usable informational/partial result
(never environment pass); 2 = invalid input, unsupported capability or collection
error; 3 = permission/interactive-approval rejection or cancellation; 4 = internal
failure. Component errors remain visible and return nonzero. Diagnostic revision
IDs and timestamps intentionally vary per run and are not durable permissions.

```sh
python -m unittest discover -s tests -p test_inventory_cli.py -v
```

Tests use temporary synthetic files and mocked platform values only. POSIX
reader tests are skipped on Windows, while cross-platform informational
commands, help, and controller no-I/O boundaries remain tested. A synthetic `darwin` value is not Mac native evidence.
The test suite does not read real configuration, modify native settings, or
contact controllers. Source packaging and release docs must explicitly include
these new files before advertising them as shipped.

## 可选解析器和分发边界

静态YAML读取使用可选PyYAML；运行时缺失即返回结构化缺依赖结果，不联网下载、不自动安装。测试环境在 `requirements-dev.txt` 固定 `PyYAML==6.0.3`，CI显式安装以确保解析测试不会因环境缺库而被悄悄漏掉。发行ZIP不打包PyYAML代码或解释器；部署者按其环境和软件安装授权准备依赖。测试版本不是对未来库版本的兼容承诺。Windows的POSIX描述符读取后端仍不开放，测试跳过必须在平台结果中单列。

`SCHEMA_FIXTURE_GUI` / `SCHEMA_FIXTURE_CORE` 是合成样例所用版本标签；不证明已在这些版本的真实Clash Verge Rev/Mihomo上完成兼容认证。控制器响应投影也不是完整配置图或流量命中证据。
