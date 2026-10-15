# 原验收案例与当前测试证据映射

审阅日期：2026-10-15。静态审阅起点 HEAD：`be2e626a3626bfb853babf2b407fd67be146ec82`；包含当时工作树已有的 `tests/test_guides.py` 及随后补入的同大小备份损坏回归，不把工作树文件假称已提交。原案例全集取自 [implementation-tracker.md §8](implementation-tracker.md)：T01—T94 与 ENV-T01—ENV-T124，共218项。设计依据为主规范附录D、§11及ENV规范§19、§20。

## 如何使用本表

- **本次只读取代码/断言，没有运行测试，没有修改原218项状态；本表不新增任何整案例通过结论。** 执行结果、平台、提交及跳过原因应另见 [validation.md](validation.md)，不能把历史结果继承到后续工作树。
- 每行都是**部分子证据**：测试确实断言了什么，以及原案例还缺什么。一个案例对应多个测试，并不等于所有条件都被验证。未列出的断言与代码存在也不自动算验收证据。
- `tests/文件.py::类.test_方法` 是可直接定位的完整名称；表内先给文件/类，再列方法。源码路径统一以仓库根目录为起点。
- 单元测试中的 `native_pass`、`TARGET_NATIVE`、`approved=True`、绑定回调都是构造输入，不能证明真人授权、真实设备身份或原生验收。POSIX临时文件、回环假服务比纯mock更接近运行，但仍不是实际配置/应用验收。
- “95-ID”指问题登记表含95个历史ID，**包括永久停用Q-C07**；`test_complete_registry`只检查数量、Q-C07登记存在且不展示/不可作答，不证明95项所有字段和分支完整符合规格。

## A. 访谈、续接与CLI（M00 / ENG-01）

实现：`skills/claude-guardian/scripts/interview_flow.py`、`interview_cli.py`。下表无其他说明时均指 `tests/test_interview_flow.py::InterviewTests`。

