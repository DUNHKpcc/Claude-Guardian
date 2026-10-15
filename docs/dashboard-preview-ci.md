# 合成状态面板：真实浏览器截图 CI

## 范围与证据边界

对应 ENV-01—05、ENV-10 的状态展示，以及用户要求的简约界面预览。此流程调用现有 `status_dashboard.render`，固定合成输入与时间（2026-10-15 12:00 UTC），保留页面上的“合成演示”和未执行/未知状态。它没有运行任何真实设备、DNS、STUN、代理、Claude 或用户配置检测，也不建立任何平台验收结论。

- 已实现：确定性合成 HTML、静态内容检查、CI 截图命令、中文字体前置检查、PNG 尺寸/哈希记录、限定产物上传
- 本地验证：16 个无浏览器单元测试通过；测试中的 PNG 头部只是协议夹具，绝不能作为截图交付
- 真实浏览器截图：须以具体 GitHub Actions run 的成功结果为证；本文件的实现记录不代表已经运行
- 视觉验收：下载真实 PNG 并查看像素之后才可确认；生成文件或 PNG 尺寸正确不代表视觉检查通过

## 执行与依赖

新的 `Synthetic dashboard browser preview` 工作流使用 GitHub 官方 `ubuntu-24.04` 镜像，只在 main 的相关路径 push 或手动 workflow_dispatch 时运行，无定时任务、无新网站。沿用仓库 `actions/checkout@v4` 版本约定，使用官方 `actions/upload-artifact@v4`。权限仅 `contents: read`，checkout 不保留 Git 凭据。运行消耗现有 GitHub Actions 配额，不引入新付费服务；浏览器版本与字体可能随镜像更新，像素不承诺跨版本完全一致。

脚本只查找镜像已有 Chrome/Chromium，不下载安装浏览器或系统包。调用 `fc-list :lang=zh family` 验证存在 Fontconfig 声明支持中文的字体，清单记录最多 20 个字体族。此检查不替代查看实际中文字形，发现方框字仍须判为视觉失败。

Chrome 以非 root 用户、默认 sandbox、安全机制和全新临时 profile 运行。命令行减少后台网络活动，页面 CSP 禁止外部资源，静态检查拒绝脚本、资源属性、CSS URL/import。没有关闭 sandbox、Web 安全或浏览器安全提示；没有凭据、扩展或用户 profile 输入。此流程没有证明浏览器所有后台网络完全隔离，manifest 明确记录 `network_isolation_verified: false`。

本地仅生成 HTML（不自动打开）：

```sh
python tools/render_dashboard_preview.py --output /tmp/new-synthetic-dashboard.html
python -m unittest discover -s tests -p test_dashboard_preview.py -v
```

真实截图只在 Linux GitHub Actions 上执行：

```sh
python tools/render_dashboard_preview.py --capture-ci --ci-font --output "$RUNNER_TEMP/guardian-dashboard-preview"
```

输出目录必须不存在；既有目录或符号链接均拒绝。捕获失败、超时、取消或缺字体不改用伪造图片，也不添加安全绕过参数。缺字体不会隐式触发下载；只有显式 `--ci-font` 且通过 CI 门禁才启用下述临时字体。Chrome 有 60 秒单次等待上限；每次新建独立 session/process group，标准输出与错误直接丢弃，不在内存累积浏览器日志。Linux waitid 的 WNOWAIT 保留 leader PID 至组清理，避免先回收 PID 再发组信号的复用窗口；成功、失败、超时与取消均清理该自有进程组，再最多等待 5 秒回收 leader，清理失败明确报错。此保证不覆盖主动脱离进程组的守护进程、无法中断的内核等待或所有操作系统故障；不搜索或终止其他浏览器。整个 job 最多 5 分钟。HTML、profile、浏览器输出不进入 artifact。

## CI 专用临时中文字体

首次浏览器工作流 run `38768934000` 在 `PREVIEW_CJK_FONT_MISSING` 停止，没有启动 Chrome、没有生成截图。为保持中文 UI 和字体检查，工作流现在显式使用 `--ci-font`，只下载一个约 17 MB（15.7 MiB）的免费官方字体数据文件；它不是系统字体安装、软件包安装、Skill 运行时依赖或网站外部资源。