| 原ID | 测试方法 | 实际断言的子证据 | 尚缺的原条件/边界 |
|---|---|---|---|
| T01、T29、T57、T73、T74 | `test_subscription_first_and_reuse`、`test_first_and_returning_do_not_get_old_billing`、`test_complete_registry` | 首问Q-J01后Q-C02；首次/重订不列P02/A06，仍列C08；C07拒绝 | L0讲解、套餐/资格前提、全对话次序与实际UI |
| T75、T78 | `test_experience_never_implies_subscription` | 含糊经历保留unknown，问J02；明确已有后问C11 | 长期免费版/熟练度的自然语言多字段场景 |
| T76、T77 | `test_first_and_returning_do_not_get_old_billing`、`test_existing_upgrade_gets_old_channel` | 重订意图resubscribe；已有升级列当前渠道及目标套餐 | 旧权益迁移、真实升级冲突及讲解裁剪 |
| T41、T80 | `test_actual_conflict_reopens_only_relevant_old_billing` | subscription_conflict打开P02/A06 | 页面冲突识别、未解决不扣款、账户对应完整流程 |
| T43、T84、ENV-T36 | `test_existing_technical_task_skips_payment` | 已有订阅network任务不列C11/C08及P/A/W | cleanup任务、首次进入环境阶段的逐字段回归；不是任意任务全覆盖 |
| T19、T20、T21、T22、T26、T27、T34 | `test_route_is_not_inferred_from_default` | 未选路线unconfirmed；显式local/vm/vps只启用对应分支 | 资产≠选择的自然语言识别、各路线新手手册行为、接受默认建议 |
| T02、T30、T51、T81、ENV-T02、ENV-T96 | `test_aliases_do_not_repeat`、`test_selective_refresh_retains_other_known_facts` | OS/Z别名归一；一个字段失效不丢订阅阶段 | 一句话同时吸收全部字段、Clash信息复用、仅追问授权的端到端轨迹 |
| T16、T24、T94、ENV-T123 | `test_saved_state_requires_scoped_opt_in_and_resets_permission`、`test_new_task_preserves_identity_but_resets_purchase_target` | 保存需host_opt_in；恢复不恢复保存权限，G3仍blocked；新任务重置购买目标/PC0 | 旧schema迁移、VM/VPS续接专例、文件取消写入与设备事实时效全链路 |
| T52、ENV-T83 | `test_target_bound_and_immutable_updates`、`test_question_subject_roles_are_enforced`、`test_device_change_preserves_subscription_only` | 不同对象拒绝写事实；换设备清设备事实、保留订阅；原state不被原地改写 | 不同时点/账号冲突的实际澄清对话 |
| T35、T46、T47、T54 | `test_unknown_refusal_deferred_are_not_false_or_reasked`、`test_bounded_clarification`、`test_pause_block_defer` | unknown/declined/deferred不等于false、不重问；G2 blocked；暂停/延期可恢复；澄清有界 | 每字段具体查看帮助、资格解释、条件式方案内容与费用指令限制 |
| T48 | `test_suspension_prioritizes_incident_over_new_purchase` | 当前停用只开放H分支，G1 emergency_deferred，解决后恢复C08 | 凭据泄露分支、最小止损动作和事实来源确认 |
| T36—T38、T83、T92、ENV-T85 | `test_apple_gift_card_branch_and_contact_deferral`、`test_other_payment_branches` | Apple指定问题存在；PC0推迟接触项、PC1出现A04；Google/网页/API/企业分支区分，组织项按条件出现 | Apple十项具体条件判定、G04旧权益措辞、商店/设备/账户/支付实证；手机不能继承PC结果 |
| T56、T90 | `test_asked_is_not_answered`、`test_all_relevant_answered_is_coverage_not_action_permission` | 问过不等于答过；适用问题完成可令G1 complete/G2 pass但G3 blocked | 所有条件分支覆盖、实际动作适配器联动 |
| T58—T64、T66、T68、T69、T72 | `test_windows_conditionals`、`test_macos_and_out_of_scope` | OS分支、时区问题/显示语言问题条件触发；mobile_only走OS12 | **不是这些平台案例通过**：SKU能力、单语言版限制、权限/受管、Linux出口和Win10支持状态尚未逐例断言 |
| T82、ENV-T92 | `test_complete_registry`、`test_reject_invalid_saved_state` | C07不可展示/回答；含C07的保存状态拒绝 | 拒绝旧状态不等于完成兼容迁移；还缺保留其他有效答案、旧C08不误作目标套餐等回归 |
| T86 | `test_purchase_completion_stops_purchase_loop` | 购买完成改active_reported/payment_intent none，去掉购买问题，G3仍blocked | 购买时点、后续交付/验收的实际续接流程 |
| T11、ENV-T34、ENV-T121 | `test_no_secret_or_inferred_sensitive_facts`、`test_credential_assignments_and_urls_rejected` | 凭据样例与敏感推断拒绝，public_export保存范围拒绝 | 不保证识别任意秘密；来源、错误、导出全链路仍须独立检查 |

CLI补充（`tests/test_interview_cli.py::InterviewCLITests`）：

| 原ID | 方法 | 子证据与缺口 |
|---|---|---|
| T55、T73、T87、T88、ENV-T69、ENV-T72 | `test_chinese_first_question_without_file_output` | 真正执行Python CLI，输出中文Q-J01且saved/action_executed为false；不是Codex原生UI/缺UI能力协商测试 |
| T16、T51、ENV-T123 | `test_saved_state_consumes_answer_and_resumes` | 显式保存后问题续接，不覆盖已有输出；不证明取消所有中间写入 |
| T52、ENV-T95 | `test_resume_requires_explicit_aliases_to_match_before_answer_or_save` | target/account不一致时不保存、不执行；不证明原生设备身份 |
| T11、T82、ENV-T34、ENV-T121 | `test_retired_question_and_secret_fail_without_echo`、`test_private_provenance_retained_only_in_explicit_saved_state`、`test_invalid_context_cannot_execute` | 秘密不进stdout/stderr，私有来源仅在明确保存状态保留，未知执行字段拒绝；不等于所有导出渠道验证 |

## B. 工作流资格与阶段门禁

实现：`skills/claude-guardian/scripts/workflow_guard.py`。测试：`tests/test_workflow_guard.py::WorkflowTests`。全部为**合成策略测试**，本模块不执行动作、不提供OS隔离。

| 原ID | 方法 | 子证据；剩余边界 |
|---|---|---|
| T90、ENV-T61、ENV-T90、ENV-T122 | `test_closed_by_default_and_no_execution`、`test_g1_g2_and_contact_gates_are_independent` | PC0 closed、executes false、enforcement_level workflow_guard；G1/G2不自动放行。仍须证明所有外部调用入口接入门禁 |
| T91、ENV-T80 | `test_neutral_consent_does_not_open_contact`、`test_client_tests_cannot_satisfy_precontact`、`test_no_authentication_cycle_and_pending_checks_reported` | 中性批准不放行Claude；阶段证据不可互换；认证后待测项保留。尚无真实客户端交接验证 |
| T07、T94、ENV-T66、ENV-T81、ENV-T124 | `test_no_handoff_on_missing_stale_future_or_other_target_evidence`、`test_ci_synthetic_and_unknown_results_cannot_open_gate`、`test_accepted_design_and_implemented_do_not_mean_validated` | unknown/skip/fail/CI/合成/陈旧证据不放行；设计/实现不能冒充native。不是Mac故障阻断测试 |
| ENV-T82 | `test_pc1_narrow_handoff_and_live_action_approval`、`test_pc1_cannot_include_login_or_authenticated_checks`、`test_payment_requires_separate_current_approval_and_review` | 精确scope单独批准；PC1拒登录/支付；支付需当前review。真人批准UI/价格披露仍未验证 |
| T94、ENV-T73、ENV-T97 | `test_cancel_denied_unknown_timeout_silence_bool_fail_closed`、`test_old_saved_approval_never_restores_permission` | 拒绝/取消/超时/沉默/布尔值不放行；存档不能复活批准。未测真实UI事件 |
| ENV-T33、ENV-T67、ENV-T83 | `test_each_binding_dimension_invalidates_evidence_and_permissions`、`test_changed_adapter_registry_during_approval_is_rejected`、`test_rebind_away_and_back_still_invalidates_approval` | 所有绑定维度变化撤销资格；审批中适配器变化/切走再切回仍失效。GUI刷新/升级须真实触发观察 |
| ENV-T67、ENV-T83 | `test_handoff_evidence_expiring_while_approval_waits_is_rejected`、`test_action_facts_expiring_while_approval_waits_are_rejected`、`test_latest_authoritative_evidence_supersedes_old_pass` | 等批准期间过期仍拒绝；较新失败/未知不被旧pass盖过。尚缺宿主证据管线 |
| ENV-T58、ENV-T64、ENV-T74 | `test_operation_version_install_product_and_platform_scope_exact`、`test_changes_require_exact_review_and_recovery`、`test_change_cannot_claim_read_risk` | scope必须完全匹配，修改须review及恢复，不能伪装read。尚未覆盖pending recommendation专例、浏览器真实策略 |
| T08、T17、T93、ENV-T68、ENV-T87 | `test_control_channel_requires_independent_rescue`、`test_irreversible_is_handoff_only` | 控制通道风险要求独立离线救援，无法逆转须交接。只校验声明，不验证实际断网终端恢复 |
| ENV-T28 | `test_rollback_preserves_later_changes` | 恢复资格要求保护后续修改标记；真实文件保护另见D，不是语义合并验证 |
| ENV-T75、ENV-T89 | `test_local_audit_cannot_hide_network_action`、`test_missing_endpoints_and_os_permission`、`test_observed_contact_revokes_and_never_erases_history` | audit不能夹带网络；probe需端点；已观察接触撤销且保留历史。未涵盖浏览器未知子请求/旧标签恢复 |

## C. 原生摘要、静态文件与控制器盘点

实现分别为 `skills/claude-guardian/scripts/guardian.py`、`clash_inventory.py`、`controller_inventory.py`、`inventory_cli.py`。测试夹具中的目标/namespace与回调不是可信宿主发现器。