- 官方仓库：`notofonts/noto-cjk`
- 固定提交：`f8d157532fbfaeda587e826d4cd5b21a49186f7c`
- 文件：`Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf`
- SHA256：`2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b`
- 许可：OFL-1.1；Adobe 字体版权保留。使用字体生成的截图不改变项目许可
- 校验来源：[同一提交的官方 SPDX manifest](https://github.com/notofonts/noto-cjk/blob/f8d157532fbfaeda587e826d4cd5b21a49186f7c/_manifest/spdx_2.2/manifest.spdx.json)
- [固定字体资产](https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf)；[固定许可](https://github.com/notofonts/noto-cjk/blob/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/LICENSE)

下载只接受上述 HTTPS URL，使用默认 TLS 验证、无凭据、禁用继承代理、拒绝所有重定向；检查 Content-Length（若有）与实际读取量的 20 MiB 上限。网络 socket 设置 30 秒无活动超时；60 秒已用时间预算仅在每次分块读取完成后检查。一次分块读取可能包含多个 socket 接收，持续缓慢传输仍可能让该次读取超过 60 秒，因此这些检查不是严格的总下载时限。外层 GitHub Actions job 的 5 分钟超时仍为整项任务的取消上限。字节哈希一致后才写入私有临时字体目录供解析，不使用下载代码或安装脚本。

Fontconfig 使用独立最小 XML，只包含该临时字体目录和该任务临时缓存目录，不包含 `/etc/fonts/fonts.conf` 或用户字体配置，也不写系统字体/缓存。`FONTCONFIG_FILE`/`FONTCONFIG_PATH` 仅通过子进程环境传给字体检查和 Chrome，不修改全局 `os.environ`。捕获后临时目录清理；font/config/cache 不上传，manifest 只记录公开来源 URL、哈希、许可和字体族，不包含私有路径。页面 HTML/CSS 不变，仍无外部资源。

普通 `--capture-ci` 未启用此选项时，缺字体仍明确失败。单元测试模拟下载成功、哈希错误、超限、重定向、HTTP/网络错误、超时及进程环境隔离；这些测试不下载真实字体，不替代 CI 的真实文件校验与中文像素检查。

依据：[Fontconfig 官方配置说明](https://github.com/fontconfig/fontconfig/blob/main/doc/fontconfig-user.sgml)。

## 产物与人工验收

Artifact 名称为 `dashboard-preview-<exact commit SHA>`，保留 7 天，只包含：

- `desktop.png`：1440 × 1000，真实 Chrome 截图
- `mobile.png`：390 × 1100，真实 Chrome 窄窗口截图；不是手机设备/触屏仿真
- `manifest.json`：Chrome 版本、CJK 字体族、合成时间、HTML 哈希、PNG 尺寸与哈希、范围限制

先确认 run 对应的精确提交与成功步骤，再取 artifact。GitHub connector 提供 `fetch_workflow_run_artifacts`（仓库、run ID、可选名称）与 `download_workflow_artifact`（仓库、artifact ID），后者返回 ZIP 文件引用。必须使用实际返回的受支持文件引用下载，不能猜测存储 URL 或令牌；取到引用不代表当前执行器已得到可读字节。若物化失败，应报告具体限制，不能声称已查看或已交付图片。

下载后检查归档只有上述三个文件、没有链接/路径穿越，再核对 manifest 的 PNG 哈希与尺寸。打开两张真实截图检查：

1. 中文字形正常，没有方框/乱码；合成演示标识可见
2. 标题、11 项状态、关键事实和底部权限说明无意外遮挡/裁切
3. 窄窗口表格可读、列宽合理、没有水平溢出
4. 主界面简洁，详情默认收起；截图不能证明点击或键盘交互正常

只有以上通过后才能报告该提交的“合成界面视觉 QA 通过”。截图不能证明真实网络可用、无 DNS 泄露、Claude 可访问或 Mac/Windows 设备验收通过。

## 回退与参考

回退只需移除本工作流及其工具/测试/说明，不改运行时诊断行为、不删除已有 artifact。未启用服务或修改用户环境。

官方依据：

- [Chrome Headless](https://developer.chrome.com/docs/automation-and-testing/headless)
- [Chromium screenshot command switch](https://github.com/chromium/chromium/blob/main/components/headless/command_handler/headless_command_switches.cc)
- [GitHub Ubuntu 24.04 runner image](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md)
- [Official upload-artifact action](https://github.com/actions/upload-artifact)
- [GitHub artifact download API](https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#download-an-artifact)