| 原ID | 文件::类.方法 | 子证据；剩余边界 |
|---|---|---|
| T45、ENV-T01、ENV-T70、ENV-T95 | `tests/test_guardian.py::FileAndCLITests.test_linux_cannot_claim_mac`；`tests/test_inventory.py::InventoryTests.test_no_collectors_before_binding_and_authorization`；`tests/test_inventory_cli.py::InventoryCliTests.test_cloud_binding_blocked` | Linux/Cloud错误绑定不采集；还缺Windows/WSL、桌面用户与低权限账户的完整原生绑定（ENV-T93/94） |
| T44、ENV-T98、ENV-T103 | `tests/test_inventory.py::InventoryTests.test_fixed_commands_have_no_shell_profile_or_environment_hooks`、`test_no_foreign_commands_or_dynamic_id` | 可信固定命令、NoProfile及最小环境、动态命令拒绝；不是中文/空格/元字符所有路径或恶意PATH实际执行回归 |
| ENV-T111、ENV-T112、ENV-T113 | `tests/test_inventory.py::InventoryTests.test_mac_projection_and_scoped_not_flattened`、`test_windows_all_synthetic_fields` | scoped不压成全局；Windows用户代理与winhttp=not_collected分开；PAC仅存在性。真实服务枚举/绑定、WinHTTP采集仍缺 |
| ENV-T115 | `tests/test_inventory.py::InventoryTests.test_windows_all_synthetic_fields`、`test_unknown_is_not_false` | SKU/Windows时区ID与unknown区分；未涵盖空UI override、Windows 10.0产品映射、DST条件 |
| ENV-T122 | `tests/test_inventory.py::InventoryTests.test_expanded_native_handoff_keeps_gate_closed`；`tests/test_inventory_cli.py::CrossPlatformCliTests.test_new_workflow_remains_closed` | 盘点后门禁closed；不证明真实探测端到端调度 |
| ENV-T99 | `tests/test_clash_inventory.py::ContractTests.test_missing_dependency_structured` | 缺依赖返回结构化缺口；没有静默安装。仍缺真实无依赖设备人工出口走查 |
| ENV-T100 | `tests/test_clash_inventory.py::ParsingTests.test_duplicate_documents_aliases_tags_rejected` | 重复键、多文档、alias、YAML自定义标签等拒绝；JS扩展执行/运行来源partial专例尚缺 |
| T11、ENV-T34、ENV-T101、ENV-T121 | `tests/test_clash_inventory.py::ParsingTests.test_secrets_addresses_and_names_never_output`、`test_invalid_utf8`；`tests/test_controller_inventory.py::ControllerTests.test_errors_never_echo_raw_content` | 本地秘密哨兵不出结果，未知字段/地址/名称白名单投影；尚缺所有WebDAV/订阅来源及实际宿主stdout/stderr管线验证 |
| ENV-T102 | `tests/test_clash_inventory.py::ContractTests.test_nonlocal_material_requires_authorization`；`tests/test_clash_inventory.py::ParsingTests.test_symlink_file_and_parent_rejected` | 非本地声明/链接路径拒绝；不能当作所有网络挂载、云占位符均可识别 |
| ENV-T05、ENV-T117 | `tests/test_clash_inventory.py::ParsingTests.test_gui_settings_separate_layer`、`test_conflicts_preserve_layers`、`test_minimal_static_result_missing_is_unknown`；`tests/test_controller_inventory.py::ControllerTests.test_safe_config_projection_and_provenance` | file/gui/runtime分层，静态冲突保留，缺runtime为unknown；控制器mode与TUN分字段。未建立磁盘/API跨源原子关联 |
| ENV-T118 | `tests/test_clash_inventory.py::ParsingTests.test_secrets_addresses_and_names_never_output`；`tests/test_controller_inventory.py::ControllerTests.test_proxy_graph_projection_direct_vs_selected`、`test_raw_name_direct_does_not_imply_type` | DIRECT候选、现选与类型不混淆，名称不等于类型；完整嵌套/后备图与真实连接未测 |
| ENV-T119 | `tests/test_clash_inventory.py::ParsingTests.test_snapshot_change_discards_freshness`、`test_replacement_with_identical_bytes_is_change`；`tests/test_controller_inventory.py::ControllerTests.test_binding_changed_after_request_discards_facts` | 文件更换/变化标stale，失绑定丢facts；不证明完整跨来源revision、最多一次重采及GUI刷新 |
| ENV-T09、ENV-T105 | `tests/test_controller_inventory.py::ControllerTests.test_ports_and_identity_required`、`test_missing_or_non_boolean_attestation_blocks`、`test_approval_wait_invalidates_binding_before_any_request` | 身份不足/非真批准/批准等待时失绑定均零请求；真实监听者归属发现、手工降级指导仍缺 |
| ENV-T108、ENV-T110 | `tests/test_controller_inventory.py::ControllerTests.test_exact_paths_only` | /connections、DNS、delay、logs等在发送前拒绝；未实现另批准的单次连接过滤读取 |
| ENV-T107 | `tests/test_controller_inventory.py::LocalTransportTests.test_no_dns_no_proxy_no_credentials` | 自建127.0.0.1假服务收到精确GET，无DNS、环境代理、Cookie/Authorization；不是用户实际Mihomo绑定证明 |
| ENV-T109 | `tests/test_controller_inventory.py::ControllerTests.test_auth_and_redirect_never_retry`、`test_depth_node_and_byte_budgets`；`tests/test_controller_inventory.py::LocalTransportTests.test_redirect_is_not_followed`、`test_auth_body_not_exposed`、`test_wire_size_including_headers_is_bounded` | 不跟随/重试认证或重定向，原始错误体不输出，线缆响应有界；真实异常服务/版本仍独立 |
| ENV-T73、ENV-T123 | `tests/test_inventory_cli.py::InventoryCliTests.test_denied_and_eof_do_not_read`、`test_saved_grants_rejected`、`test_interrupt_cancels`、`test_static_fixture_no_writes` | TTY拒绝/EOF不读配置，旧grants不复用，取消、无写入；并未实现完整盘点报告保存/过期续接 |
| ENV-T121 | `tests/test_inventory_cli.py::InventoryCliTests.test_invalid_second_file_zero_collector_io`、`test_argument_errors_do_not_echo`、`test_nonfinite_json`、`test_deep_json_is_sanitized` | 整批预验证后才采集，错误不回显，非有限数/深JSON受控；不证明所有schema/导出工具覆盖 |
| ENV-T106 | `tests/test_inventory_cli.py::CrossPlatformCliTests.test_controller_is_unavailable` | 只证明CLI控制器入口不可用；**不是**Unix socket/命名管道返回LOCAL_TRANSPORT_UNSUPPORTED的精确验收 |

## D. HTTPS、回环WebRTC与事务

| 原ID | 文件::类.方法 | 子证据；剩余边界 |
|---|---|---|
| T15、ENV-T10、ENV-T13、ENV-T80 | `tests/test_network_probes.py::ContractTests.test_success_does_not_certify_browser_or_route`、`test_browser_claim_or_proxy_fallback_rejected` | IP回显成功仍path_association unknown/browser not_observed；拒冒称browser或显式代理。没有Claude DIRECT路径、MCP或真实ISP对照 |
| ENV-T12、ENV-T65 | `tests/test_network_probes.py::ContractTests.test_ipv6_and_dual_are_separate`、`test_http_failure_never_retries`、`test_bounds_timeout_and_secret_suppression` | v6/dual分开，族不符报错；跳转/429/失败unknown且一次请求；超时和4KiB限额。使用FakeTransport，无实际双栈网络 |
| ENV-T50、ENV-T75、ENV-T77 | `tests/test_network_probes.py::ContractTests.test_endpoint_and_path_consent`、`test_arbitrary_endpoints_rejected`、`test_webrtc_asset_is_opt_in_and_no_media` | 精确端点/路径批准、任意含Claude URL拒绝；页面无外部JS/fetch/媒体/TURN。未证明任意第三方检测网站子请求安全 |
| ENV-T54 | `tests/test_network_probes.py::ContractTests.test_http_failure_never_retries` | 429停止并报rate_limited_no_retry；**没有Retry-After解析断言**，不能关闭完整案例 |
| ENV-T20、ENV-T98 | `tests/test_network_probes.py::ContractTests.test_curl_security_flags_offline`；`tests/test_network_probes.py::ProcessCleanupTests.test_environment_has_no_user_injected_hooks`、`test_windows_root_is_os_api_not_environment` | curl配置禁用，代理/证书环境不继承，Windows路径取OS API；不验证真实应用旧环境来源、NO_PROXY语义或子进程采用 |
| ENV-T16、ENV-T47 | `tests/test_network_probes.py::ContractTests.test_webrtc_asset_is_opt_in_and_no_media`；`tests/test_webrtc_server.py::LifecycleTests.test_explicit_cancellation`、`test_deadline_closes_even_incomplete_request` | 页面静态unknown/12秒，回环服务超时取消关闭；浏览器ICE无候选和策略是不同层，见下述JS补充 |
| ENV-T17、ENV-T50 | `tests/test_webrtc_server.py::ServerTests.test_host_is_exact_bound_authority`、`test_cross_origin_requests_rejected`、`test_fixed_asset_only_and_security_headers` | 本地HTTP服务限固定资源/authority/origin及安全头；不是目标Claude origin的浏览器策略接受/撤回测试 |
| ENV-T61、ENV-T67 | `tests/test_transactions.py::Transactions.test_missing_authorization`、`test_all_plan_content_bound`、`test_backup_destination_bound`、`test_edit_during_confirmation_is_stale` | 批准绑定plan/目标/备份目录，确认中目标变化拒绝；纯临时POSIX文件，真实UI授权/配置适配版本未测 |
| ENV-T25 | `tests/test_transactions.py::Transactions.test_corrupt_backup_blocks_recovery`、`test_same_size_corrupt_backup_blocks_recovery` | 新增同大小回归翻转备份首字节并断言长度不变，rollback报BACKUP_CORRUPT且当前目标字节不变；这是临时POSIX文件恢复拒绝子证据，仍缺真实清理前校验/停止条件及对应原生应用验收 |
| ENV-T26 | `tests/test_transactions.py::Transactions.test_symlink_leaf_parent_backup_rejected`、`test_parent_swap_after_plan_is_rejected`、`test_hardlink_and_directory_rejected` | POSIX叶/父/备份链接、父路径替换及hardlink拒绝；不证明Windows reparse或真实应用路径 |
| ENV-T27 | `tests/test_transactions.py::Transactions.test_backup_failure_never_writes_target`、`test_post_commit_journal_failure_retains_prepared_recovery`、`test_cancel_immediately_before_commit_retains_backup` | 故障时不误写或保留恢复记录，取消前保备份；不是多动作清理已做/未做/不可逆清单验收 |
| ENV-T28 | `tests/test_transactions.py::Transactions.test_rollback_conflict_preserves_later_edit`、`test_metadata_change_blocks_rollback` | 后续字节/元数据变化拒绝rollback并保留用户编辑；未实现字段级语义恢复合并 |
| ENV-T68 | `tests/test_transactions.py::Transactions.test_roundtrip_and_recovery_records`、`test_expired_plan_still_allows_independently_authorized_recovery` | 私有备份/receipt、正常恢复及过期计划独立批准恢复；network_effect not_tested；未证明Agent断连普通终端CLI可用 |
| ENV-T60 | `tests/test_transactions.py::Transactions.test_duplicate_apply_fails_closed` | 重复apply拒绝；**拒绝重复不是完整幂等复用**，尚缺相同任务无变化返回有效既有状态 |
| ENV-T26、ENV-T102 | `tests/test_windows_transactions.py::WindowsPlans.test_unsafe_metadata_blocks_data_read_and_closes_handles`；`tests/test_windows_transactions.py::NativeABIContracts.test_reparse_hydration_and_unknown_attributes_rejected`、`test_disk_locality_fails_closed` | FakeAPI与mock ABI拒不安全metadata/reparse/召回/非本地卷；原生测试另列，不能跨平台推广 |
| ENV-T61、ENV-T124 | `tests/test_windows_transactions.py::WindowsPlans.test_mutations_never_call_approval_or_api_even_for_approved_plan`、`test_capability_report_cannot_enable_writes` | Windows apply/verify/rollback均明确UNIMPLEMENTED，且不调用API/批准；不是Windows写入/恢复能力 |

### 非unittest与条件原生测试，单列而不混计

- `tests/webrtc-lifecycle.cjs` 是Node合成DOM/RTCPeerConnection夹具（非真实浏览器）。直接断言未同意/非回环不创建peer，完成/超时/取消/pagehide关闭peer及channel，地址不输出，候选最多128，701/超时仍unknown。关联ENV-T16/47/50的部分子证据；没有真实STUN包、mDNS全分类、原生浏览器策略或UDP出口观察。
- `tests/test_windows_transactions.py::NativeWindowsSmoke.test_native_ads_and_hardlinks_rejected_before_data_read`、`test_native_junction_ancestor_rejected_before_data_read`、`test_native_handles_closed_after_injected_metadata_denial`、`test_temporary_file_plan_and_mutation_rejection` 需Windows原生且 `GUARDIAN_TEST_WINDOWS_TRANSACTION_BOUNDARY=1`。存在这些方法不等于运行过；即使通过也仅支持临时文件读计划边界（ENV-T26/102子项），不支持Windows实际清理或rollback。
- `tests/test_transactions.py::Transactions.test_native_temporary_file_xattr_presence_and_refusal` 是条件平台临时文件检查；`ExtendedAttributePlatformTests` 的Darwin ABI测试主要使用mock。不可把Linux上的mock通过写成Mac真实xattr验证。

## E. 教程与来源打包（M01—M14 / VAL-08）

| 相关ID/模块 | 文件::类.方法 | 子证据与未覆盖内容 |
|---|---|---|
| T20、T21、T27、T70 / M08、M09 | `tests/test_guides.py::GuidanceContracts.test_independent_route_lifecycles_have_ordered_cards`、`test_routes_preserve_free_tools_and_rescue_constraints` | 三路线卡片存在/顺序正确，PC0/PC1/恢复/批准、免费工具与救援关键词存在；不是具体操作正确性、部署可完成性或用户走查 |
| T37、T49、T86 / M03 | `tests/test_guides.py::GuidanceContracts.test_account_cards_cover_all_channels_and_post_purchase` | 渠道/后购买卡片及“不先买卡”“本人完成支付”等字符串存在；不验证官方现行支付规则、总价、前提决策树 |
| T03、T10、T18 / M11、M12 | `tests/test_guides.py::GuidanceContracts.test_integrations_and_incidents_have_full_cards` | 集成、事故卡片及响应来源/事实模板词存在；不验证403/拒付/KYC分流与草稿事实准确性 |
| T48 | `tests/test_guides.py::GuidanceContracts.test_incident_containment_distinguishes_agent_and_user_tasks` | 紧急说明区分助手未发重试与需批准停止的用户任务；不证明真实事故执行 |
| T11、ENV-T123 | `tests/test_guides.py::GuidanceContracts.test_evidence_export_requires_approval_for_local_and_remote_targets` | 文本要求内容/精确目的地批准（本地和远端）；文档断言不是实际写文件授权门禁 |
| T13、T71、T89 / M14 | `tests/test_guides.py::GuidanceContracts.test_historical_sources_are_not_current_claims`、`test_contact_and_evidence_boundaries_are_explicit` | 历史/官方/未核验与PC0限制文字存在；不是来源冲突逐条判定或当前官方链接验证 |
| M14 / VAL-08；T11仅相关子项 | `tests/test_source_bundle.py::SourceBundleTests.test_exact_manifest_and_hashes` | 精确9个来源ID、文件/附件hash、路径限制、S06原始与分发hash不同且有changes；不证明来源去重(T09)、许可证可分发或论断准确 |
| M14 / VAL-08；T11仅相关子项 | `tests/test_source_bundle.py::SourceBundleTests.test_package_reproducible_and_unlisted_files_excluded`、`test_tampered_source_rejected` | 两次同环境zip相等、固定元数据、未列私有哨兵文件不入包、篡改来源无产物；不是全仓秘密扫描，也不自行证明跨OS包一致 |

## F. 全218项的未关闭范围与下一步

以上仅建立部分子证据，**218项都仍需逐案例结果或有依据的不适用结论**。这里未给整案例pass，也未把“没有对应测试”误写成“完全没有文档/实现”。精确未映射ID清单见下方；其余ID可按表中方法定位，但状态仍是部分。

最重要的未关闭能力：

1. 原生绑定/采集：47字段与26采集规格逐字段对照，桌面用户/HKCU、WSL命名空间、Rosetta/硬件架构、真实网络服务、多个Clash实例选择和监听者绑定。测试中的绑定字符串不能代替可信采集。
2. DNS/STUN：当前 `test_network_probes.py` 测HTTPS IP回显与进程清理，**没有原生DNS/STUN解析器单测**。页面使用RTCPeerConnection不等于实现/验证ENV §20.6的事务ID、来源、XOR-MAPPED IPv4/6与最多3发送协议要求。
3. 写入适配：Clash四类模板/规则语义/GUI回写刷新、浏览器原生策略、launcher子进程采用、时区/语言写入、C0—C4精确清理、免费故障阻断技术与恢复均不能由通用文件事务关闭。
4. 访谈全语义：问题登记数量、出现某前缀、文档含关键词远弱于原案例全部条件；旧画像迁移、自然语言多字段吸收、接受默认、各支付前提、完整Codex UI/取消路径需专例。
5. 发行：来源许可证/当前官方内容核验、秘密全链路、升级撤回与操作级能力矩阵需要独立证据。原始来源文档历史“仅Spec”声明不应改写；当前实现状态由跟踪/验证文档说明。

### 不依赖用户Mac即可实施的优先任务

1. **补精确回归缺口**：ENV-T54 Retry-After有界解析/未知值、T82旧画像保留有效字段且废弃C07/旧C08、T53接受默认、T81多字段导入。每项写明输入、预期与未执行动作，不能仅增加数量。
2. **完善离线事实/版本契约**：Windows SKU/UI空override/DST、WSL/用户上下文、Mac进程/硬件架构区分、控制器多实例选择与revision变化的合成样例；真实绑定适配器仍待相应平台。
3. **独立DNS/STUN协议底座**：先做二进制解析、事务/来源/长度/族拒绝、预算与取消的伪传输测试；未批准公开端点前不发真实请求。不得让新协议自动进入PC1。
4. **ENV-06离线处理计划/规则编译器**：从精确事实到条件计划、组织/救援优先级、nameserver-policy语义、DIRECT嵌套、不可表达格式报错；先验证不产生apply/网络，不把临时文件成功当Mihomo接受。
5. **普通终端恢复与故障注入**：针对POSIX临时文件写独立进程恢复、日志中断/权限/后续修改回归；Windows继续明确读计划边界。实际系统ACL/应用锁/控制通道断连留待各自平台授权验证。
6. **建立逐案例执行记录**：固定commit/构建hash、方法、输入/预期/实际、平台、跳过原因、证据类型。CI原生临时测试与用户设备真实软件/流程验收分栏，避免再次由总数推断完成。

未映射清单由下述静态核对维护；未映射通常表示没有足够精确的断言，不表示可删需求：

- 主规范：T04、T05、T06、T09、T12、T14、T23、T25、T28、T31、T32、T33、T39、T40、T42、T50、T53、T65、T67、T79、T85
- ENV：ENV-T03、ENV-T04、ENV-T06、ENV-T07、ENV-T08、ENV-T11、ENV-T14、ENV-T15、ENV-T18、ENV-T19、ENV-T21、ENV-T22、ENV-T23、ENV-T24、ENV-T29、ENV-T30、ENV-T31、ENV-T32、ENV-T35、ENV-T37、ENV-T38、ENV-T39、ENV-T40、ENV-T41、ENV-T42、ENV-T43、ENV-T44、ENV-T45、ENV-T46、ENV-T48、ENV-T49、ENV-T51、ENV-T52、ENV-T53、ENV-T55、ENV-T56、ENV-T57、ENV-T59、ENV-T62、ENV-T63、ENV-T71、ENV-T76、ENV-T78、ENV-T79、ENV-T84、ENV-T86、ENV-T88、ENV-T91、ENV-T93、ENV-T94、ENV-T104、ENV-T114、ENV-T116、ENV-T120

复核方法：从本文件表格首列提取原ID（含范围），与跟踪表218项比较；从测试AST核对文中方法名存在。本静态核对不执行测试，也不生成通过率。后续新增测试应更新相应行的实际断言/限制，再由执行证据决定状态。
