# 智御｜完整 AI 上下文与工程冻结基线

版本：2026.09.12-ai.5

本文件自动生成。全部示例为合成数据；平台功能、性能与 A01–A15 尚未因本资料包而得到验证。


## 导航

# START HERE — 智御 ai.5 Engineering Freeze

这是“智御——网络安全自主决策与持续验证平台”的工程冻结上下文包。当前版本 **2026.09.12-ai.5**。

## 读取顺序

1. `PROJECT_STATE.yaml`：当前唯一状态与冻结规则。
2. `docs/01_项目定位与总体架构.md`：功能架构与部署平面。
3. `docs/10_ai5工程冻结与实现入口.md`：ai.5 新增的工程契约和开工顺序。
4. `contracts/models.py`：API/DB/Worker/AI 的权威数据契约。
5. `contracts/state_machines.json`：Incident / Task / Action 状态迁移。
6. `docs/06_V1场景与开发接口.md`：第一条确定性闭环与 API 草案。
7. `examples/`：全部是 `SYNTHETIC` 设计 fixtures，不是实测结果。

## 当前里程碑

`M0_engineering_freeze -> M1_infrastructure -> M2_deterministic_closed_loop -> M3_ai_planner -> M4_acceptance`

## 不可误读

- ai.5 通过资料包自检，不代表真实平台通过 A01–A15。
- 主动安全能力仅限自有/教学/隔离或明确授权环境。
- LLM 不直接执行高权限动作，也不持有真实 Credential。
- ai.5 后不因“新框架更酷”修改核心 Contract；必须由实现/测试/安全/实测约束驱动。


## 机器可读状态

```yaml
meta:
  project_id: zhiyu
  name: 智御——网络安全自主决策与持续验证平台
  version: 2026.09.12-ai.5
  updated_at: '2026-09-12'
  deliverable_type: engineering_freeze_context_package
  implementation_status: project_skeleton_started_after_contract_freeze
  platform_test_status: not_run
  current_milestone: M0_engineering_freeze
authority:
  metadata_and_decisions: PROJECT_STATE.yaml
  object_contracts: contracts/models.py
  state_transitions: contracts/state_machines.json
  behavior_design: docs/
  generated_reading_copy: 智御_AI_CONTEXT_v2026.09.12_ai.5.md
  rule: generated_files_are_not_independent_sources_of_truth
positioning:
  one_sentence: 现有安全设备之上的自主安全决策与持续验证中枢。
  main_product_target: 中小企业或部门级私有网络
  initial_validation_environment: 隔离授权靶场
  core_loop:
  - event
  - incident
  - environment_state
  - context
  - ai_plan
  - task_graph
  - capability
  - authorization
  - action
  - verification
  - state_update_or_bounded_replan
architecture:
  functional_layers:
  - sensing_adapters
  - event_intelligence
  - environment_state_memory
  - context_ai_decision
  - orchestration
  - policy_risk
  - secure_execution
  - continuous_verification
  deployment_planes:
  - control_decision
  - data_sensor
  - response_execution
  - isolated_validation
  - trust_governance
  cross_cutting:
  - environment_policy
  - identity_secrets
  - data_egress
  - sensor_health_coverage
  - evidence_provenance
  - versioning
  - resource_budget
  - audit_trace
  - dashboard
  core_os: linux
  access: browser_and_api
  canonical_state: postgresql
  graph_role: optional_rebuildable_projection
invariants:
- llm_has_no_direct_privileged_execution_or_credentials
- all_active_validation_requires_explicit_scope_and_authorization
- high_business_impact_and_r5_require_human_approval
- load_mode_never_expands_permissions
- model_self_confidence_is_not_a_calibrated_probability
- origin_authentication_does_not_prove_content_truth
- duplicate_provenance_is_not_independent_evidence
- approval_binds_exact_action_digest_and_expiry
- preconditions_and_authorization_are_rechecked_before_execution
- unknown_action_result_requires_reconciliation_before_retry
- compensation_only_changes_resources_owned_by_the_action
- containment_pass_is_not_remediation_or_incident_closure
- verification_checks_security_business_and_observation
- insufficient_observation_cannot_produce_a_false_pass
- validation_run_tags_must_come_from_trusted_registration
- replan_and_recovery_budgets_are_bounded_and_separate
- raw_retention_is_bounded_and_loss_is_explicit
- no_new_state_changing_action_without_durable_intent_and_audit
- local_only_or_air_gapped_never_falls_back_to_cloud
- underlying_security_controls_survive_ai_failure
- examples_are_synthetic_and_not_platform_test_results
third_party:
  v1_primary:
  - wazuh
  - suricata
  - nuclei
  v1_capability_roles:
  - template_check
  - scoped_response_adapter
  - independent_security_and_business_probes
  optional_or_v2:
  - atomic_red_team
  - caldera
  - strix
  - zeek
  - opencti
  - graph_projection
  reference_only:
  - pentagi
  - anthropic_cybersecurity_skills
  - openaev
  infrastructure_candidates:
  - temporal_class
  - opa_class
  - spiffe_spire_class
  - vault_kms_class
  - durable_event_stream
  - clickhouse_class
  - s3_compatible_store
  - kata_or_firecracker_or_kvm
v1:
  scenario_id: SCN-LAB-AUTH-01
  scenario_status: selected_design_baseline_not_implemented
  secondary_scenario: SCN-LAB-AUTH-02_remediation_extension_design
  default_backend: python_3_12_fastapi_pydantic
  default_state: postgresql_jsonb
  default_task_durability: postgres_task_table_transactional_outbox_and_leases
  default_frontend: react_typescript_vite
  default_dev_runtime: isolated_linux_vms_with_compose_for_control_services
  default_graph_ui: choose_one_react_flow_or_cytoscape_when_needed
  default_model: replaceable_single_model_gateway_final_model_unknown
  must_have:
  - two_real_independent_event_sources
  - event_entity_provenance_and_time_normalization
  - incident_state_and_minimal_context
  - validated_structured_plan_and_dag
  - three_real_capability_roles
  - deterministic_scope_policy_and_minimal_iam
  - approval_binding_expiry_and_execution_recheck
  - durable_intent_idempotency_and_unknown_reconciliation
  - owned_ttl_cleanup_with_local_recovery_path
  - independent_three_check_verification
  - incident_containment_remediation_closure_distinction
  - bounded_replan_and_reserved_recovery_capacity
  - trace_and_versioned_reproducible_scenario
  non_goals:
  - enterprise_ha
  - multi_tenant_mssp
  - default_multi_agent
  - full_digital_twin
  - full_graph_db
  - online_learning
  - dozens_of_tools
  - public_unscoped_attack
  - ot_production_control
  - full_windows_ad_chain_in_first_demo
  contract_freeze: ai.5
  implementation_track: M1_infrastructure_then_M2_deterministic_closed_loop_then_M3_ai
decision_log:
- id: D01
  decision: preserve_eight_layers_five_planes
  status: active
- id: D02
  decision: external_state_memory_instead_of_generic_knowledge_base
  status: active
- id: D03
  decision: strix_executor_pentagi_reference
  status: active
- id: D04
  decision: independent_security_business_observation_verification
  status: active_ai4
- id: D05
  decision: approval_digest_expiry_and_preexecution_recheck
  status: active_ai4
- id: D06
  decision: action_unknown_reconcile_and_owned_compensation
  status: active_ai4
- id: D07
  decision: orthogonal_environment_dimensions
  status: active_ai4
- id: D08
  decision: first_scenario_auth_anomaly_containment
  status: design_default_ai4
- id: D09
  decision: atomic_caldera_not_required_for_first_demo
  status: active_ai4
- id: D10
  decision: durable_v1_tasks_no_memory_only_queue
  status: active_ai4
- id: D11
  decision: modular_authoritative_sources_generated_single_file
  status: active_ai4
- id: D12
  decision: deterministic_baseline_to_measure_ai_increment
  status: active_ai4
- id: D13
  decision: generic_resource_ref_and_scope_for_cross_platform_targets
  status: active_ai5
- id: D14
  decision: normalized_event_cloudevents_like_envelope_with_security_semantics_and_ocsf_mapping_path
  status: active_ai5
- id: D15
  decision: event_group_and_correlation_decision_are_first_class_objects
  status: active_ai5
- id: D16
  decision: verification_rules_are_machine_executable_specs
  status: active_ai5
- id: D17
  decision: authorization_decision_preserves_full_input_context_snapshot
  status: active_ai5
- id: D18
  decision: model_invocations_are_versioned_model_run_objects
  status: active_ai5
- id: D19
  decision: capability_definition_and_dynamic_health_are_separate
  status: active_ai5
unknowns:
- actual_repository_and_implemented_modules
- team_members_roles_and_capacity
- confirmed_server_ram_gpu_and_virtualization
- competition_name_deadline_and_required_template
- final_model_provider_version_and_measured_quality
- dependency_versions_licenses_and_compatibility
- measured_throughput_latency_cost_and_recovery
- real_pilot_assets_scope_egress_and_approval_owner
- customers_market_pricing_and_ip_status
next_steps:
- initialize_real_repository_from_ai5_contracts
- build_M1_linux_control_plane_postgresql_migrations_and_lab_topology
- implement_M2_deterministic_event_to_verification_closed_loop
- run_negative_and_recovery_cases_before_ai
- integrate_M3_model_gateway_and_structured_planner_through_same_contracts
- run_M4_acceptance_A01_A15_and_G1_vs_G2_experiments
engineering_freeze:
  status: FROZEN_FOR_IMPLEMENTATION
  freeze_scope:
  - resource_and_scope_semantics
  - normalized_event_semantics
  - event_correlation_contracts
  - incident_task_action_lifecycle
  - verification_spec
  - authorization_context
  - model_run
  - capability_definition_vs_health
  change_gate:
  - implementation_finding
  - test_evidence
  - security_finding
  - measured_performance_bottleneck
  - third_party_constraint_mismatch
  rule: new frameworks or aesthetic preference alone do not justify contract changes
```


---

模块来源：`docs/01_项目定位与总体架构.md`

# 项目定位与总体架构

## 1. 定位与价值

项目名：智御——网络安全自主决策与持续验证平台。

项目把现有防火墙、EDR、IDS、终端日志和验证工具连接成可解释的决策闭环。主要产品目标是已有一定安全设备基础的中小企业或部门级私有网络；高校授权靶场是首个研发与比赛验证环境。平台服务安全分析人员、审批人员和环境管理员，帮助他们关联重复告警、核对证据、选择处置、控制影响范围并验证效果。

平台不承诺精确预测攻击者下一步；候选路径只能按证据和影响排序。底层检测设备的检测能力、模板库和第三方攻击模拟能力必须明确归属于原项目。当前没有可引用的用户访谈、客户、销售、专利、团队或性能数据。

## 2. 保持八层功能架构

| 层 | 输入 | 责任 | 输出与边界 |
|---|---|---|---|
| 1 感知与适配 | 设备、网络、主机和资产记录 | 解析、来源标记、规范化；采集责任归 Adapter | NormalizedEvent、SensorHealth；不执行自动响应 |
| 2 事件智能 | 规范化事件 | 去重、窗口聚合、实体关联、风险排序 | Incident、证据引用；不让每条日志调用模型 |
| 3 环境状态与记忆 | 资产观测、事件、动作、验证 | 保存有版本与有效期的环境状态、工作记忆、历史记忆 | 可回溯状态；推断与观测分离 |
| 4 上下文与 AI 决策 | 当前任务、授权可见证据、能力目录 | 最小上下文、候选解释、计划和批评 | 结构化 Plan；无凭据、无执行权 |
| 5 自主编排 | 合法 Plan、资源与依赖 | 任务图、优先级、预算、路由、取消 | 可调度 Task；不自行扩大权限 |
| 6 策略与风险 | 环境、目标、身份、证据、能力和动作 | 确定性授权、审批、Scope、业务影响检查 | 有期限的授权决定；负载不能放宽策略 |
| 7 安全执行 | 已授权结构化动作 | 凭据代理、站点适配、幂等、状态核对、补偿 | 执行证据；执行成功不自证安全有效 |
| 8 持续验证 | 验证目标、独立探针、业务与观测证据 | 检验安全效果、业务可用性、覆盖与时效 | PASS/FAIL/INCONCLUSIVE、残余风险、后续任务 |

所有层共用：EnvironmentProfile、身份与秘密管理、数据出域、传感器健康、版本溯源、预算、审计与 Trace、Dashboard。横向能力完整呈现，不再保留“仅两个横向体系”的旧摘要。

## 3. 五个部署平面

| 平面 | 承载内容 | 信任边界 |
|---|---|---|
| 控制与决策 | API、事件处理、状态、模型网关、编排、策略、验证控制器 | 默认 Linux；不持全网目标管理会话 |
| 感知与数据 | Wazuh/EDR、Suricata、日志/API、按需 eBPF | 跨 OS；有身份不代表数据内容绝对可信 |
| 响应与执行 | 站点 Action Gateway、设备适配器、凭据代理 | 只接收经授权的具体动作，执行前再检查 |
| 隔离验证 | Linux 工具环境、Windows 临时 VM、隔离目标和业务探针 | Scope、网络与权限同时限制；目标内执行需单独授权 |
| 信任与治理 | 身份、策略、秘密、审计、出域、供应链、时间与恢复 | 横跨各平面，不等于额外开发一个大平台 |

功能层描述职责，部署平面描述位置与隔离。V1 可在多个隔离 VM 内合并低风险服务；企业部署按故障域拆开。八层不等于八个微服务，五平面也不等于固定五台物理机。

## 4. 三类运行闭环

| 时机 | 触发 | 输出 |
|---|---|---|
| 持续检查 | 已授权的定时场景或变更 | 控制有效性、覆盖缺口、版本化复测记录 |
| 事件处置 | 多源 Incident、关键状态变化 | 证据计划、受控响应、遏制/修复/关闭状态 |
| 事后复盘 | 处置完成、人工复核 | 可复现场景、规则改进建议、历史记忆；禁止未经审核直接学习生产策略 |

AI 计划执行和周期验证共享 Capability、Scope、Action 与 Evidence 契约。周期任务并不天然获得更高权限。

## 5. 必须自研的核心与可复用基础设施

自研重点为事件关联策略、环境状态语义、上下文取舍、结构化决策契约、任务优先级和预算策略、能力路由、风险授权规则、动作协调、独立验证判据和证据链。统一事件语义可按需映射现有标准，不要求从零发明所有日志字段。

数据库、队列、身份、秘密管理、工作流引擎、图渲染和安全扫描工具可复用成熟项目。自研边界指的是项目拥有这些行为定义及组合逻辑，不要求重复实现 PostgreSQL、Temporal、OPA 或凭据存储引擎。

五个待实验验证的创新主张：环境状态驱动决策、保留关键证据的事件压缩、资源与风险共同约束的编排、证据约束的分级自主、同时检查安全与业务的验证闭环。使用先进组件本身不是创新证据。

## 6. 明确阶段

V1：双源真实接入、一个完整场景、至少三种实际能力、结构化规划、确定性授权、可核对动作、三态验证与全链路展示。

V2：更多场景、Windows/AD 验证、Atomic/CALDERA、可选 Strix/Zeek/OpenCTI、图投影与跨环境能力扩展。

V3：多站点、企业 HA/DR、多租户、企业身份治理、离线交付、按需云与特殊资产适配。企业完整版是设计目标，不能被写成当前已支持的产品能力。


---

模块来源：`docs/02_事件状态与上下文.md`

# 事件、环境状态与模型上下文

## 1. 事件工程

Adapter 负责来源协议到 NormalizedEvent 的转换；Event Intelligence 检查规范化结果，再去重、聚合、关联与评分。所有时间用带时区的 UTC，保留 source_timestamp、ingested_at、时钟可信状态和解析版本。

V1 按环境、传感器及稳定实体 ID 分区。去重键包含来源事件 ID或原始记录指纹；聚合键包含目标实体、事件类型、规则、来源上下文和时间窗。不能用“相同文本”跨所有主机合并。一个 IP 只是时间范围内的地址绑定，NAT、DHCP、代理和容器重建不能被当作同一资产的永久身份。

关联输出同时保留事件数量、首次/末次时间、代表证据、异常分支、聚合规则版本。低频但高影响事件不得因数量小被常见事件吞并。迟到事件按可配置 watermark 接纳或补正 Incident，补正生成新状态版本；已经发生的动作记录不随补正被改写。

源头优先级是输入信号；最终 P0–P4 由服务端结合已登记资产等级、规则和证据计算。不能允许任意日志中的 severity=P0 独占紧急队列。

## 2. 来源、血缘与可信度

NormalizedEvent、Evidence 都保存 origin_event_id、provenance_group、collector_id。Wazuh 转发同一条 Suricata 告警时，来源工具不同也属于同一证据血缘。真实的网络观测与应用审计可以提供互补证据，但仍需核对它们观察的是同一次行为。

信任拆成三件事：谁发送了记录、记录是否被改动、记录中的结论是否可信。认证与哈希只能帮助前两者，不能证明被攻陷主机发出的内容为真。设备输出也是“观测或来源声明”，状态中的推断必须明确标注。

模型引用 Evidence 前，由代码检查 ID 存在、属于当前环境与授权范围、时效未失效，并保留相反证据。历史摘要的高置信度不得在多次摘要后递增。人工确认记录身份和理由；不能单凭人工按钮把未知观测自动变成技术验证通过。

## 3. 环境状态与三层记忆

PostgreSQL 是资产、关系、Incident、Action、授权与验证的事务主库。每次状态更新使用 state_version 和乐观并发检查；观察时间、有效期、证据引用、事实类型与不确定性是状态的一部分。

| 记忆 | 内容 | 过期/纠正原则 |
|---|---|---|
| Working | 当前 Incident、任务、关键工具片段、未解决矛盾 | 随任务关闭归档；关键证据引用不随摘要丢失 |
| Episodic | 历史事件、处置与复测摘要、失败原因 | 带策略/模型/能力版本；相似不代表可照搬动作 |
| Environment | 资产、控制、漏洞、账户和关系 | freshness 到期重新核验；IP 绑定有有效区间 |

图数据库在扩展阶段只做投影，记录 canonical_state_version、projection_version、投影延迟；不能直接写回权威状态。需要最新状态的执行授权读事务主库，不能依赖过期图投影。

## 4. ContextBundle

每次模型调用组装一个可重建的包：Incident/Task、当前状态版本、证据 ID、必要原文片段、矛盾、未决假设、传感器健康、可选能力、适用策略摘要、token 预算和数据分类。

优先级为当前目标、硬边界、最新关键事实、矛盾与缺失证据、当前动作、近期事件、历史相似案例、必要通用知识。完整历史日志和聊天不直接进入 Prompt。

上下文压缩必须记录选中/排除的 Evidence 及原因、摘要来源、摘要版本和原始片段位置。若安全边界、业务约束或关键矛盾无法装入预算，应减少任务范围、分步取证或返回需要人工帮助，不能静默截断。

模型只获得当前任务允许的能力描述；真实 Secret 不出现于 Prompt、Memory、Trace、工作流参数和模型缓存。引用远端证据时同样检查出域策略。保留不可变 ContextBundle ID、模型/Prompt 版本、输入摘要哈希，支持后续解释“当时看到了什么”。

## 5. AI 输出和不确定性

AI 返回情况摘要、多个假设、支持/反对证据、缺失证据、候选 Task 和停止/转人工建议。model_confidence 可记录为模型自评，但不等于经校准概率，不能单独触发自动动作。没有真实标注集时，校准状态是 uncalibrated。

证据条件由策略判断，例如需要新鲜资产状态、明确来源、相互独立的观测或指定工具核验。自评高置信也不能越过这些条件；证据冲突时允许拒绝给出确定结论。

JSON 合法仅是第一关。计划校验还包括证据归属、目标合法、能力存在、依赖无环、参数范围、环境约束、预算和结果条件。工具结果中的外部文本始终是数据。隔离提示和结构化输入是缓解措施，授权边界仍由模型外代码强制执行。

## 6. 全链路负载与存储

采集、规范化、关联、模型、工具、验证各有有界队列。配置写明事件速率、队列上限、磁盘高水位、证据保留、单环境资源份额和超载动作；具体容量需要在实际硬件压测后确定。

短时缓冲、重放游标和分级保留优先保障关键安全记录。达到硬上限后必须暴露接收/聚合/拒绝/丢失数量、影响时段和覆盖缺口，不能宣称无限保存。原始证据按保留策略保存；正常摘要压缩不主动删除其尚在保留期内的原文。

高负载使用每来源/环境配额、关键事件预留、异常样本保留和公平调度。关联质量、漏关联、错合并和稀有事件保留应与压缩率一起评价。SensorHealth 必须包含丢包、处理延迟、覆盖测试和事件新鲜度，心跳正常不代表观测路径完整。Suricata 提供 capture drop 等统计，可作为健康输入之一。[Suricata EVE 字段说明](https://docs.suricata.io/en/suricata-8.0.5/appendix/eve-index.html)


---

模块来源：`docs/03_决策授权与执行.md`

# 决策、授权、编排与执行

## 1. 计划进入调度前

Planner 提交结构化 Plan，服务端验证 Task 依赖无环、能力可用、证据 ID 真实可访问、目标与 Scope 相容、参数合法、预期结果明确。Planner/Critic 可以共享一个模型顺序调用；V1 不默认开多个 Agent。Critic 是建议审查，不能代替代码校验或 Risk Gate。

Task 必须显式携带 target_ids、scope_id、能力版本与参数；不可依赖“上一轮模型应该还记得目标”。参数按注册能力的 input_schema 检查。operation_kind 来自受管理的 CapabilityManifest，不能由 Planner 把状态变更重新标成只读来降低要求。

Scheduler 决定何时执行；Router 决定适配器和执行位置；Risk Gate 决定能否执行；Action Gateway 保证最终参数、授权和执行凭据绑定。简单核验优先用模板或确定性探针，复杂任务才评估 Strix。第三方 Agent 的子任务同样受智御预算和目标约束，其内部自主扩展不能形成第二套无约束控制器。

## 2. 风险维度和权限模式

事件紧急程度 P0–P4 与动作风险 R0–R5 独立。动作风险由能力基准、目标关键性、参数、权限、可逆性、爆炸半径和业务依赖共同确定，不能用“工具名字”固定判级。R0 读取，R1 被动分析，R2 低影响主动检查或范围很小的可恢复动作，R3 有限影响验证/处置，R4 高影响模拟或变更，R5 破坏性或核心业务影响。该解释是 ai.4 对旧版只按工具类别划级的收敛。

| 模式 | 权限 |
|---|---|
| OBSERVE_ONLY | 仅经授权读取、分析、报告；禁止主动探测与状态变更 |
| ASSISTED | 读取/分析按策略执行；主动测试与状态变更需具体人工批准 |
| CONTROLLED_AUTONOMY | 预授权低风险动作自动；超阈值转人工 |
| VALIDATION | 限定验证域的预授权测试；不是绕过高影响审批的特权模式 |

active_validation、capability_allowlist、network_scope 仍单独生效。运行中的生产响应与验证任务可分别绑定不同 Scope/配置，不用切换全平台模式来做测试。LoadMode=NORMAL/HIGH_LOAD/EMERGENCY 只决定资源分配，不能放宽任何权限。

高业务影响和 R5 动作始终要求人工审批；R5 不纳入 V1，概念完整版也只在明确允许的隔离实验域考虑执行。任何自动化阈值不能覆盖这一硬规则。

## 3. 确定性授权契约

授权顺序：身份与环境 → 目标身份/Scope → Capability/版本 → 参数与前置状态 → 证据质量/观测 → 业务影响 → 预算 → 自动化阈值 → 所需人工审批。返回 ALLOW、DENY、REQUIRE_APPROVAL 或 DOWNGRADE，以及理由、策略版本和有效期。DOWNGRADE 产生新的候选动作，不能在不留痕的情况下改变已批动作。

ActionRequest 仅是请求，不含可自授的 approval_required、assessed_risk 或 allow 字段。AuthorizationDecision 才保存服务端计算的风险与结果。ALLOW 也不是无限期通行证：执行前重查环境未退休、Scope 未撤销、批准未过期、状态前置条件仍满足、能力版本未变化。

生产/测试的高影响目标、关键网络出口、管理通道和共享依赖可以配置永久拒绝或强制审批。R0 查询同样要有数据读取权限和查询范围；低风险不意味着无权限控制。

## 4. ApprovalRecord 与动作绑定

ApprovalRecord 记录审批人、角色、理由、决策时间、expires_at、action_id、action_digest。摘要涵盖目标、参数、Scope、Capability 版本、环境/策略版本、证据引用、前置条件、TTL 和动作有效期。演示摘要序列化采用包内明确的 JSON 排序规则；不是数字签名，也不能替代审批人身份认证。生产中摘要和批准记录须受数据库权限、审计或签名保护。

参数变更生成新动作/摘要并重新授权；已批准记录不可就地覆盖。审批被拒绝只改变动作/任务状态，不证明 Incident 已被遏制。预授权策略版本与人工审批记录分别存储，不能伪造一个“系统审批人”混淆两者。

若审批等待跨越状态版本改变，重新读取受影响前置条件。无关状态更新可按明确定义的字段版本策略判定仍有效；目标、Scope、策略或业务依赖变化必须重新评估。初版使用保守的整体版本检查。

## 5. ActionGateway 的提交协议

1. 规范化目标身份与参数，生成不可变请求摘要和幂等键。
2. 在事务库保存动作意图、授权和审计记录；用 outbox 或事务任务领取避免“数据库保存了但任务丢失”。
3. 对动作实际修改的资源加互斥租约。防火墙规则冲突按网关/规则/受影响集合协调，不只按资产 ID 加锁。
4. 执行器领取有代次的执行租约，检查授权有效期和 kill switch，再通过短时最小权限凭据调用设备。
5. 保存执行回执或结果未知，随后执行独立验证。
6. 以查询真实状态的核对流程恢复中断任务；释放租约并清理专属资源。

V1 的 PostgreSQL 持久 Task 表、事务 outbox 和租约即可承载必要语义；不能用纯内存 asyncio 队列保存唯一任务状态。Redis 可以辅助排队但不做动作事实主库。完整版按需要采用 Durable Workflow 与高吞吐事件流，二者职责保持分离。

## 6. 重试、未知结果与补偿

| 情形 | 状态与处理 |
|---|---|
| 执行器明确拒绝且未修改 | FAILED 或 DENIED，记录原因 |
| 调用后超时，是否已修改不明 | EXECUTION_UNKNOWN → RECONCILING；先查询实际状态 |
| 同一请求重复投递 | 保持同一 action_id/idempotency_key，返回已有结果或核对，不新建重复规则 |
| 部分步骤成功 | 保存每步回执和实际效果，按预授权补偿处理；禁止一键重放全部副作用 |
| 旧 Worker 在租约过期后恢复 | 检查 fencing generation，拒绝旧代次写操作；不能假设 Redis 锁消除了旧 Worker |
| 无法确认真实状态 | NEEDS_MANUAL，暂停相冲突的新动作，不虚构 FAILED/ROLLED_BACK |

Temporal 的工作流恢复不等于外部副作用恰好执行一次；重试和回报前崩溃都要求调用端与设备适配器处理幂等和核对。[Temporal Activity 定义](https://docs.temporal.io/activity-definition)

每个变更具有 ownership_tag、原始状态引用、设备规则 ID、TTL 执行位置和 cleanup policy。删除/恢复只作用于本动作拥有的变化；管理员后续变更、其他有效 Incident 持有的封禁和共享规则不能被旧补偿覆盖。TTL 到期可能让临时控制失效，应产生复核任务；不能自动声称根因已消除。

租约代次必须在真正写设备的边界检查。对于不支持设备侧 fencing 的接口，站点序列化、短时凭据、设备幂等标识和核对只能组合降低重复/并发风险，不能声称可以撤销已在网络中执行的旧请求。不具备可靠互斥与核对的能力限制为人工处理或只读。

如果依赖控制面在线才能恢复，能力清单必须写明这一限制。无法证明恢复路径可靠、无设备原生期限或本地恢复守护的能力，不进入自动响应默认清单。数据库或审计不可用时停止新的状态变更；既有底层防御独立运行，已授权的本地过期清理由本地持久记录约束。

## 7. 调度、停止和应急

普通研判、紧急响应、验证恢复分开资源份额。给清理、撤销、独立业务探针和动作核对保留容量；不能让“只保 P0/P1”饿死刚才动作的恢复。控制面暂停开关阻止新动作，并通过各站点执行器的本地状态生效；不能承诺瞬间撤销已经发生的副作用。

V1 场景默认草案：单 Incident 最多 3 次重新规划、8 次模型调用、12 次主动能力调用、15 分钟自动处置时间；这些是演示配置起点，非性能承诺。达到任一上限、相同失败重复且无新增证据、目标变化、授权撤回或业务恶化时，转人工/保持安全状态。超时、Token、工具与重试预算跨子任务累计。

恢复/清理使用预留但有界预算；预算耗尽必须显式上报未恢复状态，不能为了停止循环而假报清理完成。


---

模块来源：`docs/04_验证与运行状态.md`

# 独立验证与运行状态

## 1. 验证一个明确的主张

VerificationResult 必须包含 objective_type、claim、target_ids、scope_id、方法、预期与实测证据、开始结束时间、valid_until、适用策略/场景版本、残余风险。

| 目标类型 | 能证明的事 | 不自动证明的事 |
|---|---|---|
| DETECTION | 指定行为触发了预期检测 | 防御已阻止或根因已修复 |
| CONTAINMENT | 指定攻击路径在期限和范围内受限 | 所有路径都被阻止、漏洞已修复 |
| REMEDIATION | 指定根因的修复条件得到核验 | 未测试资产与变种全部安全 |
| RECOVERY | 指定合法业务恢复且状态一致 | 原攻击原因已经消失 |
| CLEANUP | 本次测试/动作资源按约定清理 | 整个环境不存在其他风险 |

扫描器连接失败不能证明漏洞不存在；一次模板未命中也不能泛化为“目标无漏洞”。实验室 HTTP 可用于让网络/应用两类观测清晰，生产 TLS 的可见范围必须另行定义。

## 2. 三类检查与整体判定

安全目标：授权重放、目标状态检查、指定控制/配置验证是否满足预期。

正常业务：独立良性请求、正常账户/合法路径、服务健康与业务依赖是否满足容忍阈值。根因修复可能有暂时维护影响，应在审批前写清可接受窗口，不能事后降低阈值。

观测有效性：所需 Sensor/Runner 身份、覆盖、配置、时钟、采集延迟、丢包、探针控制通道是否正常。心跳正常只是必要输入之一。探针被封禁或自身故障时，“没有攻击信号”属于证据缺口。

| 输入情况 | 总体结果 |
|---|---|
| 三类必要检查均 PASS，证据满足时效与 Scope | PASS |
| 有可信证据证明安全目标不达成或正常业务不满足 | FAIL，同时保留其他观测缺口 |
| 缺失必要证据，且没有足够证据判定目标/业务失败 | INCONCLUSIVE |

某检查无可靠观测时，其状态必须是 INCONCLUSIVE，不能先填 FAIL 再宣称这是可信失败。INCONCLUSIVE 不等于自动重做攻击测试；先修复观测/确认 Scope，再在预算内复核。

执行器回执证明调用层状态；独立验证探针和业务探针采用不同职责与权限，可共享可信观测基础设施，但不能仅复制执行器的 success 字段给自己打分。人为豁免/接受风险记录为 closure disposition，不改写技术验证结果。

## 3. Incident、Action、Task 状态分工

Incident 是事件处理进展；Action 是副作用调用生命周期；Task 是工作单元执行状态。权威迁移表在 `contracts/state_machines.json`。

Incident 主路径：NEW、TRIAGED、INVESTIGATING、PLANNED、EXECUTING、VERIFYING。验证遏制成功进入 CONTAINED；修复证据充分且满足关闭前置条件进入 RESOLVED；复核后 CLOSED。审批等待为 WAITING_APPROVAL，拒绝后回到调查/重新规划或 HUMAN_REVIEW，不跳转到已遏制。

CONTAINED 可以维持控制并等待根因处理；TTL 失效、业务异常、关键证据过期或发现新路径后返回调查。CLOSED 后收到新的相关证据，可以显式 REOPENED 并建立新处理周期，历史关闭记录保留。

Action 的执行成功终态是 EXECUTED，VerificationResult 单独记录 PASS/FAIL/INCONCLUSIVE。这样“执行成功但验证失败”可以同时成立。补偿使用 COMPENSATING、COMPENSATED、COMPENSATION_FAILED；不再把 VERIFIED/FAILED/ROLLED_BACK 混成一个轴。

Task 支持 QUEUED、BLOCKED、WAITING_APPROVAL、RUNNING、SUCCEEDED、FAILED、CANCELLED、TIMED_OUT。Task 成功只代表工作单元输出满足契约，例如“已取得 INCONCLUSIVE 验证记录”可视为验证任务完成；不会自动把 Incident 判为安全。

## 4. 关闭条件

自动技术关闭要求：处置目标达成且证据未过期、必要正常业务检查通过、观测有效、没有未核对的动作、没有逾期未清理副作用、残余风险在预先授权的关闭标准内。

至少保存 closure_type、理由、证据引用、责任人/策略版本和时间。CLOSED_REMEDIATED、CLOSED_FALSE_POSITIVE、CLOSED_DUPLICATE、CLOSED_ACCEPTED_RISK 是 closure_type，不是互相矛盾的 Incident 状态。接受风险/缺少技术证明的关闭必须人工记录，不改写 Verification 为 PASS。

判断为误报必须有具体证据；拒绝动作、模型置信度低、暂时没有新日志都不是误报证明。重复 Incident 可人工或确定性规则合并，保留旧 ID 重定向与证据关系。

## 5. 测试行为的反馈控制

ValidationRun 在发起前登记 run_id、发起身份、环境、目标、Scope、起止时间、预期信号、允许副作用、清理规则。run_id 来自可信控制记录；不信任日志正文自行声明“我是测试”。

预期行为关联到对应验证任务并计入检测效果；不另外无限创建处置链。异常目标、越时、越权、超出已登记行为或业务恶化仍进入正常检测和响应。没有全局免检 IP。

验证探针被响应影响时，先检查执行结果与业务旁路探针，不把自我阻断当作修复。暂停计划、取消新任务、恢复所拥有的临时规则和人工接管是明确的逃生路径。


---

模块来源：`docs/05_部署与能力适配.md`

# 运行环境、基础设施与能力适配

## 1. 平台与支持声明

核心控制面默认 Linux；用户在任意支持浏览器的 Windows/Linux/macOS 等设备操作。端点通过 Agent、日志、网络观测或 API 接入。服务器 OS 与用户桌面 OS 分离；在 Windows 上开发并不要求控制面生产运行在 Windows。

每项支持必须标成设计候选、已适配、已实验验证或已生产验证，附 OS/版本/架构/权限矩阵。此包中跨系统能力全部处于设计状态；不能把依赖项目支持某 OS 推导成智御已经完整支持它。

EnvironmentProfile 拆分正交维度：deployment_stage=LAB/PILOT/PRODUCTION；asset_domain=IT/OT/MIXED；connectivity=CONNECTED/RESTRICTED/AIR_GAPPED；operating_model=SINGLE_ORG/SOC_MSSP。Windows、Linux 等放在具体资产对象中。旧 LAB/ENTERPRISE/SOC_MSSP/AIR_GAPPED/CLOUD 的混合枚举不再使用；云是资产/接入属性，不互斥于企业生产或离线治理。

## 2. 按规模部署

| 配置 | 适用条件 | 运行组成 | 当前状态 |
|---|---|---|---|
| 实验室 V1 | 开发、比赛、重复场景 | Linux 控制 VM＋隔离网关/Sensor＋靶机＋测试与良性探针；Compose 管控制服务 | 当前设计基线 |
| 单组织试点 | 单站点、明确资产与响应范围 | 强化 Linux VM/少量节点、站点 Gateway、独立证据存储和备份；按风险隔离工具 | V1 后候选 |
| 企业扩展 | 实测吞吐/可用性要求超过单站点部署 | 按需 Kubernetes 多节点、独立状态/分析/模型/验证节点、Durable Workflow | 完整版可选配置 |
| 多站点/MSSP | 跨域与多客户边界明确 | 中央控制＋站点 Gateway，站点数据驻留与授权分域、多租户身份和密钥隔离 | V3 |
| 强隔离 | 数据不出域、离线运行 | 本地模型、离线签名更新包、内部制品仓、内网审计/证据，禁云路由 | V3 |

Ubuntu Server 24.04 LTS 可作为可复现起点；部署前锁定实际 OS、内核、包、镜像和工具版本并验证兼容性，不用“最新”替代锁文件。开发宿主可使用独立 Linux、Linux VM 或远程 Linux；是否支持嵌套虚拟化、抓包、GPU 透传必须实测。用户已有 RTX 5060 8GB 仅是可考虑的模型测试资源，未确认它是项目服务器，不能预设足以运行完整环境。

## 3. 跨平台感知与执行

| 资产域 | 接入方式 | 实际执行位置与限制 |
|---|---|---|
| Windows/AD | Wazuh/EDR、Event Log、可选 Sysmon/ETW/身份 API | Windows 指令/控制在授权 Windows 目标或管理端执行；高影响身份变更需审批 |
| Linux | Wazuh、audit/journal、可选 eBPF | Linux 目标或受控站点 Gateway；按需选择主 Sensor |
| Kubernetes | Audit、CNI/云 API、可选 Tetragon/Falco | 集群最小权限角色、命名空间和资源 UID 绑定；不默认部署所有重复 Sensor |
| macOS | Wazuh/MDM/EDR 接口 | 依实际厂商和权限矩阵验证；不是套用 Linux 命令 |
| Legacy Unix | 受支持 Agent 或 Syslog/API | OS/版本/架构单独核验；优先保守读取与适配 |
| 网络设备、IoT | Syslog、NetFlow/IPFIX、SNMP/API、被动网络 | 通过网关、交换机、防火墙等授权控制面；设备内执行不是默认能力 |
| 云/SaaS | 原生审计、Webhook、API | 账号/租户/区域/资源 ID 绑定；凭据与查询数据范围受控 |
| OT/ICS | TAP/SPAN、被动协议和厂商只读接口 | 生产默认 OBSERVE_ONLY/ASSISTED；主动测试仅在厂商认可的离线实验域 |
| Mainframe | 审计导出、消息/API/网关 | Agentless 适配，不能把支持日志读取宣传为端点自主处置 |
| 移动设备 | MDM/EDR/Identity API | 不将个人手机作为完整平台或任意目标执行宿主 |

## 4. Capability 要写清五个位置

每个 Manifest 明确 controller_location、execution_location、target_domain、network_path、cleanup_owner；另有 OS/arch、工具/模板版本、输入输出 Schema、Scope、权限、风险、超时、资源、幂等支持、核对与回滚能力。

| 能力 | 控制端与执行端 | 进入阶段 |
|---|---|---|
| Nuclei | 验证 Runner 向 Scope 内服务发请求；模板是输入的一部分，审查、锁定并留证 | V1 模板驱动检查 |
| 站点临时网络限制 | 控制面请求；网关 Adapter 对拥有的规则执行明确变更 | V1 |
| 独立安全/业务探针 | 独立 Runner 分别验证受限路径和合法路径，控制通道不被待测规则影响 | V1 |
| Atomic Red Team | 调度端发起；本地或远程测试代码实际在授权被测 OS 上执行 | V2，V1 可选补充 |
| CALDERA | 调度端限制 operation/ability；授权 agent 在对应端点执行步骤 | V2，V1 可选补充 |
| Strix | 受限复杂任务执行器；所有目标扩展、工具权限和预算仍受智御控制 | V2 可选 |

Atomic 官方区分本地执行和远程执行；Runner 的所在位置不等于测试影响发生的位置。[Atomic 远程执行说明](https://github.com/redcanaryco/invoke-atomicredteam/wiki/Execute-Atomic-Tests-%28Remote%29)

只读任务同样会解析不可信输入；R0–R2 不自动意味着可与主控共享宿主。隔离依据同时考虑不可信代码、解析器、网络暴露、权限与目标影响。普通容器适合可信低权限任务；有不可信执行需求时选 VM 隔离。Kata、Firecracker、KVM 是备选技术路径，不要求叠加使用。

Firecracker 需要 KVM 和配套 Linux 内核/rootfs，不能把“Kali Docker 镜像”视为可直接装入的通用替代；Windows 专项使用实际 Windows VM。[Firecracker 入门与要求](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md)

## 5. 完整版基础设施角色

| 属性 | 候选基础设施 | 引入条件与边界 |
|---|---|---|
| 长任务恢复 | Temporal 或同类 | 跨重启/审批/长时任务复杂度需要；业务幂等仍归 Adapter |
| 策略代码化 | OPA/Rego 或同类 | 策略规模/独立治理有收益；各入口和执行器仍须强制执行结果 |
| 工作负载身份 | SPIFFE/SPIRE 或同类、mTLS | 多服务/跨站点身份与证书治理需要 |
| 秘密管理 | Vault/KMS/HSM 或厂商代理 | 不默认同时部署所有产品；凭据在执行侧短时获取 |
| 高吞吐事件流 | Kafka/Redpanda/NATS JetStream 类 | 明确持久性、重放、排序与消费者语义；不把普通无持久 Pub/Sub 当耐久流 |
| 主状态 | PostgreSQL | Incident/Task/Action/Policy 等唯一事务主库 |
| 分析存储 | ClickHouse 类 | 事件量和分析查询实测需要；不要默认重复全部索引 |
| 原始证据 | S3 兼容对象存储 | hash、留存、访问权限、备份/不可变策略 |
| 图与全文 | Neo4j/Graphiti、OpenSearch 可选 | 只在查询收益明确时引入；图是可重建投影 |
| 缓存 | Redis/Valkey | 不做唯一动作状态或审批主库 |

事件流与工作流分开，不要求两个系统在 V1 都上线。高可用配置根据可用性目标与故障域制定；单纯有三个节点不能证明 HA。完整版需规划 PostgreSQL HA/PITR、证据备份、站点离线缓存、策略撤销与缓存期限、模型降级和验证 Worker 重建。RPO/RTO、吞吐、硬件容量待实测与业务要求确定。

## 6. 开源使用边界

Wazuh/Suricata/Nuclei 属第三方真实能力；Atomic/CALDERA 是验证扩展；PentAGI 只参考队列、摘要、记忆、沙箱与可观测思想；Anthropic-Cybersecurity-Skills 仅开发参考，不纳入运行时核心。OpenCTI/Zeek/图记忆按实际缺口后移。

每项依赖在首次集成时登记上游仓库、精确版本/commit、许可证、镜像 digest、模板集版本、支持平台、权限和漏洞处理人。本包未锁定真实构建版本，不能宣称完成许可证或供应链审核。

## 7. 完整版模型平面

保留 local_small（低成本提取/摘要）、local_strong（本地复杂研判）、cloud_strong（出域策略允许的复杂任务）与 offline_fallback（本地降级/规则/人工）四种路由角色，不要求实际部署四个模型。提取/标准化能用代码稳定完成时优先用代码。

路由先检查数据与环境边界，再比较任务复杂度、模型健康、延迟、成本和可用资源。模型 Worker 与主控解耦；V1可先一个模型接口。模型超时或上下文不足不能通过偷偷上传更多数据或绕过审批解决。各路由的真实质量、显存、并发和成本需要同一任务集实测，未验证前不填硬件承诺。


---

模块来源：`docs/06_V1场景与开发接口.md`

# V1 场景、数据链路与开发接口

## 1. 场景状态

SCN-LAB-AUTH-01 v1 是 ai.4 选定的默认设计基线，用于替代“以后再选一条攻击链”的长期未决项。它尚未搭建或实测。下列网段、阈值和时间均是可修改的合成实验参数，上线前必须确认与宿主/VPN网络不冲突并获得实际环境授权。

目标：证明受控异常认证行为能从独立网络/应用观测形成 Incident，经过证据规划与授权产生有限临时限制，再独立验证安全与业务效果。首条场景不宣称证明复杂 APT 识别或通用 Web 漏洞修复。

## 2. 最小拓扑

| 节点/区域 | 示例地址 | 职责 |
|---|---|---|
| Control/Mgmt | 10.77.10.10 | API、状态库、任务、模型网关、策略、Dashboard；与靶场接口分离 |
| Lab Gateway/Sensor | 各测试子网的 .1 网关 | 强制测试流量经过、Suricata、受控规则 Adapter；管理流量另走管理网 |
| Target-A | 10.77.20.10:8080 | 自建合成登录服务、结构化应用日志、Wazuh Agent |
| Validation-A | 10.77.30.10 | 授权异常请求与受限路径复测，仅访问目标端口 |
| Business-Probe | 10.77.40.10 | 独立良性业务请求与恢复检查 |
| Wazuh Manager/Evidence | 管理域内独立服务 | 主机/应用记录收集、只追加证据接入，可与低风险控制服务合并 |

物理机器可合并，逻辑隔离必须真实生效。Target-A 使用虚构测试账户，不使用真实口令/个人信息。演示可用明文 HTTP 观察请求与响应，仅限隔离环境；生产 TLS 场景另做可见性与传感器验证。

不需要 Target-B、AD 域或全部攻击模拟工具才能验收第一条链。后续场景再体现横向关系和 Windows 控制。

Scope 对每项能力分别限制来源主体：独立验证可以使用测试源和正常业务探针；临时限制能力的可作用来源只有 Validation-A。正常探针具有验证访问权，不因此成为可自动封禁对象。端口、目标和来源不能只靠一个粗略网段白名单判定。

## 3. 前置检查

环境注册 → 导入资产和地址有效期 → 时钟/覆盖检查 → 绑定 Profile/Scope/策略 → 注册 Capability → 测试合法业务基线 → 检查临时规则恢复能力 → 小流量 canary → ACTIVE。

必要条件：测试路由无绕行；Scope 外无默认可达路径；控制通道不经过待封规则；Sensor 能看到请求和应用失败记录；实验准备的正向健康请求成功；证据存储和动作核对可用。任一缺失则停止主动阶段。

## 4. 具体闭环

1. 登记可信 ValidationRun。测试节点在一分钟内产生 20 次虚构账户失败请求，最大 1 请求/秒。正常探针每 5 秒完成一次独立合法操作。参数是起始配置，不是攻击强度或性能成绩。
2. Suricata 输出受控测试请求的网络记录；Wazuh 收集 Target-A 的应用认证日志。不可用“Wazuh 转发 Suricata 的同一告警”替代第二来源。
3. 事件引擎以环境、目标、源地址有效绑定和 60 秒窗口关联；保留计数、失败分布、正常流量及冲突证据。
4. AI 至少比较“授权测试/异常重复认证、正常用户误操作、采集重复”三类解释，并引用真实输入 Evidence。该 run 的检测结果归属于场景，不能制造无限自响应链。
5. 确定性任务读取目标状态、失败日志、网络观测和正常业务基线；可用 Nuclei 的受审模板核对合成服务标识/配置，模板未命中不能泛化为安全。
6. 依据已登记的场景允许响应，对 Validation-A → Target-A TCP/8080 生成临时限制请求。ActionGateway 在实际网关执行，只操作该测试源/目标/端口和自己的规则，TTL 草案为 300 秒。
7. 执行器返回规则标识。独立验证从受限路径检查预期限制，从 Business-Probe 检查合法业务，另查 Sensor/Runner 覆盖与健康；证据充分才判 CONTAINMENT PASS。
8. Incident 进入 CONTAINED，记录控制到期时间、仍需处理的认证防护缺口；不直接 CLOSED。
9. 演示恢复：确认无冲突持有者后，由本地期限机制或预授权撤销清理专属规则，再验证合法路径/预期测试路径恢复。恢复不意味着攻击根因修复。
10. 需要完整修复展示时，启动 SCN-LAB-AUTH-02：人工批准启用测试服务的认证限速/锁定防护配置，移除临时源限制，在独立新测试会话中验证异常请求受限、合法账户正常、配置版本已生效；目标 REMEDIATION 满足后才按关闭条件复核。该扩展也是待实现设计。

## 5. 必须演示的反例

| 注入变化 | 预期判断 |
|---|---|
| 目标服务整体停止，攻击请求失败 | 正常业务失败，总体 FAIL；不能称防御成功 |
| 传感器/验证路径不可用 | 必要证据 INCONCLUSIVE；转观测修复 |
| 网关执行成功但回执丢失 | EXECUTION_UNKNOWN，先核对，不重复添加 |
| 审批后目标/参数变化 | 摘要不匹配，旧审批不可复用 |
| 规则到期但根因未修复 | 更新控制有效性，保持未修复/重新调查 |
| LLM 停止服务 | 新 AI 规划降级；既有规则、证据、核对和清理继续 |

## 6. V1 API 草案

所有入口带认证身份、环境权限和 trace_id。请求幂等键必须在实际修改系统的 Gateway 侧生效。以下是待实现接口契约，不是已上线端点。

| 方法/资源 | 作用 | 关键约束 |
|---|---|---|
| POST /v1/events/batches | 传感器批量提交规范化事件 | 校验来源身份、体积、重复和环境归属，返回接收/拒绝计数 |
| GET /v1/incidents/{id} | 获取 Incident 和引用 | 按环境过滤，证据正文按权限另取 |
| POST /v1/incidents/{id}/plans | 提交规划候选 | Schema/证据/能力/依赖/预算检查，不直接执行 |
| POST /v1/actions | 创建不可变动作请求 | 仅创建意图；服务端授权 |
| POST /v1/actions/{id}/approvals | 人工批准/拒绝 | 身份、角色、摘要、有效期绑定 |
| POST /v1/actions/{id}/dispatch | 授权后分发 | 执行前复核、租约、幂等、审计 |
| POST /v1/actions/{id}/reconcile | 核对未知执行状态 | 查询能力与权限单独校验 |
| POST /v1/validation-runs | 创建场景运行 | 版本化 Scope、测试窗口、预算和清理 |
| GET /v1/verification-results/{id} | 查询三态验证 | 展示目标、范围、时效和残余风险 |
| POST /v1/environments/{id}/pause | 暂停新动作 | 管理权限、站点确认和审计；不宣称副作用自动撤销 |

## 7. 数据表与事务边界

V1 建议实体表：environments、assets/address_bindings、sensor_health、events/event_groups、incidents、evidence_refs、context_bundles、plans/tasks、capability_manifests、actions/action_attempts、authorizations/approvals、verification_results、validation_runs、audit_entries、outbox。

动作意图/授权记录/outbox 同事务提交；任务领取原子改变状态和租约代次；回执更新校验版本。外部设备写操作不能和 PostgreSQL 做一个数据库事务，必须依靠幂等、状态核对和补偿。原始大对象由 Evidence Store 保存引用与哈希；中间件故障不能静默丢失审计。

## 8. Dashboard

首页显示 Incident、关键资产、Sensor 覆盖、负载与待审批动作。事件页按证据、模型假设、计划、授权理由、执行/核对、三项验证、残余风险展开时间线。区分模拟数据与真实数据、已遏制与已修复、执行失败与验证失败。聊天为辅助入口，不拥有额外执行权限。

人工操作至少包括查看证据、修改候选计划后重新授权、批准/拒绝、暂停环境、处理未知状态、确认清理和记录风险接受。Security Score 若尚无定义和校准，V1 不显示一个似乎精确的综合安全分数。


---

模块来源：`docs/07_实验验收与路线.md`

# 实验、验收与开发路线

## 1. 对照设计

| 组 | 保持条件 | 用途 |
|---|---|---|
| G0 底层工具 | 相同原始数据和场景；原有设备/人工步骤 | 观察总体运维流程变化 |
| G1 固定编排 | 与 G2 相同的聚合、状态、工具、授权、验证和资源预算，用规则/固定流程规划 | 分离“编排基础设施”与“AI 规划”的贡献 |
| G2 智御 AI 闭环 | 结构化研判、动态取证/规划；相同硬安全边界 | 主实验 |
| G3 定向消融 | 每次只去掉一种非安全能力，如相似历史检索或某种聚合策略 | 判断各项设计是否有实际收益 |

不能为了消融而关闭权限、Scope、业务健康或恢复机制。场景分为用于开发的已知案例和事先固定的未参与调参案例；模型/Prompt/策略/模板/环境版本同时锁定。

建议每个场景先做多次重复并报告样本数、失败数和离散程度；重复次数与硬件预算由实验计划批准，不能从少量样本宣称显著领先。相同事件回放和真实流量触发分别报告，避免把缓存重放性能当实时吞吐。

## 2. 指标定义

| 指标 | 计算口径/注意点 |
|---|---|
| 聚合压缩 | 原始事件数/事件组或 Incident 数，明确分母；同时报告错合并、漏关联和关键异常保留 |
| 研判质量 | 有标注场景的正确解释、漏报/误报、矛盾证据处理；模型自评分不算准确率 |
| 响应时延 | 事件发生/入库→首次判断→开始动作→独立验证分别计时，人工等待单列 |
| 有效遏制/修复 | 按 objective_type 分开统计 PASS/FAIL/INCONCLUSIVE，不把未知从分母隐去 |
| 业务影响 | 合法请求成功率、错误率、延迟、恢复用时和被误限制资产数 |
| 负载 | 接收/拒绝/丢失事件、队列长度/等待、P95/P99、降级与恢复时间 |
| 可靠性 | 未知动作最终核对率、重复副作用、残留规则、审批失效拦截 |
| 成本 | 每 Incident/每成功验证的模型调用、Token、工具次数、时间和实际费用（若可获得） |

临时规则到期后再次失败应记为遏制失效/根因未修复，不能只统计到首次 PASS 就结束。生产可用性、RPO/RTO、吞吐目标和模型准确率当前没有实测值。

## 3. 可执行的验收编号

| ID | 必须验证的行为 | 预期证据 |
|---|---|---|
| A01 | 两个真实来源入统一 Schema，重复血缘可识别 | 原始样本、解析版本、source/origin/provenance |
| A02 | 关联保留异常与矛盾，地址更换不误关联旧资产 | 输入/输出、时间与实体绑定 |
| A03 | 非法 JSON、伪造 Evidence ID、未知能力和循环依赖被拒绝 | 计划拒绝记录，无外部副作用 |
| A04 | Scope 外、过期授权、变更摘要、高影响自动请求被拒绝 | 决策与审计 |
| A05 | 实际变更后回执丢失进入 UNKNOWN 并核对 | 设备记录、ActionAttempts、没有重复规则 |
| A06 | 旧 Worker/重复消息不重复修改；补偿不覆盖他人变更 | 租约代次、规则 ownership 和设备状态 |
| A07 | 攻击受限、正常业务可用、观测有效才 PASS | 三类独立检查 |
| A08 | 业务中断是 FAIL；观测缺失是 INCONCLUSIVE | 反例输入和判定 |
| A09 | 临时遏制不会自动变成修复/关闭；TTL 到期复核 | Incident/Verification 时间线 |
| A10 | 模型离线/数据库异常不令底层防御失效，不新增无审计变更 | 故障注入与恢复记录 |
| A11 | 高负载下保留关键处理与恢复容量，损失显式可见 | 配额、丢失统计、恢复任务完成情况 |
| A12 | 可信测试运行可关联，伪造测试标签不能免检 | run registry、越界异常和正常检测 |
| A13 | 重规划无新证据/达预算后停止并转人工 | 事件级预算与停止原因 |
| A14 | 全链路可重建，敏感数据没有进入云模型/工作流历史/日志 | Context/版本/出域记录和数据检查 |
| A15 | 环境清理后恢复基线，闭环能重复运行 | 场景版本、前后快照、资源清理 |

资料包自检只检查文件、契约、合成示例和预期语义。A01–A15 的平台级验收全部未执行，不因本包自检通过而改成已完成。

## 4. 里程碑与实施顺序

| 里程碑 | 交付与出口条件 | 状态 |
|---|---|---|
| M0 设计基线 | 当前资料包、契约、默认场景、未决项 | 文档已形成；可继续审查 |
| M1 靶场与数据 | 拓扑可重置、双源真实样本、覆盖/合法业务基线 | 未验证 |
| M2 确定性骨架 | 不依赖 LLM 的事件→任务→授权→响应→三态验证，含 UNKNOWN 核对 | 未验证 |
| M3 AI 接入 | 合法 Context/Plan、证据校验、预算；与固定编排共用执行链 | 未验证 |
| M4 故障与对照 | A01–A15、G0/G1/G2、版本化运行记录 | 未验证 |
| M5 演示与材料 | 实际时间线、数据图表、限制和复现说明，再派生比赛稿 | 未验证 |

先定义接口和高风险边界，再接真实 Sensor，后让模型进入同一条链；避免模型接入后才补权限。日期和工作量由确认后的团队/硬件/比赛时间制定，本包不虚构排期。

## 5. 后续增强的进入条件

| 能力 | 应看到的缺口 | 阶段 |
|---|---|---|
| Atomic/CALDERA、Windows 池 | 首场景稳定后需要端点或攻击链控制覆盖 | V2/按需提前 |
| Strix | 固定工具无法完成某类明确授权的复杂验证，且可约束其子任务 | V2 |
| Zeek/eBPF/云源 | 当前 Evidence 类型不足，而非单纯增加来源数量 | V2 |
| 图投影/图检索 | 实际多跳查询或路径分析明显受限 | V2 |
| Temporal/事件流/列式库 | 长任务恢复、吞吐或查询瓶颈已有证据 | V2/V3 |
| 多租户/HA/跨站点 | 客户、故障域、数据驻留和权限需求明确 | V3 |

## 6. 仍需确认的事实

可用硬件和内存/GPU、团队分工、真实代码仓库与实现进度、比赛名称/日期/模板、最终模型与部署方式、企业试点资产/授权/出域要求、依赖版本、真实成本和性能均未知。可提出候选方案，不能填造结果。


---

模块来源：`docs/08_平台治理与故障处理.md`

# 平台治理、威胁模型与运行故障

## 1. 权限与数据

V1 最少 viewer、analyst、approver、admin 四类权限。审批记录具有真实身份；高影响变更可按环境配置禁止自批。服务身份与人身份分离。执行器仅获得当前动作所需的短时秘密；模型、原始日志、Trace 和工作流参数不得携带 Secret。

外部数据默认不可信。TLS/mTLS 帮助确认连接身份，不保证设备没有被攻陷；需要证据血缘、时效与交叉核对。受限数据的云模型 fallback 不进入候选路由。

Data Egress Gate 覆盖模型 API、第三方 Agent、模板下载、遥测、崩溃上报和外部存储。每条路径检查目的地、数据分类、脱敏、传输授权和留痕；不能只在主模型调用前加一个开关。离线环境需要预置受审工具/模板，不能临时从公网取包。

## 2. 关键威胁与约束

| 威胁 | 必须落实的约束 |
|---|---|
| 日志/网页/工具输出提示注入 | 不可信文本只做输入数据；证据 ID、能力、参数、Scope 和权限模型外校验 |
| 记忆污染 | 观测/推断分层、血缘与冲突、版本化纠正、有效期；高置信摘要不自我升级 |
| 目标绕行/重定向/DNS 变化 | 执行前与连接时绑定授权身份/IP范围/端口，按策略处理重定向，网络层强制限制 |
| 审批偷换 | 不可变请求摘要、批准有效期、执行前重审、服务端授权 |
| 控制面被滥用 | 最小权限、独立执行域、审计、环境暂停和站点强制策略 |
| 秘密泄露 | 凭据代理、返回值/错误/日志清洗、权限化证据正文、无秘密工作流参数 |
| 供应链污染 | 版本和 digest 锁定、模板/镜像审核、许可证记录、签名/来源与撤销机制 |
| 证据篡改 | 受限写入、只追加记录、哈希与审计、备份；哈希本身不能证明原始采集真实 |
| 告警资源攻击 | 可信分级、每来源配额、有界队列、保留恢复容量与可见损失 |
| 未恢复副作用 | ownership、设备回执、TTL执行位置、核对与补偿失败升级 |

## 3. 故障处置

| 故障 | 默认行为 | 恢复条件 |
|---|---|---|
| 模型超时/非法输出 | 有限重试，规则/人工降级 | 健康探测通过，保持事件级预算 |
| 模型给出危险动作 | 拒绝候选，保存理由 | 新证据或人工授权；不允许模型自批 |
| 主库/审计不可用 | 暂停新的状态变更，底层防御独立运行 | 恢复持久状态并核对未完成动作 |
| 站点断连 | 无有效缓存授权则不新执行；保持既有控制及受约束本地清理 | 重连后按 action_id/代次核对，不重放全部积压动作 |
| 策略/Scope 缓存过期 | 新变更 fail closed | 取得有效版本和撤销状态 |
| 传感器有心跳但丢包/积压 | 降低覆盖可信度，必要验证 INCONCLUSIVE | 覆盖 canary 和延迟恢复 |
| 执行器失联/超时 | 标未知、撤销执行租约、核对真实副作用 | 证明已执行/未执行/部分执行或转人工 |
| 验证 FAIL | 区分安全失败与业务损害，按预授权方案撤销或重新规划 | 新证据，预算允许，合法业务稳定 |
| 清理失败 | 标残留、通知 Dashboard 待人工，禁止声称恢复 | 核对设备与资源确已清理 |
| 证据空间不足 | 高水位降级、分级留存、明确损失和覆盖影响 | 空间恢复并处理积压；缺失历史不补造 |

## 4. 审计与可复现记录

每条 Trace 关联环境、Incident、Context、Plan、Task、Capability、授权/审批、ActionAttempt、Evidence、Verification、状态版本。模型记录 provider/model/config 和可获得的版本；若供应商未提供不可变版本，则记录已知别名与调用时间，并标注复现限制。

需要记录 policy、prompt、parser、event_rule、capability、tool/template、scenario、environment_profile 的精确版本。重放实验保留原始输入与实际输出；同一个模型再次调用不保证逐字相同，应比较结构、证据与行为结果。

## 5. 备份与升级

V1 至少能导出 PostgreSQL 状态、证据对象索引、配置/策略/模板版本和场景定义，并演示一次恢复到隔离环境。升级先迁移与兼容性检查，再 canary，再切换；不能在有未知动作时直接覆盖数据库或重置执行租约。

完整版按需求制定 RPO/RTO、状态复制、PITR、对象存储保护、站点证书轮换、离线更新包和灾备演练。备份成功不等于可恢复，恢复测试记录才是证据。企业 SLA、可用性百分比和恢复时间现在都没有实测承诺。


---

模块来源：`docs/09_接续维护与审查闭环.md`

# 接续、维护和审查闭环

## 1. 本轮审查项逐项落实

| 审查项 | 落实位置 | 需要后续运行验证 |
|---|---|---|
| 文件引用、摘要与字段漂移 | START_HERE、PROJECT_STATE、生成脚本/manifest | 包自检可检查引用/枚举，真实代码兼容性未验证 |
| 遏制与修复/关闭混淆 | 文档04/06，VerificationResult、Incident状态 | A07–A09 |
| 正常业务被一并阻断 | 文档04，三项检查及反例 | A07/A08 |
| 审批目标/参数偷换 | 文档03，ApprovalRecord、动作摘要 | A04 |
| 幂等与未知执行/回滚冲突 | 文档03/08，状态机 | A05/A06 |
| 模型置信度与证据血缘 | 文档02，Evidence/AIPlan | A01–A03 |
| 自测试触发自响应循环 | 文档04/06，ValidationRun | A12/A13 |
| 队列、存储、恢复容量 | 文档02/03/08 | A10/A11 |
| 跨系统执行位置和基础设施门槛 | 文档05，CapabilityManifest | OS/权限/网络适配测试 |
| AI 相对固定编排增益 | 文档07，对照G1/G2 | 正式实验未开始 |

## 2. 与 ai.3 的迁移

- 原 0/1/2/5/6/13/15/附录C → START_HERE、文档01/05、PROJECT_STATE 和 CHANGELOG。
- 原 4/9/19 的数据、状态和上下文 → 文档02/03＋contracts；模型字段定义集中维护。
- 原 20/21/23 → 文档04/07/08＋state_machines。
- 原 27–32 → 文档01/05/08；五平面保留，环境分类正交化。
- 原 7/8/10/14/16/24/25/26 → 文档06/07；默认场景已选为设计基线，实际硬件/代码/指标仍未知。
- 原 11/22/28 的治理边界 → 文档03/04/08。
- 原 17/阅读协议 → START_HERE 与本文；AI 阅读版自动合并，禁止继续无止境附加“新审查章节”而不更新前文。

关键不兼容变化：ActionRequest 删除可自授的审批字段；Approval 绑定请求摘要/到期；旧环境枚举拆分；Action 执行状态与 Verification 分离；时间字段明确 source/ingest；PASS 不自动关闭 Incident。没有旧代码，故这里只定义迁移规则，未声称完成数据库迁移。

## 3. 变更流程

新增/替换组件必须回答现有明确缺口、既有模块能否解决、属于V1/V2/V3、运行成本、权限边界、失败行为、迁移方法和可验证收益。改变设计可由用户或新证据触发；“已确定”不表示永远不能改。

编辑权威源后执行 `python tools/build_package.py` 和 `python tools/validate_package.py`。生成阅读版、JSON Schema 与 manifest，并核对示例。生成物禁止手工修改；发现冲突修源再生成。依赖 Python 3.12+、Pydantic 2.x、PyYAML 6.x，当前使用环境的具体版本记录于自检结果。

contracts/models.py 是可执行的数据契约草案和包内校验依据，不是平台运行代码。示例 action digest 用于展示绑定机制；生产必须由服务端生成并验证，不能信任客户端自报。tools/validate_package.py 不构成权限系统或安全产品测试。

## 4. 每次接续输出

接手 AI 先说明正在做哪个里程碑、读取哪些相关源、哪些是已知设计/实际成果/未知。完成后更新变更日志、项目状态和可复现证据。若没有运行环境，交付设计或代码时直接标记未运行；禁止写虚构命令输出、性能数字或成功截图。

重大变更必须同步数据契约、负面样例、状态迁移、场景与完整阅读版。新增文件名使用稳定路径；版本放在元数据中，避免每次版本变更都造成大量内部链接失效。

## 5. 参考来源与使用限制

以下为查核入口，不代表已经锁定依赖或完成集成：

| 来源 | 作用 |
|---|---|
| [Wazuh](https://github.com/wazuh/wazuh) | 终端数据与响应适配 |
| [Suricata](https://github.com/OISF/suricata) | 网络观测与事件字段 |
| [Nuclei](https://github.com/projectdiscovery/nuclei) / [模板](https://github.com/projectdiscovery/nuclei-templates) | 模板驱动检查 |
| [Atomic](https://github.com/redcanaryco/atomic-red-team) | 原子行为测试 |
| [CALDERA 文档](https://caldera.readthedocs.io/en/latest/Basic-Usage.html) | 授权模拟与端点执行 |
| [Strix](https://github.com/usestrix/strix) | 可选复杂安全执行器 |
| [PentAGI](https://github.com/vxcontrol/pentagi) | 架构参考 |
| [Zeek](https://github.com/zeek/zeek) / [OpenCTI](https://github.com/OpenCTI-Platform/opencti) | 后续感知/情报适配 |
| [MITRE ATT&CK](https://attack.mitre.org/) | 行为分类参考，不作为预测真值 |
| [Temporal Activity](https://docs.temporal.io/activity-definition) | 重试、幂等与外部副作用边界 |
| [Firecracker](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md) | 隔离执行的实际要求 |

技术选型在首次集成前重新核对官方仓库、许可和版本。本文引用的具体运行语义已在本轮审查查核；未逐一证明所有可选产品的现行兼容性。


---

模块来源：`docs/10_ai5工程冻结与实现入口.md`

# ai.5 Engineering Freeze 与实现入口

## 1. 冻结含义

ai.5 是第一版可以直接指导数据库、API、Adapter、Worker 和测试实现的工程基线。它不表示平台已经实现，也不表示 A01–A15 已通过；它表示核心语义不再因为“发现一个新框架”而随意变化。

允许触发 ai.6 的原因仅包括：实现发现、测试证据、安全缺陷、实测性能瓶颈、第三方真实约束与当前假设冲突。

## 2. 七项 P0 工程补强

1. **ResourceRef / Scope 泛化**：网络端点、Host、Identity、Kubernetes、Cloud、SaaS 和 Security Control 使用统一资源引用；网络端口只作为 NetworkConstraint，而不是整个系统的唯一 Target 模型。
2. **NormalizedEvent 语义冻结**：统一事件拥有 CloudEvents-like 标识/来源/时间，同时具备安全 activity/outcome/actor/source/target/observable 语义。Adapter 可映射 OCSF，但核心不绑定完整 OCSF。
3. **EventGroup / CorrelationDecision**：任何事件压缩都保留成员、排除项、规则版本和原因，支持解释与回归测试。
4. **生命周期与租约**：Incident/Task/ActionAttempt 具备可计算 MTTD/MTTR 和恢复语义所需的时间、worker、lease/fencing 信息。
5. **VerificationSpec**：Security / Business / Observation 三类检查由结构化断言驱动；执行器 ACK 不直接作为 PASS。
6. **AuthorizationContext**：策略输出之外还保存当时的完整授权输入快照，支持审计与重放。
7. **ModelRun**：AI 调用本身成为可版本化、可计费、可回归评测的一等对象。

## 3. 开工原则

第一阶段不接 LLM。M1/M2 必须先跑通确定性闭环：

`Event -> EventGroup -> Incident -> deterministic plan -> Task -> Capability -> Authorization -> Action -> Verification -> State Update`

只有这条链能在真实靶场稳定复现后，M3 才把 AI Planner 通过相同 Contract 接入。AI 不获得额外执行权限。

## 4. M1 最小工程入口

- Linux Control Plane；开发期 Docker Compose，PostgreSQL 为 canonical state。
- FastAPI + Pydantic + SQLAlchemy/Alembic。
- 真实代码中的 `domain/contracts` 直接来源于 ai.5，不重新手抄一套字段。
- 首批持久对象：Environment、Resource、Scope、Event、EventGroup、CorrelationDecision、Incident、Evidence、Task、Lease、Capability、CapabilityHealth、Action、Authorization、Attempt、Verification、Audit、Outbox。
- 所有外部 side effect 在 durable intent + authorization + outbox 成功提交后才允许分发。
- 第一个场景继续使用 `SCN-LAB-AUTH-01`，但示例地址和阈值仍是合成配置，必须在真实宿主网络确认后才能运行。


---

# 权威数据契约

```python
"""智御 ai.5 Engineering Freeze 数据契约。

这些模型是实现基线：用于 API / DB / Adapter / Worker / AI structured output 之间的共同语言。
它们不等价于平台已实现，也不授予任何真实环境权限。
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Risk(str, Enum):
    R0 = "R0"; R1 = "R1"; R2 = "R2"; R3 = "R3"; R4 = "R4"; R5 = "R5"


class Verdict(str, Enum):
    PASS = "PASS"; FAIL = "FAIL"; INCONCLUSIVE = "INCONCLUSIVE"


class IncidentStatus(str, Enum):
    NEW = "NEW"; TRIAGED = "TRIAGED"; INVESTIGATING = "INVESTIGATING"; PLANNED = "PLANNED"
    WAITING_APPROVAL = "WAITING_APPROVAL"; EXECUTING = "EXECUTING"; VERIFYING = "VERIFYING"
    CONTAINED = "CONTAINED"; RESOLVED = "RESOLVED"; CLOSED = "CLOSED"; HUMAN_REVIEW = "HUMAN_REVIEW"; REOPENED = "REOPENED"


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"; BLOCKED = "BLOCKED"; WAITING_APPROVAL = "WAITING_APPROVAL"; RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"; FAILED = "FAILED"; CANCELLED = "CANCELLED"; TIMED_OUT = "TIMED_OUT"


class ActionStatus(str, Enum):
    PROPOSED = "PROPOSED"; WAITING_APPROVAL = "WAITING_APPROVAL"; AUTHORIZED = "AUTHORIZED"; DISPATCHED = "DISPATCHED"
    EXECUTING = "EXECUTING"; EXECUTED = "EXECUTED"; EXECUTION_UNKNOWN = "EXECUTION_UNKNOWN"; RECONCILING = "RECONCILING"
    COMPENSATING = "COMPENSATING"; COMPENSATED = "COMPENSATED"; COMPENSATION_FAILED = "COMPENSATION_FAILED"
    NEEDS_MANUAL = "NEEDS_MANUAL"; DENIED = "DENIED"; EXPIRED = "EXPIRED"; CANCELLED = "CANCELLED"; FAILED = "FAILED"


class EnvironmentProfile(Contract):
    object_type: Literal["EnvironmentProfile"] = "EnvironmentProfile"
    environment_id: str
    version: str
    deployment_stage: Literal["LAB", "PILOT", "PRODUCTION"]
    asset_domain: Literal["IT", "OT", "MIXED"]
    connectivity: Literal["CONNECTED", "RESTRICTED", "AIR_GAPPED"]
    operating_model: Literal["SINGLE_ORG", "SOC_MSSP"]
    autonomy_mode: Literal["OBSERVE_ONLY", "ASSISTED", "CONTROLLED_AUTONOMY", "VALIDATION"]
    load_mode: Literal["NORMAL", "HIGH_LOAD", "EMERGENCY"]
    model_policy: Literal["LOCAL_ONLY", "HYBRID", "CLOUD_ALLOWED"]
    data_egress_policy: Literal["DENY", "REDACT_THEN_ALLOW", "ALLOW"]
    max_auto_risk: Risk
    active_validation: Literal["DISABLED", "ISOLATED_ONLY", "SCOPED_PREAPPROVED"]
    scope_ids: list[str]
    capability_allowlist: list[str]
    required_sensor_ids: list[str]
    policy_version: str
    owner_id: str

    @model_validator(mode="after")
    def constraints(self):
        if self.max_auto_risk == Risk.R5:
            raise ValueError("R5 cannot be preauthorized for automatic execution")
        if self.connectivity == "AIR_GAPPED" and (self.model_policy != "LOCAL_ONLY" or self.data_egress_policy != "DENY"):
            raise ValueError("air-gapped profile must use local-only model and deny egress")
        if self.deployment_stage == "PRODUCTION" and self.asset_domain in ("OT", "MIXED"):
            if self.autonomy_mode not in ("OBSERVE_ONLY", "ASSISTED") or self.active_validation != "DISABLED":
                raise ValueError("OT production profile defaults to passive; IT scopes require separate profiles")
        return self


class ResourceRef(Contract):
    """跨 OS / Cloud / K8s / Identity 的统一资源引用。locator 是定位信息，不是授权本身。"""
    object_type: Literal["ResourceRef"] = "ResourceRef"
    resource_id: str
    environment_id: str
    resource_type: Literal["NETWORK_ENDPOINT", "HOST", "IDENTITY", "KUBERNETES", "CLOUD", "SAAS", "SECURITY_CONTROL"]
    binding_version: int = Field(ge=1)
    locator: dict[str, Any]
    display_name: str | None = None

    @model_validator(mode="after")
    def locator_constraints(self):
        if self.resource_type == "NETWORK_ENDPOINT":
            required = {"address", "port", "protocol"}
            if not required.issubset(self.locator):
                raise ValueError("network endpoint requires address/port/protocol locator")
            if not 1 <= int(self.locator["port"]) <= 65535:
                raise ValueError("invalid network endpoint port")
            if self.locator["protocol"] not in ("TCP", "UDP"):
                raise ValueError("invalid network endpoint protocol")
        if self.resource_type == "IDENTITY" and not ({"object_id", "account_name"} & set(self.locator)):
            raise ValueError("identity requires object_id or account_name")
        if self.resource_type == "KUBERNETES" and not {"cluster_uid", "kind", "name"}.issubset(self.locator):
            raise ValueError("kubernetes resource requires cluster_uid/kind/name")
        if self.resource_type == "CLOUD" and not {"provider", "resource_id"}.issubset(self.locator):
            raise ValueError("cloud resource requires provider/resource_id")
        return self


class NetworkConstraint(Contract):
    source_resource_ids: list[str] = Field(min_length=1)
    target_resource_ids: list[str] = Field(min_length=1)
    destination_ports: list[int] = Field(min_length=1)
    protocols: list[Literal["TCP", "UDP"]] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_ports(self):
        if any(not 1 <= p <= 65535 for p in self.destination_ports):
            raise ValueError("invalid network constraint port")
        return self


class ScopeDefinition(Contract):
    object_type: Literal["ScopeDefinition"] = "ScopeDefinition"
    scope_id: str
    environment_id: str
    version: str
    source_resource_ids: list[str] = Field(min_length=1)
    target_resource_ids: list[str] = Field(min_length=1)
    capability_source_ids: dict[str, list[str]]
    allowed_capabilities: list[str] = Field(min_length=1)
    network_constraints: list[NetworkConstraint] = Field(default_factory=list)
    valid_from: AwareDatetime
    valid_until: AwareDatetime
    max_requests_per_second: float = Field(gt=0)

    @model_validator(mode="after")
    def constraints(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("invalid scope time")
        for cap, sources in self.capability_source_ids.items():
            if cap not in self.allowed_capabilities or not sources or not set(sources).issubset(self.source_resource_ids):
                raise ValueError("capability-specific source constraint must narrow declared scope")
        for nc in self.network_constraints:
            if not set(nc.source_resource_ids).issubset(self.source_resource_ids) or not set(nc.target_resource_ids).issubset(self.target_resource_ids):
                raise ValueError("network constraint must narrow declared resources")
        return self


class Observable(Contract):
    observable_type: Literal["IP", "DOMAIN", "URL", "HASH", "PROCESS", "USER", "FILE", "REGISTRY", "CLOUD_RESOURCE", "OTHER"]
    value: str
    role: Literal["SOURCE", "TARGET", "RELATED", "INDICATOR"] = "RELATED"


class NormalizedEvent(Contract):
    object_type: Literal["NormalizedEvent"] = "NormalizedEvent"
    event_id: str
    specversion: Literal["1.0"] = "1.0"
    environment_id: str
    source_type: str
    collector_id: str
    origin_event_id: str
    provenance_group: str
    source_timestamp: AwareDatetime
    ingested_at: AwareDatetime
    clock_status: Literal["TRUSTED", "SKEWED", "UNKNOWN"]
    event_type: str
    activity_category: str
    activity_name: str
    outcome: Literal["SUCCESS", "FAILURE", "UNKNOWN", "PARTIAL", "DENIED"]
    actor_resource_id: str | None = None
    source_resource_ids: list[str] = Field(default_factory=list)
    target_resource_ids: list[str] = Field(default_factory=list)
    observables: list[Observable] = Field(default_factory=list)
    severity_signal: int = Field(ge=0, le=10)
    raw_ref: str
    parser_version: str
    mapping_version: str
    fingerprint: str
    validation_run_id: str | None = None
    data_origin: Literal["SYNTHETIC", "OBSERVED"]


class EventGroup(Contract):
    object_type: Literal["EventGroup"] = "EventGroup"
    group_id: str
    environment_id: str
    first_seen_at: AwareDatetime
    last_seen_at: AwareDatetime
    member_event_ids: list[str] = Field(min_length=1)
    grouping_keys: dict[str, str]
    correlation_reasons: list[str] = Field(min_length=1)
    outlier_event_ids: list[str] = Field(default_factory=list)
    correlation_confidence: float = Field(ge=0, le=1)
    rule_version: str
    algorithm_version: str

    @model_validator(mode="after")
    def interval(self):
        if self.last_seen_at < self.first_seen_at:
            raise ValueError("invalid event group interval")
        if set(self.outlier_event_ids) & set(self.member_event_ids):
            raise ValueError("outliers cannot also be members")
        return self


class CorrelationDecision(Contract):
    object_type: Literal["CorrelationDecision"] = "CorrelationDecision"
    decision_id: str
    environment_id: str
    input_event_ids: list[str] = Field(min_length=1)
    output_group_id: str
    rules_fired: list[str] = Field(min_length=1)
    merge_reason: str
    excluded_event_ids: list[str] = Field(default_factory=list)
    decision_version: str
    created_at: AwareDatetime


class Evidence(Contract):
    object_type: Literal["Evidence"] = "Evidence"
    evidence_id: str
    environment_id: str
    incident_id: str
    source_event_ids: list[str]
    provenance_group: str
    claim_kind: Literal["OBSERVATION", "SOURCE_ASSERTION", "INFERENCE", "HUMAN_REVIEW"]
    observed_at: AwareDatetime
    collected_at: AwareDatetime
    valid_until: AwareDatetime
    content_ref: str
    integrity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    hash_algorithm: Literal["SHA256"] = "SHA256"
    collector_id: str
    collection_method: str
    trust_status: Literal["VERIFIED_ORIGIN", "UNVERIFIED_ORIGIN", "CONFLICTED"]
    supports: list[str]
    contradicts: list[str]
    data_origin: Literal["SYNTHETIC", "OBSERVED"]


class SensorHealth(Contract):
    object_type: Literal["SensorHealth"] = "SensorHealth"
    sensor_id: str
    environment_id: str
    status: Literal["HEALTHY", "DEGRADED", "OFFLINE", "UNKNOWN"]
    last_heartbeat_at: AwareDatetime
    last_event_at: AwareDatetime | None
    lag_seconds: float = Field(ge=0)
    lost_event_count: int = Field(ge=0)
    coverage_scope_ids: list[str]
    coverage_validated: bool
    config_version: str


class StateEntity(Contract):
    object_type: Literal["StateEntity"] = "StateEntity"
    entity_id: str
    environment_id: str
    entity_type: str
    state_version: int = Field(ge=1)
    attributes: dict[str, Any]
    claim_kind: Literal["OBSERVATION", "INFERENCE", "HUMAN_REVIEW"]
    evidence_ids: list[str]
    observed_at: AwareDatetime
    valid_until: AwareDatetime


class StateRelation(Contract):
    object_type: Literal["StateRelation"] = "StateRelation"
    relation_id: str
    environment_id: str
    source_entity_id: str
    destination_entity_id: str
    relation_type: str
    state_version: int = Field(ge=1)
    evidence_ids: list[str]
    valid_from: AwareDatetime
    valid_until: AwareDatetime


class SecurityIncident(Contract):
    object_type: Literal["SecurityIncident"] = "SecurityIncident"
    incident_id: str
    environment_id: str
    title: str
    status: IncidentStatus
    priority: Literal["P0", "P1", "P2", "P3", "P4"]
    affected_asset_ids: list[str]
    related_event_ids: list[str]
    event_group_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str]
    state_version: int = Field(ge=1)
    first_observed_at: AwareDatetime
    created_at: AwareDatetime
    updated_at: AwareDatetime
    triaged_at: AwareDatetime | None = None
    investigation_started_at: AwareDatetime | None = None
    contained_at: AwareDatetime | None = None
    resolved_at: AwareDatetime | None = None
    closed_at: AwareDatetime | None = None
    open_action_ids: list[str]
    residual_risks: list[str]
    closure_type: Literal["CLOSED_REMEDIATED", "CLOSED_FALSE_POSITIVE", "CLOSED_DUPLICATE", "CLOSED_ACCEPTED_RISK"] | None = None
    closure_evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def constraints(self):
        if self.created_at < self.first_observed_at or self.updated_at < self.created_at:
            raise ValueError("incident timestamps are not monotonic")
        if self.status == IncidentStatus.CLOSED and (not self.closure_type or not self.closure_evidence_ids or not self.closed_at):
            raise ValueError("closed incident requires disposition, evidence and closed_at")
        if self.status != IncidentStatus.CLOSED and self.closure_type:
            raise ValueError("closure disposition only applies to closed incident")
        return self


class ContextBundle(Contract):
    object_type: Literal["ContextBundle"] = "ContextBundle"
    context_id: str
    environment_id: str
    incident_id: str
    state_version: int = Field(ge=1)
    evidence_ids: list[str]
    excluded_evidence_reasons: dict[str, str]
    unresolved_conflicts: list[str]
    sensor_health_ids: list[str]
    capability_ids: list[str]
    policy_version: str
    token_budget: int = Field(gt=0)
    data_classification: Literal["PUBLIC", "INTERNAL", "SENSITIVE", "RESTRICTED"]
    egress_allowed: bool
    summary_version: str
    prompt_version: str
    created_at: AwareDatetime


class WorkerLease(Contract):
    object_type: Literal["WorkerLease"] = "WorkerLease"
    lease_id: str
    task_id: str
    worker_id: str
    generation: int = Field(ge=1)
    acquired_at: AwareDatetime
    expires_at: AwareDatetime
    renewed_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def lease_time(self):
        if self.expires_at <= self.acquired_at:
            raise ValueError("lease expiry must follow acquisition")
        if self.renewed_at and self.renewed_at < self.acquired_at:
            raise ValueError("renewed_at cannot predate acquisition")
        return self


class Task(Contract):
    object_type: Literal["Task"] = "Task"
    task_id: str
    incident_id: str
    environment_id: str
    dependencies: list[str]
    capability_id: str
    capability_version: str
    target_resource_ids: list[str] = Field(min_length=1)
    scope_id: str
    parameters: dict[str, Any]
    status: TaskStatus
    priority: Literal["P0", "P1", "P2", "P3", "P4"]
    timeout_seconds: int = Field(gt=0)
    max_attempts: int = Field(ge=1, le=10)
    attempt_count: int = Field(ge=0, le=10)
    expected_output: str
    evidence_ids: list[str]
    created_at: AwareDatetime
    queued_at: AwareDatetime
    claimed_at: AwareDatetime | None = None
    started_at: AwareDatetime | None = None
    finished_at: AwareDatetime | None = None
    active_lease_id: str | None = None
    worker_id: str | None = None


class Hypothesis(Contract):
    hypothesis_id: str
    claim: str
    evidence_ids: list[str]
    counter_evidence_ids: list[str]
    missing_evidence: list[str]
    model_confidence: float | None = Field(default=None, ge=0, le=1)
    calibration_status: Literal["UNCALIBRATED", "CALIBRATED"] = "UNCALIBRATED"


class AIPlan(Contract):
    object_type: Literal["AIPlan"] = "AIPlan"
    plan_id: str
    incident_id: str
    environment_id: str
    context_id: str
    model_run_id: str | None = None
    hypotheses: list[Hypothesis] = Field(min_length=1)
    tasks: list[Task] = Field(min_length=1)
    stop_conditions: list[str] = Field(min_length=1)
    max_replans: int = Field(ge=0)
    total_model_calls: int = Field(ge=0)

    @model_validator(mode="after")
    def dag(self):
        nodes = {t.task_id: t for t in self.tasks}
        if len(nodes) != len(self.tasks): raise ValueError("duplicate task id")
        visited, active = set(), set()
        def visit(key):
            if key not in nodes: raise ValueError("unknown task dependency")
            if key in active: raise ValueError("cyclic task graph")
            if key in visited: return
            active.add(key)
            for dep in nodes[key].dependencies: visit(dep)
            active.remove(key); visited.add(key)
        for t in self.tasks:
            if t.environment_id != self.environment_id or t.incident_id != self.incident_id:
                raise ValueError("cross-environment/incident task")
            visit(t.task_id)
        return self


class ModelRun(Contract):
    object_type: Literal["ModelRun"] = "ModelRun"
    run_id: str
    environment_id: str
    incident_id: str
    task_id: str | None
    provider: str
    model: str
    model_revision: str | None = None
    prompt_version: str
    context_id: str
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    route_reason: str
    fallback_from_run_id: str | None = None
    started_at: AwareDatetime
    finished_at: AwareDatetime
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    schema_valid: bool
    safety_status: Literal["PASS", "REJECTED", "DEGRADED"]


class CapabilityManifest(Contract):
    object_type: Literal["CapabilityManifest"] = "CapabilityManifest"
    capability_id: str
    version: str
    adapter: str
    base_risk: Risk
    operation_kind: Literal["PASSIVE_READ", "ACTIVE_CHECK", "STATE_CHANGE"]
    controller_location: str
    execution_location: str
    target_domain: str
    network_path: str
    cleanup_owner: str
    supported_os: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    scope_required: bool
    timeout_seconds: int = Field(gt=0)
    idempotency: Literal["NATIVE", "ADAPTER_RECONCILE", "NONE"]
    reconciliation_method: str
    ttl_enforcement: Literal["DEVICE", "SITE_DURABLE_WATCHDOG", "CONTROLLER_ONLY", "NONE"]
    rollback_policy: str
    required_permissions: list[str]
    required_secret_refs: list[str]
    supports_cancel: bool
    supports_dry_run: bool
    resource_locks: list[str]
    max_concurrency: int = Field(ge=1)
    expected_evidence_types: list[str]
    verification_capability_id: str | None = None
    compensator_capability_id: str | None = None
    integration_status: Literal["DESIGN", "ADAPTED", "LAB_VERIFIED", "PRODUCTION_VERIFIED"]


class CapabilityHealth(Contract):
    object_type: Literal["CapabilityHealth"] = "CapabilityHealth"
    capability_id: str
    capability_version: str
    environment_id: str
    worker_pool: str
    status: Literal["UNVERIFIED", "HEALTHY", "DEGRADED", "OFFLINE"]
    checked_at: AwareDatetime
    latency_ms: int | None = Field(default=None, ge=0)
    queue_depth: int = Field(ge=0)
    running_count: int = Field(ge=0)
    detail: str | None = None


class ActionRequest(Contract):
    object_type: Literal["ActionRequest"] = "ActionRequest"
    action_id: str
    incident_id: str
    task_id: str
    environment_id: str
    capability_id: str
    capability_version: str
    source: ResourceRef | None
    target: ResourceRef
    parameters: dict[str, Any]
    scope_id: str
    scope_version: str
    environment_profile_version: str
    policy_version: str
    expected_state_version: int = Field(ge=1)
    preconditions: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    created_at: AwareDatetime
    expires_at: AwareDatetime
    ttl_seconds: int = Field(ge=0)
    idempotency_key: str
    ownership_tag: str
    rollback_policy_id: str

    @model_validator(mode="after")
    def constraints(self):
        if self.expires_at <= self.created_at: raise ValueError("action expiry must follow creation")
        if self.target.environment_id != self.environment_id or (self.source and self.source.environment_id != self.environment_id):
            raise ValueError("action resource must belong to environment")
        return self


def action_digest(action: ActionRequest) -> str:
    body = json.dumps(action.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


class ApprovalRecord(Contract):
    object_type: Literal["ApprovalRecord"] = "ApprovalRecord"
    approval_id: str
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    actor_id: str
    actor_role: Literal["APPROVER", "ADMIN"]
    decision: Literal["APPROVED", "REJECTED"]
    reason: str
    policy_version: str
    approved_at: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def constraints(self):
        if self.expires_at <= self.approved_at: raise ValueError("approval has no valid time window")
        return self


class AuthorizationContext(Contract):
    object_type: Literal["AuthorizationContext"] = "AuthorizationContext"
    authorization_context_id: str
    environment_id: str
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    principal_id: str
    principal_role: str
    environment_profile_version: str
    scope_id: str
    scope_version: str
    capability_id: str
    capability_version: str
    target_resource_id: str
    source_resource_id: str | None
    asset_criticality: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    business_impact: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    evidence_quality: Literal["LOW", "MEDIUM", "HIGH"]
    sensor_health_status: Literal["HEALTHY", "DEGRADED", "UNKNOWN"]
    autonomy_mode: Literal["OBSERVE_ONLY", "ASSISTED", "CONTROLLED_AUTONOMY", "VALIDATION"]
    load_mode: Literal["NORMAL", "HIGH_LOAD", "EMERGENCY"]
    requested_risk: Risk
    policy_version: str
    budget_id: str
    created_at: AwareDatetime


class AuthorizationDecision(Contract):
    object_type: Literal["AuthorizationDecision"] = "AuthorizationDecision"
    authorization_id: str
    authorization_context_id: str
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL", "DOWNGRADE"]
    assessed_risk: Risk
    business_impact: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    human_approval_required: bool
    approval_id: str | None
    policy_version: str
    valid_until: AwareDatetime
    reasons: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def constraints(self):
        high = self.assessed_risk == Risk.R5 or self.business_impact in ("HIGH", "CRITICAL")
        if high and not self.human_approval_required: raise ValueError("high impact cannot bypass human approval")
        if self.outcome == "ALLOW" and self.human_approval_required and not self.approval_id: raise ValueError("allow requires approval reference")
        return self


class ActionAttempt(Contract):
    object_type: Literal["ActionAttempt"] = "ActionAttempt"
    attempt_id: str
    action_id: str
    status: ActionStatus
    fencing_generation: int = Field(ge=1)
    worker_id: str
    started_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    device_receipt_id: str | None
    reconciliation_state: Literal["NOT_NEEDED", "PENDING", "CONFIRMED_APPLIED", "CONFIRMED_NOT_APPLIED", "PARTIAL", "UNKNOWN"]
    evidence_ids: list[str]
    error_code: str | None = None
    error_class: str | None = None
    device_response_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class AssertionSpec(Contract):
    field: str
    operator: Literal["EQUALS", "NOT_EQUALS", "IN", "NOT_IN", "LT", "LTE", "GT", "GTE", "EXISTS", "NOT_EXISTS", "MATCHES"]
    expected: Any | None = None


class VerificationCheckSpec(Contract):
    check_id: str
    dimension: Literal["SECURITY", "BUSINESS", "OBSERVATION"]
    capability_id: str
    source_resource_id: str | None = None
    target_resource_id: str
    timeout_seconds: int = Field(gt=0)
    repetitions: int = Field(ge=1, le=20)
    assertions: list[AssertionSpec] = Field(min_length=1)
    required_sensor_ids: list[str] = Field(default_factory=list)
    executor_must_differ_from_action_executor: bool = True
    on_missing_observation: Literal["INCONCLUSIVE", "FAIL"] = "INCONCLUSIVE"


class VerificationSpec(Contract):
    object_type: Literal["VerificationSpec"] = "VerificationSpec"
    verification_spec_id: str
    scenario_id: str
    scenario_version: str
    objective_type: Literal["DETECTION", "CONTAINMENT", "REMEDIATION", "RECOVERY", "CLEANUP"]
    checks: list[VerificationCheckSpec] = Field(min_length=3)
    aggregation_rule: Literal["THREE_DIMENSION_STRICT"] = "THREE_DIMENSION_STRICT"

    @model_validator(mode="after")
    def three_dimensions(self):
        if {c.dimension for c in self.checks} != {"SECURITY", "BUSINESS", "OBSERVATION"}:
            raise ValueError("verification spec requires security, business and observation checks")
        return self


def expected_verdict(security: Verdict | str, business: Verdict | str, observation: Verdict | str) -> Verdict:
    if security == "FAIL" or business == "FAIL": return Verdict.FAIL
    if security == "PASS" and business == "PASS" and observation == "PASS": return Verdict.PASS
    return Verdict.INCONCLUSIVE


class VerificationResult(Contract):
    object_type: Literal["VerificationResult"] = "VerificationResult"
    verification_id: str
    verification_spec_id: str
    incident_id: str
    environment_id: str
    action_id: str | None
    validation_run_id: str
    objective_type: Literal["DETECTION", "CONTAINMENT", "REMEDIATION", "RECOVERY", "CLEANUP"]
    claim: str
    target_ids: list[str] = Field(min_length=1)
    scope_id: str
    scenario_version: str
    started_at: AwareDatetime
    finished_at: AwareDatetime
    valid_until: AwareDatetime
    security_status: Verdict
    business_status: Verdict
    observation_status: Verdict
    status: Verdict
    evidence_ids: list[str] = Field(min_length=1)
    expected_result: str
    observed_result: str
    residual_risks: list[str]
    recommended_next_step: str

    @model_validator(mode="after")
    def constraints(self):
        if self.finished_at < self.started_at or self.valid_until < self.finished_at: raise ValueError("invalid verification time interval")
        if self.status != expected_verdict(self.security_status, self.business_status, self.observation_status):
            raise ValueError("overall verdict violates three-check semantics")
        return self


class ValidationScenario(Contract):
    object_type: Literal["ValidationScenario"] = "ValidationScenario"
    scenario_id: str
    version: str
    implementation_status: Literal["DESIGN_ONLY", "LAB_VERIFIED"]
    objective: str
    environment_id: str
    scope_id: str
    preconditions: list[str]
    trigger_steps: list[str]
    expected_events: list[str]
    verification_spec_id: str
    cleanup_steps: list[str]
    stop_conditions: list[str]
    config_is_measured_performance: Literal[False] = False


class ValidationRun(Contract):
    object_type: Literal["ValidationRun"] = "ValidationRun"
    run_id: str
    scenario_id: str
    scenario_version: str
    environment_id: str
    scope_id: str
    registered_by: str
    trusted_registration: bool
    started_at: AwareDatetime
    expires_at: AwareDatetime
    expected_event_types: list[str]
    allowed_side_effects: list[str]
    cleanup_policy_id: str
    data_origin: Literal["SYNTHETIC", "OBSERVED"]


class PolicySnapshot(Contract):
    object_type: Literal["PolicySnapshot"] = "PolicySnapshot"
    policy_id: str
    version: str
    environment_id: str
    high_impact_requires_human: Literal[True] = True
    r5_auto_allowed: Literal[False] = False
    load_can_expand_permissions: Literal[False] = False
    allowed_capability_ids: list[str]
    valid_until: AwareDatetime
    max_replans: int = Field(ge=0)
    max_model_calls: int = Field(ge=1)
    max_active_calls: int = Field(ge=1)
    max_elapsed_seconds: int = Field(ge=1)


class AuditEntry(Contract):
    object_type: Literal["AuditEntry"] = "AuditEntry"
    audit_id: str
    trace_id: str
    environment_id: str
    actor_type: Literal["HUMAN", "SERVICE", "MODEL", "WORKER"]
    actor_id: str
    object_kind: str
    object_id: str
    operation: str
    reason: str
    timestamp: AwareDatetime
    previous_entry_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    integrity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class OutboxMessage(Contract):
    object_type: Literal["OutboxMessage"] = "OutboxMessage"
    message_id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload_ref: str
    created_at: AwareDatetime
    published_at: AwareDatetime | None = None
    attempt_count: int = Field(ge=0)


CONTRACTS = {c.__name__: c for c in (
    EnvironmentProfile, ResourceRef, ScopeDefinition, NormalizedEvent, EventGroup, CorrelationDecision,
    Evidence, SensorHealth, StateEntity, StateRelation, SecurityIncident, ContextBundle, WorkerLease,
    Task, AIPlan, ModelRun, CapabilityManifest, CapabilityHealth, ActionRequest, ApprovalRecord,
    AuthorizationContext, AuthorizationDecision, ActionAttempt, VerificationSpec, VerificationResult,
    ValidationScenario, ValidationRun, PolicySnapshot, AuditEntry, OutboxMessage,
)}
```


# 状态迁移

```json
{
  "version": "2026.09.12-ai.5",
  "note": "guards require runtime implementation; this file only defines legal transitions",
  "machines": {
    "Incident": {
      "states": [
        "NEW",
        "TRIAGED",
        "INVESTIGATING",
        "PLANNED",
        "WAITING_APPROVAL",
        "EXECUTING",
        "VERIFYING",
        "CONTAINED",
        "RESOLVED",
        "CLOSED",
        "HUMAN_REVIEW",
        "REOPENED"
      ],
      "initial": "NEW",
      "transitions": [
        {
          "from": "NEW",
          "event": "triage",
          "to": "TRIAGED",
          "guard": "schema and origin checked"
        },
        {
          "from": "TRIAGED",
          "event": "investigate",
          "to": "INVESTIGATING",
          "guard": "scope-bound evidence lookup"
        },
        {
          "from": "INVESTIGATING",
          "event": "plan_validated",
          "to": "PLANNED",
          "guard": "valid evidence, capability, DAG and budget"
        },
        {
          "from": "PLANNED",
          "event": "approval_required",
          "to": "WAITING_APPROVAL",
          "guard": "policy requires exact approval"
        },
        {
          "from": "WAITING_APPROVAL",
          "event": "approval_rejected",
          "to": "HUMAN_REVIEW",
          "guard": "rejection gives no containment evidence"
        },
        {
          "from": "WAITING_APPROVAL",
          "event": "approval_expired",
          "to": "INVESTIGATING",
          "guard": "refresh state and authorization"
        },
        {
          "from": "WAITING_APPROVAL",
          "event": "approval_granted",
          "to": "PLANNED",
          "guard": "digest and expiry match; dispatch must recheck"
        },
        {
          "from": "PLANNED",
          "event": "dispatch",
          "to": "EXECUTING",
          "guard": "fresh authorization and durable action intent"
        },
        {
          "from": "EXECUTING",
          "event": "ready_for_verification",
          "to": "VERIFYING",
          "guard": "execution resolved; never assume effect from receipt"
        },
        {
          "from": "EXECUTING",
          "event": "outcome_unresolved",
          "to": "HUMAN_REVIEW",
          "guard": "unknown action requires reconcile"
        },
        {
          "from": "VERIFYING",
          "event": "containment_pass",
          "to": "CONTAINED",
          "guard": "security/business/observation pass for containment"
        },
        {
          "from": "VERIFYING",
          "event": "remediation_pass",
          "to": "RESOLVED",
          "guard": "remediation and closure preconditions verified"
        },
        {
          "from": "VERIFYING",
          "event": "verification_fail",
          "to": "INVESTIGATING",
          "guard": "budget available; diagnose trustworthy failure"
        },
        {
          "from": "VERIFYING",
          "event": "observation_missing",
          "to": "INVESTIGATING",
          "guard": "repair observation first"
        },
        {
          "from": "VERIFYING",
          "event": "budget_exhausted",
          "to": "HUMAN_REVIEW",
          "guard": "no unsafe repeated action"
        },
        {
          "from": "CONTAINED",
          "event": "control_expires",
          "to": "INVESTIGATING",
          "guard": "root cause may persist"
        },
        {
          "from": "CONTAINED",
          "event": "plan_remediation",
          "to": "PLANNED",
          "guard": "new plan and authorization"
        },
        {
          "from": "CONTAINED",
          "event": "new_risk",
          "to": "INVESTIGATING",
          "guard": "new conflicting or path evidence"
        },
        {
          "from": "RESOLVED",
          "event": "closure_approved",
          "to": "CLOSED",
          "guard": "closure evidence fresh; no unresolved or overdue owned effects"
        },
        {
          "from": "RESOLVED",
          "event": "evidence_expired",
          "to": "INVESTIGATING",
          "guard": "revalidate"
        },
        {
          "from": "INVESTIGATING",
          "event": "manual_disposition",
          "to": "CLOSED",
          "guard": "documented false positive/duplicate/risk acceptance; no fake PASS"
        },
        {
          "from": "HUMAN_REVIEW",
          "event": "manual_disposition",
          "to": "CLOSED",
          "guard": "explicit recorded reason and residual risk owner"
        },
        {
          "from": "HUMAN_REVIEW",
          "event": "resume",
          "to": "INVESTIGATING",
          "guard": "new evidence or authorization"
        },
        {
          "from": "CLOSED",
          "event": "new_related_evidence",
          "to": "REOPENED",
          "guard": "preserve previous closure audit"
        },
        {
          "from": "REOPENED",
          "event": "resume",
          "to": "INVESTIGATING",
          "guard": "new handling cycle"
        }
      ]
    },
    "Task": {
      "states": [
        "QUEUED",
        "BLOCKED",
        "WAITING_APPROVAL",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
        "CANCELLED",
        "TIMED_OUT"
      ],
      "initial": "QUEUED",
      "transitions": [
        {
          "from": "QUEUED",
          "event": "dependencies_pending",
          "to": "BLOCKED",
          "guard": "dependency unresolved"
        },
        {
          "from": "BLOCKED",
          "event": "dependencies_ready",
          "to": "QUEUED",
          "guard": "all dependencies completed"
        },
        {
          "from": "QUEUED",
          "event": "needs_approval",
          "to": "WAITING_APPROVAL",
          "guard": "policy"
        },
        {
          "from": "WAITING_APPROVAL",
          "event": "approved",
          "to": "QUEUED",
          "guard": "approval still valid"
        },
        {
          "from": "WAITING_APPROVAL",
          "event": "rejected",
          "to": "CANCELLED",
          "guard": "no execution"
        },
        {
          "from": "QUEUED",
          "event": "claim",
          "to": "RUNNING",
          "guard": "valid lease"
        },
        {
          "from": "RUNNING",
          "event": "output_valid",
          "to": "SUCCEEDED",
          "guard": "task output contract met, not incident closure"
        },
        {
          "from": "RUNNING",
          "event": "known_failure",
          "to": "FAILED",
          "guard": "failure evidence"
        },
        {
          "from": "RUNNING",
          "event": "timeout",
          "to": "TIMED_OUT",
          "guard": "side effect uncertainty tracked in Action"
        },
        {
          "from": "TIMED_OUT",
          "event": "retry",
          "to": "QUEUED",
          "guard": "budget and reconciliation allow retry"
        },
        {
          "from": "FAILED",
          "event": "retry",
          "to": "QUEUED",
          "guard": "budget and safe retry"
        },
        {
          "from": "QUEUED",
          "event": "cancel",
          "to": "CANCELLED",
          "guard": "authorized stop"
        },
        {
          "from": "BLOCKED",
          "event": "cancel",
          "to": "CANCELLED",
          "guard": "authorized stop"
        },
        {
          "from": "RUNNING",
          "event": "cancel_confirmed",
          "to": "CANCELLED",
          "guard": "stop confirmed; action effect remains separately tracked"
        }
      ]
    },
    "Action": {
      "states": [
        "PROPOSED",
        "WAITING_APPROVAL",
        "AUTHORIZED",
        "DISPATCHED",
        "EXECUTING",
        "EXECUTED",
        "EXECUTION_UNKNOWN",
        "RECONCILING",
        "COMPENSATING",
        "COMPENSATED",
        "COMPENSATION_FAILED",
        "NEEDS_MANUAL",
        "DENIED",
        "EXPIRED",
        "CANCELLED",
        "FAILED"
      ],
      "initial": "PROPOSED",
      "transitions": [
        {
          "from": "PROPOSED",
          "event": "cancel",
          "to": "CANCELLED",
          "guard": "no dispatch or side effect"
        },
        {
          "from": "WAITING_APPROVAL",
          "event": "cancel",
          "to": "CANCELLED",
          "guard": "no execution"
        },
        {
          "from": "PROPOSED",
          "event": "needs_approval",
          "to": "WAITING_APPROVAL",
          "guard": "policy decision"
        },
        {
          "from": "PROPOSED",
          "event": "allowed",
          "to": "AUTHORIZED",
          "guard": "matching current policy and scope"
        },
        {
          "from": "PROPOSED",
          "event": "denied",
          "to": "DENIED",
          "guard": "hard rule"
        },
        {
          "from": "WAITING_APPROVAL",
          "event": "approved",
          "to": "AUTHORIZED",
          "guard": "matching digest and valid approval"
        },
        {
          "from": "WAITING_APPROVAL",
          "event": "rejected",
          "to": "DENIED",
          "guard": "no side effect"
        },
        {
          "from": "WAITING_APPROVAL",
          "event": "expired",
          "to": "EXPIRED",
          "guard": "approval/action validity ended"
        },
        {
          "from": "AUTHORIZED",
          "event": "dispatch",
          "to": "DISPATCHED",
          "guard": "recheck current scope/state/lease/approval"
        },
        {
          "from": "AUTHORIZED",
          "event": "stale",
          "to": "EXPIRED",
          "guard": "must create or reauthorize updated request"
        },
        {
          "from": "AUTHORIZED",
          "event": "cancel",
          "to": "CANCELLED",
          "guard": "no side effect started"
        },
        {
          "from": "DISPATCHED",
          "event": "started",
          "to": "EXECUTING",
          "guard": "current fencing generation"
        },
        {
          "from": "DISPATCHED",
          "event": "lost_ack",
          "to": "EXECUTION_UNKNOWN",
          "guard": "may have reached device"
        },
        {
          "from": "EXECUTING",
          "event": "receipt_applied",
          "to": "EXECUTED",
          "guard": "execution evidence only"
        },
        {
          "from": "EXECUTING",
          "event": "timeout",
          "to": "EXECUTION_UNKNOWN",
          "guard": "cannot prove no effect"
        },
        {
          "from": "EXECUTING",
          "event": "known_no_effect_failure",
          "to": "FAILED",
          "guard": "no side effect confirmed"
        },
        {
          "from": "EXECUTION_UNKNOWN",
          "event": "query",
          "to": "RECONCILING",
          "guard": "authorized status query"
        },
        {
          "from": "RECONCILING",
          "event": "confirmed_applied",
          "to": "EXECUTED",
          "guard": "real device state matches owned request"
        },
        {
          "from": "RECONCILING",
          "event": "confirmed_not_applied",
          "to": "AUTHORIZED",
          "guard": "same immutable request, valid new authorization and budget"
        },
        {
          "from": "RECONCILING",
          "event": "unresolved",
          "to": "NEEDS_MANUAL",
          "guard": "no blind retry"
        },
        {
          "from": "RECONCILING",
          "event": "partial",
          "to": "COMPENSATING",
          "guard": "authorized owned compensation"
        },
        {
          "from": "EXECUTED",
          "event": "owned_expiry_or_rollback",
          "to": "COMPENSATING",
          "guard": "preauthorized cleanup and conflict check"
        },
        {
          "from": "COMPENSATING",
          "event": "cleanup_confirmed",
          "to": "COMPENSATED",
          "guard": "independent cleanup/state evidence"
        },
        {
          "from": "COMPENSATING",
          "event": "cleanup_failed",
          "to": "COMPENSATION_FAILED",
          "guard": "retain residual effect"
        },
        {
          "from": "COMPENSATION_FAILED",
          "event": "escalate",
          "to": "NEEDS_MANUAL",
          "guard": "human review"
        },
        {
          "from": "NEEDS_MANUAL",
          "event": "recheck",
          "to": "RECONCILING",
          "guard": "explicit authorized reconciliation"
        }
      ]
    }
  }
}
```


# 合成示例：golden_chain.json

```json
{
  "data_origin": "SYNTHETIC",
  "description": "一条假设运行后的合成快照，用来检查字段与关系。示例HEALTHY/EXECUTED不是实际运行证据；必须完成环境上线检查后才能真实分发。",
  "objects": [
    {
      "object_type": "NormalizedEvent",
      "event_id": "evt-net",
      "environment_id": "lab-zhiyu-01",
      "source_type": "suricata",
      "collector_id": "sensor-suricata",
      "origin_event_id": "net-origin-001",
      "provenance_group": "network-origin-001",
      "source_timestamp": "2026-09-12T10:00:10Z",
      "ingested_at": "2026-09-12T10:00:12Z",
      "clock_status": "TRUSTED",
      "event_type": "lab.auth.network",
      "severity_signal": 5,
      "raw_ref": "examples/evidence_payloads.json#/payloads/e-net",
      "parser_version": "parser-design-v1",
      "fingerprint": "291df2fa088572c0d66ebf196fac094bd24a38e1038b600324c6b6f96ee7d072",
      "validation_run_id": "run-synthetic-001",
      "data_origin": "SYNTHETIC",
      "specversion": "1.0",
      "activity_category": "authentication",
      "activity_name": "failed_login",
      "outcome": "FAILURE",
      "actor_resource_id": null,
      "source_resource_ids": [
        "validation-a"
      ],
      "target_resource_ids": [
        "target-a"
      ],
      "observables": [
        {
          "observable_type": "IP",
          "value": "10.77.30.10",
          "role": "SOURCE"
        }
      ],
      "mapping_version": "zhiyu-security-map-v1"
    },
    {
      "object_type": "NormalizedEvent",
      "event_id": "evt-app",
      "environment_id": "lab-zhiyu-01",
      "source_type": "wazuh_application_log",
      "collector_id": "sensor-wazuh",
      "origin_event_id": "app-origin-001",
      "provenance_group": "application-origin-001",
      "source_timestamp": "2026-09-12T10:00:10Z",
      "ingested_at": "2026-09-12T10:00:12Z",
      "clock_status": "TRUSTED",
      "event_type": "lab.auth.failure",
      "severity_signal": 5,
      "raw_ref": "examples/evidence_payloads.json#/payloads/e-app",
      "parser_version": "parser-design-v1",
      "fingerprint": "c38a16b65e8b4529929a1fdfe9e72a29ca1f8759a6c3fa15879a20d4544f8ba9",
      "validation_run_id": "run-synthetic-001",
      "data_origin": "SYNTHETIC",
      "specversion": "1.0",
      "activity_category": "authentication",
      "activity_name": "failed_login",
      "outcome": "FAILURE",
      "actor_resource_id": null,
      "source_resource_ids": [
        "validation-a"
      ],
      "target_resource_ids": [
        "target-a"
      ],
      "observables": [
        {
          "observable_type": "IP",
          "value": "10.77.30.10",
          "role": "SOURCE"
        }
      ],
      "mapping_version": "zhiyu-security-map-v1"
    },
    {
      "object_type": "NormalizedEvent",
      "event_id": "evt-net-forwarded",
      "environment_id": "lab-zhiyu-01",
      "source_type": "wazuh_forwarded_suricata",
      "collector_id": "sensor-wazuh",
      "origin_event_id": "net-origin-001",
      "provenance_group": "network-origin-001",
      "source_timestamp": "2026-09-12T10:00:10Z",
      "ingested_at": "2026-09-12T10:00:12Z",
      "clock_status": "TRUSTED",
      "event_type": "lab.auth.network",
      "severity_signal": 5,
      "raw_ref": "examples/evidence_payloads.json#/payloads/e-net",
      "parser_version": "parser-design-v1",
      "fingerprint": "291df2fa088572c0d66ebf196fac094bd24a38e1038b600324c6b6f96ee7d072",
      "validation_run_id": "run-synthetic-001",
      "data_origin": "SYNTHETIC",
      "specversion": "1.0",
      "activity_category": "authentication",
      "activity_name": "failed_login",
      "outcome": "FAILURE",
      "actor_resource_id": null,
      "source_resource_ids": [
        "validation-a"
      ],
      "target_resource_ids": [
        "target-a"
      ],
      "observables": [
        {
          "observable_type": "IP",
          "value": "10.77.30.10",
          "role": "SOURCE"
        }
      ],
      "mapping_version": "zhiyu-security-map-v1"
    },
    {
      "object_type": "Evidence",
      "evidence_id": "e-net",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "source_event_ids": [
        "evt-net"
      ],
      "provenance_group": "network-origin-001",
      "claim_kind": "OBSERVATION",
      "observed_at": "2026-09-12T10:00:10Z",
      "valid_until": "2026-09-12T10:06:00Z",
      "content_ref": "examples/evidence_payloads.json#/payloads/e-net",
      "integrity_hash": "f4ae6f4c66e84181e1e972c902cc08fa0c4cf5f067fd114297bb5669fa49dac1",
      "trust_status": "VERIFIED_ORIGIN",
      "supports": [
        "synthetic-scenario-observation"
      ],
      "contradicts": [],
      "data_origin": "SYNTHETIC",
      "collected_at": "2026-09-12T10:00:10Z",
      "collector_id": "collector-synthetic",
      "collection_method": "synthetic_fixture"
    },
    {
      "object_type": "Evidence",
      "evidence_id": "e-app",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "source_event_ids": [
        "evt-app"
      ],
      "provenance_group": "application-origin-001",
      "claim_kind": "OBSERVATION",
      "observed_at": "2026-09-12T10:00:10Z",
      "valid_until": "2026-09-12T10:06:00Z",
      "content_ref": "examples/evidence_payloads.json#/payloads/e-app",
      "integrity_hash": "61e8a8aa5ffa9f9fa78bfd39ee0c1287b5cd8dd24e907e7438e025d6fc620429",
      "trust_status": "VERIFIED_ORIGIN",
      "supports": [
        "synthetic-scenario-observation"
      ],
      "contradicts": [],
      "data_origin": "SYNTHETIC",
      "collected_at": "2026-09-12T10:00:10Z",
      "collector_id": "collector-synthetic",
      "collection_method": "synthetic_fixture"
    },
    {
      "object_type": "Evidence",
      "evidence_id": "e-state",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "source_event_ids": [],
      "provenance_group": "e-state-independent",
      "claim_kind": "OBSERVATION",
      "observed_at": "2026-09-12T10:00:00Z",
      "valid_until": "2026-09-12T10:06:00Z",
      "content_ref": "examples/evidence_payloads.json#/payloads/e-state",
      "integrity_hash": "0bf8f0852035d06eb7611d84be8de13ea8aba31e17308e5a5e86397e22d7c585",
      "trust_status": "VERIFIED_ORIGIN",
      "supports": [
        "synthetic-scenario-observation"
      ],
      "contradicts": [],
      "data_origin": "SYNTHETIC",
      "collected_at": "2026-09-12T10:00:00Z",
      "collector_id": "collector-synthetic",
      "collection_method": "synthetic_fixture"
    },
    {
      "object_type": "Evidence",
      "evidence_id": "e-control",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "source_event_ids": [],
      "provenance_group": "e-control-independent",
      "claim_kind": "OBSERVATION",
      "observed_at": "2026-09-12T10:01:15Z",
      "valid_until": "2026-09-12T10:06:00Z",
      "content_ref": "examples/evidence_payloads.json#/payloads/e-control",
      "integrity_hash": "92a4762ba120cf2db15baf1b8d0aa63b308e4d06845f1791fec53b27d65dd7cd",
      "trust_status": "VERIFIED_ORIGIN",
      "supports": [
        "synthetic-scenario-observation"
      ],
      "contradicts": [],
      "data_origin": "SYNTHETIC",
      "collected_at": "2026-09-12T10:01:15Z",
      "collector_id": "collector-synthetic",
      "collection_method": "synthetic_fixture"
    },
    {
      "object_type": "Evidence",
      "evidence_id": "e-probe-security",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "source_event_ids": [],
      "provenance_group": "e-probe-security-independent",
      "claim_kind": "OBSERVATION",
      "observed_at": "2026-09-12T10:01:25Z",
      "valid_until": "2026-09-12T10:06:00Z",
      "content_ref": "examples/evidence_payloads.json#/payloads/e-probe-security",
      "integrity_hash": "460426ccf0accdd5fe6f63f8b6412528be16f486c5aa913008b1c4460ef92acb",
      "trust_status": "VERIFIED_ORIGIN",
      "supports": [
        "synthetic-scenario-observation"
      ],
      "contradicts": [],
      "data_origin": "SYNTHETIC",
      "collected_at": "2026-09-12T10:01:25Z",
      "collector_id": "collector-synthetic",
      "collection_method": "synthetic_fixture"
    },
    {
      "object_type": "Evidence",
      "evidence_id": "e-probe-business",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "source_event_ids": [],
      "provenance_group": "e-probe-business-independent",
      "claim_kind": "OBSERVATION",
      "observed_at": "2026-09-12T10:01:25Z",
      "valid_until": "2026-09-12T10:06:00Z",
      "content_ref": "examples/evidence_payloads.json#/payloads/e-probe-business",
      "integrity_hash": "94baf68d0328bd0618358df33182dbd54551ac59d48c5ba1fe8158fc45db2154",
      "trust_status": "VERIFIED_ORIGIN",
      "supports": [
        "synthetic-scenario-observation"
      ],
      "contradicts": [],
      "data_origin": "SYNTHETIC",
      "collected_at": "2026-09-12T10:01:25Z",
      "collector_id": "collector-synthetic",
      "collection_method": "synthetic_fixture"
    },
    {
      "object_type": "Evidence",
      "evidence_id": "e-observation",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "source_event_ids": [],
      "provenance_group": "e-observation-independent",
      "claim_kind": "OBSERVATION",
      "observed_at": "2026-09-12T10:01:25Z",
      "valid_until": "2026-09-12T10:06:00Z",
      "content_ref": "examples/evidence_payloads.json#/payloads/e-observation",
      "integrity_hash": "eebf495c87db30da938fa4c644aa2aa999d4cbec64dd3e5ee9b475a58e2d7500",
      "trust_status": "VERIFIED_ORIGIN",
      "supports": [
        "synthetic-scenario-observation"
      ],
      "contradicts": [],
      "data_origin": "SYNTHETIC",
      "collected_at": "2026-09-12T10:01:25Z",
      "collector_id": "collector-synthetic",
      "collection_method": "synthetic_fixture"
    },
    {
      "object_type": "SensorHealth",
      "sensor_id": "sensor-suricata",
      "environment_id": "lab-zhiyu-01",
      "status": "HEALTHY",
      "last_heartbeat_at": "2026-09-12T10:01:00Z",
      "last_event_at": "2026-09-12T10:00:12Z",
      "lag_seconds": 2.0,
      "lost_event_count": 0,
      "coverage_scope_ids": [
        "scope-lab-web"
      ],
      "coverage_validated": true,
      "config_version": "sensor-config-design-v1"
    },
    {
      "object_type": "SensorHealth",
      "sensor_id": "sensor-wazuh",
      "environment_id": "lab-zhiyu-01",
      "status": "HEALTHY",
      "last_heartbeat_at": "2026-09-12T10:01:00Z",
      "last_event_at": "2026-09-12T10:00:12Z",
      "lag_seconds": 2.0,
      "lost_event_count": 0,
      "coverage_scope_ids": [
        "scope-lab-web"
      ],
      "coverage_validated": true,
      "config_version": "sensor-config-design-v1"
    },
    {
      "object_type": "Task",
      "task_id": "task-check",
      "incident_id": "inc-synthetic-001",
      "environment_id": "lab-zhiyu-01",
      "dependencies": [],
      "capability_id": "lab.template.check",
      "capability_version": "1.0-design",
      "scope_id": "scope-lab-web",
      "parameters": {
        "template_id": "lab-service-marker-v1"
      },
      "status": "SUCCEEDED",
      "priority": "P2",
      "timeout_seconds": 30,
      "max_attempts": 2,
      "expected_output": "evidence for current lab service identity and scope",
      "evidence_ids": [
        "e-net",
        "e-app",
        "e-state"
      ],
      "target_resource_ids": [
        "target-a"
      ],
      "attempt_count": 1,
      "created_at": "2026-09-12T10:00:20Z",
      "queued_at": "2026-09-12T10:00:20Z",
      "claimed_at": "2026-09-12T10:00:21Z",
      "started_at": "2026-09-12T10:00:21Z",
      "finished_at": "2026-09-12T10:00:25Z",
      "active_lease_id": null,
      "worker_id": "worker-lab-01"
    },
    {
      "object_type": "Task",
      "task_id": "task-block",
      "incident_id": "inc-synthetic-001",
      "environment_id": "lab-zhiyu-01",
      "dependencies": [
        "task-check"
      ],
      "capability_id": "lab.gateway.temporary_block",
      "capability_version": "1.0-design",
      "scope_id": "scope-lab-web",
      "parameters": {
        "operation": "ensure_temporary_block",
        "rule_namespace": "zhiyu_lab"
      },
      "status": "SUCCEEDED",
      "priority": "P2",
      "timeout_seconds": 30,
      "max_attempts": 2,
      "expected_output": "owned rule receipt or execution_unknown",
      "evidence_ids": [
        "e-net",
        "e-app",
        "e-state"
      ],
      "target_resource_ids": [
        "target-a"
      ],
      "attempt_count": 1,
      "created_at": "2026-09-12T10:01:00Z",
      "queued_at": "2026-09-12T10:01:00Z",
      "claimed_at": "2026-09-12T10:01:05Z",
      "started_at": "2026-09-12T10:01:05Z",
      "finished_at": "2026-09-12T10:01:15Z",
      "active_lease_id": null,
      "worker_id": "worker-lab-01"
    },
    {
      "object_type": "Task",
      "task_id": "task-verify",
      "incident_id": "inc-synthetic-001",
      "environment_id": "lab-zhiyu-01",
      "dependencies": [
        "task-block"
      ],
      "capability_id": "lab.independent.verify",
      "capability_version": "1.0-design",
      "scope_id": "scope-lab-web",
      "parameters": {
        "objective": "CONTAINMENT"
      },
      "status": "SUCCEEDED",
      "priority": "P2",
      "timeout_seconds": 30,
      "max_attempts": 2,
      "expected_output": "security/business/observation verification and residual risk",
      "evidence_ids": [
        "e-net",
        "e-app",
        "e-state"
      ],
      "target_resource_ids": [
        "target-a"
      ],
      "attempt_count": 1,
      "created_at": "2026-09-12T10:01:20Z",
      "queued_at": "2026-09-12T10:01:20Z",
      "claimed_at": "2026-09-12T10:01:21Z",
      "started_at": "2026-09-12T10:01:21Z",
      "finished_at": "2026-09-12T10:01:30Z",
      "active_lease_id": null,
      "worker_id": "worker-lab-01"
    },
    {
      "object_type": "StateEntity",
      "entity_id": "target-a",
      "environment_id": "lab-zhiyu-01",
      "entity_type": "service_host",
      "state_version": 7,
      "attributes": {
        "address": "10.77.20.10",
        "service_port": 8080,
        "address_binding_version": 1,
        "business_criticality": "lab_only"
      },
      "claim_kind": "OBSERVATION",
      "evidence_ids": [
        "e-state"
      ],
      "observed_at": "2026-09-12T10:00:00Z",
      "valid_until": "2026-09-12T10:05:00Z"
    },
    {
      "object_type": "StateRelation",
      "relation_id": "rel-target-control",
      "environment_id": "lab-zhiyu-01",
      "source_entity_id": "target-a",
      "destination_entity_id": "lab-gateway",
      "relation_type": "protected_by",
      "state_version": 7,
      "evidence_ids": [
        "e-state"
      ],
      "valid_from": "2026-09-12T10:00:00Z",
      "valid_until": "2026-09-12T10:05:00Z"
    },
    {
      "object_type": "SecurityIncident",
      "incident_id": "inc-synthetic-001",
      "environment_id": "lab-zhiyu-01",
      "title": "合成认证异常的受控遏制演示",
      "status": "CONTAINED",
      "priority": "P2",
      "affected_asset_ids": [
        "target-a"
      ],
      "related_event_ids": [
        "evt-net",
        "evt-app",
        "evt-net-forwarded"
      ],
      "evidence_ids": [
        "e-net",
        "e-app",
        "e-state",
        "e-control",
        "e-probe-security",
        "e-probe-business",
        "e-observation"
      ],
      "state_version": 8,
      "open_action_ids": [
        "act-synthetic-block-001"
      ],
      "residual_risks": [
        "temporary control expires; root cause not remediated"
      ],
      "closure_type": null,
      "closure_evidence_ids": [],
      "event_group_ids": [
        "eg-auth-001"
      ],
      "first_observed_at": "2026-09-12T10:00:10Z",
      "created_at": "2026-09-12T10:00:15Z",
      "updated_at": "2026-09-12T10:01:30Z",
      "triaged_at": "2026-09-12T10:00:20Z",
      "investigation_started_at": "2026-09-12T10:00:21Z",
      "contained_at": "2026-09-12T10:01:30Z",
      "resolved_at": null,
      "closed_at": null
    },
    {
      "object_type": "ContextBundle",
      "context_id": "ctx-001",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "state_version": 7,
      "evidence_ids": [
        "e-net",
        "e-app",
        "e-state"
      ],
      "excluded_evidence_reasons": {},
      "unresolved_conflicts": [
        "distinguish expected validation from unexpected activity"
      ],
      "sensor_health_ids": [
        "sensor-suricata",
        "sensor-wazuh"
      ],
      "capability_ids": [
        "lab.template.check",
        "lab.gateway.temporary_block",
        "lab.independent.verify"
      ],
      "policy_version": "policy-v1",
      "token_budget": 6000,
      "data_classification": "INTERNAL",
      "egress_allowed": false,
      "summary_version": "summary-v1",
      "prompt_version": "planner-design-v1",
      "created_at": "2026-09-12T10:00:25Z"
    },
    {
      "object_type": "AIPlan",
      "plan_id": "plan-001",
      "incident_id": "inc-synthetic-001",
      "environment_id": "lab-zhiyu-01",
      "context_id": "ctx-001",
      "hypotheses": [
        {
          "hypothesis_id": "h1",
          "claim": "pattern matches failed authentication; consult trusted run registration before attribution",
          "evidence_ids": [
            "e-net",
            "e-app"
          ],
          "counter_evidence_ids": [],
          "missing_evidence": [
            "verify service baseline and control path"
          ],
          "model_confidence": 0.8,
          "calibration_status": "UNCALIBRATED"
        },
        {
          "hypothesis_id": "h2",
          "claim": "legitimate user mistakes are an alternative explanation",
          "evidence_ids": [
            "e-app"
          ],
          "counter_evidence_ids": [
            "e-net"
          ],
          "missing_evidence": [
            "compare identity and frequency with baseline"
          ],
          "model_confidence": null,
          "calibration_status": "UNCALIBRATED"
        },
        {
          "hypothesis_id": "h3",
          "claim": "forwarded duplicate records may inflate apparent event count",
          "evidence_ids": [
            "e-net"
          ],
          "counter_evidence_ids": [
            "e-app"
          ],
          "missing_evidence": [
            "verify provenance-group deduplication"
          ],
          "model_confidence": null,
          "calibration_status": "UNCALIBRATED"
        }
      ],
      "tasks": [
        {
          "object_type": "Task",
          "task_id": "task-check",
          "incident_id": "inc-synthetic-001",
          "environment_id": "lab-zhiyu-01",
          "dependencies": [],
          "capability_id": "lab.template.check",
          "capability_version": "1.0-design",
          "scope_id": "scope-lab-web",
          "parameters": {
            "template_id": "lab-service-marker-v1"
          },
          "status": "SUCCEEDED",
          "priority": "P2",
          "timeout_seconds": 30,
          "max_attempts": 2,
          "expected_output": "evidence for current lab service identity and scope",
          "evidence_ids": [
            "e-net",
            "e-app",
            "e-state"
          ],
          "target_resource_ids": [
            "target-a"
          ],
          "attempt_count": 1,
          "created_at": "2026-09-12T10:00:20Z",
          "queued_at": "2026-09-12T10:00:20Z",
          "claimed_at": "2026-09-12T10:00:21Z",
          "started_at": "2026-09-12T10:00:21Z",
          "finished_at": "2026-09-12T10:00:25Z",
          "active_lease_id": null,
          "worker_id": "worker-lab-01"
        },
        {
          "object_type": "Task",
          "task_id": "task-block",
          "incident_id": "inc-synthetic-001",
          "environment_id": "lab-zhiyu-01",
          "dependencies": [
            "task-check"
          ],
          "capability_id": "lab.gateway.temporary_block",
          "capability_version": "1.0-design",
          "scope_id": "scope-lab-web",
          "parameters": {
            "operation": "ensure_temporary_block",
            "rule_namespace": "zhiyu_lab"
          },
          "status": "SUCCEEDED",
          "priority": "P2",
          "timeout_seconds": 30,
          "max_attempts": 2,
          "expected_output": "owned rule receipt or execution_unknown",
          "evidence_ids": [
            "e-net",
            "e-app",
            "e-state"
          ],
          "target_resource_ids": [
            "target-a"
          ],
          "attempt_count": 1,
          "created_at": "2026-09-12T10:01:00Z",
          "queued_at": "2026-09-12T10:01:00Z",
          "claimed_at": "2026-09-12T10:01:05Z",
          "started_at": "2026-09-12T10:01:05Z",
          "finished_at": "2026-09-12T10:01:15Z",
          "active_lease_id": null,
          "worker_id": "worker-lab-01"
        },
        {
          "object_type": "Task",
          "task_id": "task-verify",
          "incident_id": "inc-synthetic-001",
          "environment_id": "lab-zhiyu-01",
          "dependencies": [
            "task-block"
          ],
          "capability_id": "lab.independent.verify",
          "capability_version": "1.0-design",
          "scope_id": "scope-lab-web",
          "parameters": {
            "objective": "CONTAINMENT"
          },
          "status": "SUCCEEDED",
          "priority": "P2",
          "timeout_seconds": 30,
          "max_attempts": 2,
          "expected_output": "security/business/observation verification and residual risk",
          "evidence_ids": [
            "e-net",
            "e-app",
            "e-state"
          ],
          "target_resource_ids": [
            "target-a"
          ],
          "attempt_count": 1,
          "created_at": "2026-09-12T10:01:20Z",
          "queued_at": "2026-09-12T10:01:20Z",
          "claimed_at": "2026-09-12T10:01:21Z",
          "started_at": "2026-09-12T10:01:21Z",
          "finished_at": "2026-09-12T10:01:30Z",
          "active_lease_id": null,
          "worker_id": "worker-lab-01"
        }
      ],
      "stop_conditions": [
        "no new evidence after repeated failure",
        "scope expires",
        "business degradation",
        "budget exhausted"
      ],
      "max_replans": 3,
      "total_model_calls": 1,
      "model_run_id": "modelrun-synthetic-001"
    },
    {
      "object_type": "ActionRequest",
      "action_id": "act-synthetic-block-001",
      "incident_id": "inc-synthetic-001",
      "task_id": "task-block",
      "environment_id": "lab-zhiyu-01",
      "capability_id": "lab.gateway.temporary_block",
      "capability_version": "1.0-design",
      "parameters": {
        "operation": "ensure_temporary_block",
        "rule_namespace": "zhiyu_lab"
      },
      "scope_id": "scope-lab-web",
      "scope_version": "scope-v1",
      "environment_profile_version": "env-v1",
      "policy_version": "policy-v1",
      "expected_state_version": 7,
      "preconditions": [
        "asset binding version 1 still valid",
        "business baseline healthy",
        "no conflicting owners",
        "scope and authorization current"
      ],
      "evidence_ids": [
        "e-net",
        "e-app",
        "e-state"
      ],
      "created_at": "2026-09-12T10:01:00Z",
      "expires_at": "2026-09-12T10:02:00Z",
      "ttl_seconds": 300,
      "idempotency_key": "lab01-inc001-block-001",
      "ownership_tag": "act-synthetic-block-001",
      "rollback_policy_id": "rollback-owned-rule-v1",
      "source": {
        "object_type": "ResourceRef",
        "resource_id": "validation-a",
        "environment_id": "lab-zhiyu-01",
        "resource_type": "HOST",
        "binding_version": 1,
        "locator": {
          "address": "10.77.30.10",
          "os": "Linux"
        },
        "display_name": "Validation-A"
      },
      "target": {
        "object_type": "ResourceRef",
        "resource_id": "target-a",
        "environment_id": "lab-zhiyu-01",
        "resource_type": "NETWORK_ENDPOINT",
        "binding_version": 1,
        "locator": {
          "address": "10.77.20.10",
          "port": 8080,
          "protocol": "TCP"
        },
        "display_name": "Target-A synthetic login service"
      }
    },
    {
      "object_type": "AuthorizationDecision",
      "authorization_id": "authz-001",
      "action_id": "act-synthetic-block-001",
      "action_digest": "99d4a0cda0cc9d54e9374443fb62d91c9f56721125bf192361289b35255d7a44",
      "outcome": "ALLOW",
      "assessed_risk": "R2",
      "business_impact": "LOW",
      "human_approval_required": false,
      "approval_id": null,
      "policy_version": "policy-v1",
      "valid_until": "2026-09-12T10:02:00Z",
      "reasons": [
        "synthetic preauthorized lab source-target-port scope",
        "local recovery capability must be verified before actual dispatch"
      ],
      "authorization_context_id": "authctx-001"
    },
    {
      "object_type": "ActionAttempt",
      "attempt_id": "attempt-001",
      "action_id": "act-synthetic-block-001",
      "status": "EXECUTED",
      "fencing_generation": 1,
      "started_at": "2026-09-12T10:01:10Z",
      "device_receipt_id": "synthetic-rule-001",
      "reconciliation_state": "CONFIRMED_APPLIED",
      "evidence_ids": [
        "e-control"
      ],
      "worker_id": "worker-lab-gateway-01",
      "finished_at": "2026-09-12T10:01:15Z",
      "error_code": null,
      "error_class": null,
      "device_response_hash": "1d4201f410d36def435b38603f6c8ed6f1efc005d7e38faa89ae3cfe18ccc955"
    },
    {
      "object_type": "EventGroup",
      "group_id": "eg-auth-001",
      "environment_id": "lab-zhiyu-01",
      "first_seen_at": "2026-09-12T10:00:10Z",
      "last_seen_at": "2026-09-12T10:00:10Z",
      "member_event_ids": [
        "evt-net",
        "evt-app"
      ],
      "grouping_keys": {
        "source": "validation-a",
        "target": "target-a",
        "category": "authentication"
      },
      "correlation_reasons": [
        "same source and target",
        "same second",
        "authentication semantics"
      ],
      "outlier_event_ids": [
        "evt-net-forwarded"
      ],
      "correlation_confidence": 0.95,
      "rule_version": "corr-rules-v1",
      "algorithm_version": "window-entity-v1"
    },
    {
      "object_type": "CorrelationDecision",
      "decision_id": "corrdec-001",
      "environment_id": "lab-zhiyu-01",
      "input_event_ids": [
        "evt-net",
        "evt-app",
        "evt-net-forwarded"
      ],
      "output_group_id": "eg-auth-001",
      "rules_fired": [
        "dedupe.provenance.v1",
        "window.entity.auth.v1"
      ],
      "merge_reason": "independent network/application observations align; forwarded network copy excluded as duplicate provenance",
      "excluded_event_ids": [
        "evt-net-forwarded"
      ],
      "decision_version": "corrdec-v1",
      "created_at": "2026-09-12T10:00:14Z"
    },
    {
      "object_type": "WorkerLease",
      "lease_id": "lease-task-block-001",
      "task_id": "task-block",
      "worker_id": "worker-lab-01",
      "generation": 1,
      "acquired_at": "2026-09-12T10:01:05Z",
      "expires_at": "2026-09-12T10:01:35Z",
      "renewed_at": null
    },
    {
      "object_type": "ModelRun",
      "run_id": "modelrun-synthetic-001",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "task_id": null,
      "provider": "synthetic",
      "model": "deterministic-fixture",
      "model_revision": "design-v1",
      "prompt_version": "planner-design-v1",
      "context_id": "ctx-001",
      "input_hash": "04bbc1a629385f507a6581f567f28e7dff594f2d6fe0f8158d503a18d5524beb",
      "output_hash": "8541951fa5f90b604efda98d14f6f3dca9668174fc35dbdfb12c5bb9defba412",
      "route_reason": "contract fixture only",
      "fallback_from_run_id": null,
      "started_at": "2026-09-12T10:00:26Z",
      "finished_at": "2026-09-12T10:00:27Z",
      "input_tokens": 100,
      "output_tokens": 50,
      "cached_tokens": 0,
      "latency_ms": 1000,
      "cost_usd": 0.0,
      "schema_valid": true,
      "safety_status": "PASS"
    },
    {
      "object_type": "AuthorizationContext",
      "authorization_context_id": "authctx-001",
      "environment_id": "lab-zhiyu-01",
      "action_id": "act-synthetic-block-001",
      "action_digest": "99d4a0cda0cc9d54e9374443fb62d91c9f56721125bf192361289b35255d7a44",
      "principal_id": "system-planner",
      "principal_role": "CONTROL_PLANE",
      "environment_profile_version": "env-v1",
      "scope_id": "scope-lab-web",
      "scope_version": "scope-v1",
      "capability_id": "lab.gateway.temporary_block",
      "capability_version": "1.0-design",
      "target_resource_id": "target-a",
      "source_resource_id": "validation-a",
      "asset_criticality": "LOW",
      "business_impact": "LOW",
      "evidence_quality": "HIGH",
      "sensor_health_status": "HEALTHY",
      "autonomy_mode": "VALIDATION",
      "load_mode": "NORMAL",
      "requested_risk": "R2",
      "policy_version": "policy-v1",
      "budget_id": "budget-lab-001",
      "created_at": "2026-09-12T10:01:01Z"
    },
    {
      "object_type": "AuditEntry",
      "audit_id": "audit-001",
      "trace_id": "trace-inc-001",
      "environment_id": "lab-zhiyu-01",
      "actor_type": "SERVICE",
      "actor_id": "event-intelligence",
      "object_kind": "SecurityIncident",
      "object_id": "inc-synthetic-001",
      "operation": "CREATE",
      "reason": "synthetic correlation threshold reached",
      "timestamp": "2026-09-12T10:00:15Z",
      "previous_entry_hash": null,
      "integrity_hash": "a0410f98f1359d36d1350ff0844aa2c24f26d3dd4261d3649d7e2735cb742638"
    },
    {
      "object_type": "OutboxMessage",
      "message_id": "outbox-001",
      "aggregate_type": "ActionRequest",
      "aggregate_id": "act-synthetic-block-001",
      "event_type": "ActionAuthorized",
      "payload_ref": "synthetic://action/act-synthetic-block-001",
      "created_at": "2026-09-12T10:01:02Z",
      "published_at": "2026-09-12T10:01:03Z",
      "attempt_count": 1
    }
  ]
}
```


# 合成示例：scenario.json

```json
{
  "data_origin": "SYNTHETIC",
  "description": "设计用例；可信登记字段需由实际服务端身份与Scope验证，客户端填写true不构成授权。",
  "objects": [
    {
      "object_type": "ValidationScenario",
      "scenario_id": "SCN-LAB-AUTH-01",
      "version": "1",
      "implementation_status": "DESIGN_ONLY",
      "objective": "controlled authentication anomaly -> scoped temporary containment -> independent three-check verification",
      "environment_id": "lab-zhiyu-01",
      "scope_id": "scope-lab-web",
      "preconditions": [
        "authorized isolated topology",
        "independent network and application evidence",
        "healthy legitimate operation",
        "locally enforceable TTL demonstrated before automatic actions"
      ],
      "trigger_steps": [
        "register trusted validation run",
        "20 synthetic failed authentication attempts in 60 seconds at <=1 request/second",
        "collect network and application observations",
        "correlate incident and check evidence",
        "authorize source-target-port temporary restriction",
        "verify containment, legitimate business and observation independently"
      ],
      "expected_events": [
        "lab.auth.network",
        "lab.auth.failure"
      ],
      "cleanup_steps": [
        "remove only owned rule after scope/conflict check",
        "verify restored paths and cleanup",
        "preserve unresolved root-cause risk"
      ],
      "stop_conditions": [
        "scope expired or revoked",
        "business health deteriorates",
        "incident or recovery budget exhausted",
        "unknown action outcome must reconcile"
      ],
      "config_is_measured_performance": false,
      "verification_spec_id": "vspec-containment-v1"
    },
    {
      "object_type": "VerificationSpec",
      "verification_spec_id": "vspec-containment-v1",
      "scenario_id": "SCN-LAB-AUTH-01",
      "scenario_version": "1",
      "objective_type": "CONTAINMENT",
      "checks": [
        {
          "check_id": "check-security",
          "dimension": "SECURITY",
          "capability_id": "lab.independent.verify",
          "source_resource_id": "validation-a",
          "target_resource_id": "target-a",
          "timeout_seconds": 10,
          "repetitions": 3,
          "assertions": [
            {
              "field": "path_restricted",
              "operator": "EQUALS",
              "expected": true
            }
          ],
          "required_sensor_ids": [
            "sensor-suricata"
          ],
          "executor_must_differ_from_action_executor": true,
          "on_missing_observation": "INCONCLUSIVE"
        },
        {
          "check_id": "check-business",
          "dimension": "BUSINESS",
          "capability_id": "lab.independent.verify",
          "source_resource_id": "business-probe",
          "target_resource_id": "target-a",
          "timeout_seconds": 10,
          "repetitions": 3,
          "assertions": [
            {
              "field": "legitimate_operation_success",
              "operator": "EQUALS",
              "expected": true
            }
          ],
          "required_sensor_ids": [],
          "executor_must_differ_from_action_executor": true,
          "on_missing_observation": "INCONCLUSIVE"
        },
        {
          "check_id": "check-observation",
          "dimension": "OBSERVATION",
          "capability_id": "lab.independent.verify",
          "source_resource_id": "business-probe",
          "target_resource_id": "target-a",
          "timeout_seconds": 10,
          "repetitions": 1,
          "assertions": [
            {
              "field": "required_paths_valid",
              "operator": "EQUALS",
              "expected": true
            }
          ],
          "required_sensor_ids": [
            "sensor-suricata",
            "sensor-wazuh"
          ],
          "executor_must_differ_from_action_executor": true,
          "on_missing_observation": "INCONCLUSIVE"
        }
      ],
      "aggregation_rule": "THREE_DIMENSION_STRICT"
    },
    {
      "object_type": "ValidationRun",
      "run_id": "run-synthetic-001",
      "scenario_id": "SCN-LAB-AUTH-01",
      "scenario_version": "1",
      "environment_id": "lab-zhiyu-01",
      "scope_id": "scope-lab-web",
      "registered_by": "lab-admin-synthetic",
      "trusted_registration": true,
      "started_at": "2026-09-12T10:00:00Z",
      "expires_at": "2026-09-12T10:20:00Z",
      "expected_event_types": [
        "lab.auth.network",
        "lab.auth.failure"
      ],
      "allowed_side_effects": [
        "one owned temporary source-target-port restriction for 300 seconds"
      ],
      "cleanup_policy_id": "rollback-owned-rule-v1",
      "data_origin": "SYNTHETIC"
    }
  ]
}
```


# 合成示例：verification_cases.json

```json
{
  "data_origin": "SYNTHETIC",
  "description": "四个互斥的反事实分支；不是同一次实际运行的四个先后结果。只有pass分支与主链CONTAINED快照对应。",
  "objects": [
    {
      "object_type": "Evidence",
      "evidence_id": "e-observation-gap",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "source_event_ids": [],
      "provenance_group": "e-observation-gap-independent",
      "claim_kind": "OBSERVATION",
      "observed_at": "2026-09-12T10:01:25Z",
      "valid_until": "2026-09-12T10:06:00Z",
      "content_ref": "examples/evidence_payloads.json#/payloads/e-observation-gap",
      "integrity_hash": "5a670dddf4b7117d82e6c1e70f26357aa4c76b91b78f72f760236f2e2df899d9",
      "trust_status": "VERIFIED_ORIGIN",
      "supports": [
        "synthetic-scenario-observation"
      ],
      "contradicts": [],
      "data_origin": "SYNTHETIC",
      "collected_at": "2026-09-12T10:01:25Z",
      "collector_id": "collector-synthetic",
      "collection_method": "synthetic_fixture"
    },
    {
      "object_type": "Evidence",
      "evidence_id": "e-business-down",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "source_event_ids": [],
      "provenance_group": "e-business-down-independent",
      "claim_kind": "OBSERVATION",
      "observed_at": "2026-09-12T10:01:25Z",
      "valid_until": "2026-09-12T10:06:00Z",
      "content_ref": "examples/evidence_payloads.json#/payloads/e-business-down",
      "integrity_hash": "2e8a353eefebfdace8dcbe362003cf6eb4c7f1533ad813e2a8767f7477648afc",
      "trust_status": "VERIFIED_ORIGIN",
      "supports": [
        "synthetic-scenario-observation"
      ],
      "contradicts": [],
      "data_origin": "SYNTHETIC",
      "collected_at": "2026-09-12T10:01:25Z",
      "collector_id": "collector-synthetic",
      "collection_method": "synthetic_fixture"
    },
    {
      "object_type": "Evidence",
      "evidence_id": "e-probe-security-fail",
      "environment_id": "lab-zhiyu-01",
      "incident_id": "inc-synthetic-001",
      "source_event_ids": [],
      "provenance_group": "e-probe-security-fail-independent",
      "claim_kind": "OBSERVATION",
      "observed_at": "2026-09-12T10:01:25Z",
      "valid_until": "2026-09-12T10:06:00Z",
      "content_ref": "examples/evidence_payloads.json#/payloads/e-probe-security-fail",
      "integrity_hash": "09fac7b61b2d4fae79f855e8f63042461e270b821436824756f879bc7e1fcba5",
      "trust_status": "VERIFIED_ORIGIN",
      "supports": [
        "security_failure"
      ],
      "contradicts": [
        "successful_containment"
      ],
      "data_origin": "SYNTHETIC",
      "collected_at": "2026-09-12T10:01:25Z",
      "collector_id": "collector-synthetic",
      "collection_method": "synthetic_fixture"
    },
    {
      "object_type": "VerificationResult",
      "verification_id": "verify-containment-pass",
      "incident_id": "inc-synthetic-001",
      "environment_id": "lab-zhiyu-01",
      "action_id": "act-synthetic-block-001",
      "validation_run_id": "run-synthetic-001",
      "objective_type": "CONTAINMENT",
      "claim": "only validate the named source-target-port restriction within this interval",
      "target_ids": [
        "target-a"
      ],
      "scope_id": "scope-lab-web",
      "scenario_version": "1",
      "started_at": "2026-09-12T10:01:20Z",
      "finished_at": "2026-09-12T10:01:30Z",
      "valid_until": "2026-09-12T10:05:30Z",
      "security_status": "PASS",
      "business_status": "PASS",
      "observation_status": "PASS",
      "status": "PASS",
      "evidence_ids": [
        "e-probe-security",
        "e-probe-business",
        "e-observation"
      ],
      "expected_result": "scoped anomalous path restricted; legitimate path available; required observation valid",
      "observed_result": "scoped path restricted; legitimate path available; observation healthy",
      "residual_risks": [
        "root cause unremediated",
        "temporary control has finite lifetime"
      ],
      "recommended_next_step": "remain CONTAINED; plan root-cause remediation and TTL review",
      "verification_spec_id": "vspec-containment-v1"
    },
    {
      "object_type": "VerificationResult",
      "verification_id": "verify-observation-gap",
      "incident_id": "inc-synthetic-001",
      "environment_id": "lab-zhiyu-01",
      "action_id": "act-synthetic-block-001",
      "validation_run_id": "run-synthetic-001",
      "objective_type": "CONTAINMENT",
      "claim": "only validate the named source-target-port restriction within this interval",
      "target_ids": [
        "target-a"
      ],
      "scope_id": "scope-lab-web",
      "scenario_version": "1",
      "started_at": "2026-09-12T10:01:20Z",
      "finished_at": "2026-09-12T10:01:30Z",
      "valid_until": "2026-09-12T10:05:30Z",
      "security_status": "INCONCLUSIVE",
      "business_status": "PASS",
      "observation_status": "INCONCLUSIVE",
      "status": "INCONCLUSIVE",
      "evidence_ids": [
        "e-observation-gap",
        "e-probe-business"
      ],
      "expected_result": "scoped anomalous path restricted; legitimate path available; required observation valid",
      "observed_result": "required security observation missing",
      "residual_risks": [
        "root cause unremediated",
        "temporary control has finite lifetime"
      ],
      "recommended_next_step": "repair observation within budget; no closure",
      "verification_spec_id": "vspec-containment-v1"
    },
    {
      "object_type": "VerificationResult",
      "verification_id": "verify-business-fail",
      "incident_id": "inc-synthetic-001",
      "environment_id": "lab-zhiyu-01",
      "action_id": "act-synthetic-block-001",
      "validation_run_id": "run-synthetic-001",
      "objective_type": "CONTAINMENT",
      "claim": "only validate the named source-target-port restriction within this interval",
      "target_ids": [
        "target-a"
      ],
      "scope_id": "scope-lab-web",
      "scenario_version": "1",
      "started_at": "2026-09-12T10:01:20Z",
      "finished_at": "2026-09-12T10:01:30Z",
      "valid_until": "2026-09-12T10:05:30Z",
      "security_status": "PASS",
      "business_status": "FAIL",
      "observation_status": "PASS",
      "status": "FAIL",
      "evidence_ids": [
        "e-probe-security",
        "e-business-down",
        "e-observation"
      ],
      "expected_result": "scoped anomalous path restricted; legitimate path available; required observation valid",
      "observed_result": "restriction also broke legitimate business",
      "residual_risks": [
        "root cause unremediated",
        "temporary control has finite lifetime"
      ],
      "recommended_next_step": "owned compensation if authorized; otherwise immediate human review",
      "verification_spec_id": "vspec-containment-v1"
    },
    {
      "object_type": "VerificationResult",
      "verification_id": "verify-security-fail",
      "incident_id": "inc-synthetic-001",
      "environment_id": "lab-zhiyu-01",
      "action_id": "act-synthetic-block-001",
      "validation_run_id": "run-synthetic-001",
      "objective_type": "CONTAINMENT",
      "claim": "only validate the named source-target-port restriction within this interval",
      "target_ids": [
        "target-a"
      ],
      "scope_id": "scope-lab-web",
      "scenario_version": "1",
      "started_at": "2026-09-12T10:01:20Z",
      "finished_at": "2026-09-12T10:01:30Z",
      "valid_until": "2026-09-12T10:05:30Z",
      "security_status": "FAIL",
      "business_status": "PASS",
      "observation_status": "PASS",
      "status": "FAIL",
      "evidence_ids": [
        "e-probe-security-fail",
        "e-probe-business",
        "e-observation"
      ],
      "expected_result": "scoped anomalous path restricted; legitimate path available; required observation valid",
      "observed_result": "counterfactual: scoped path remains reachable with trustworthy probe",
      "residual_risks": [
        "root cause unremediated",
        "temporary control has finite lifetime"
      ],
      "recommended_next_step": "diagnose and bounded replan",
      "verification_spec_id": "vspec-containment-v1"
    }
  ]
}
```


---

# 智御变更记录

## 2026-09-12｜ai.4：从概念补充转为可接续的工程设计基线

本轮是资料设计更新，没有实际平台代码或性能结果。

1. 重整入口、状态、主题文档、数据契约、状态机、示例与单文件阅读版；修复错误引用，消除旧摘要与新增设计不同步的问题。
2. 保留八层功能与五平面部署、Linux主控、跨平台感知/响应、隔离验证、私有化和完整版扩展。
3. 环境分类拆分部署阶段、资产领域、联网条件和运营模式；继续区分 AutonomyMode 与 LoadMode。
4. 动作按风险/影响/参数分级；R5 与高业务影响不能自动批准。人工审批绑定具体参数摘要及有效期，执行前重新评估。
5. 增加执行结果未知、状态核对、幂等、资源级冲突、租约代次、ownership 补偿、清理失败和持久任务要求。
6. 区分遏制、修复、恢复、检测和清理；验证同时检查安全效果、正常业务、观测有效性。PASS不直接关闭Incident。
7. 明确来源认证与内容真实的区别；增加证据血缘、时间有效性、冲突和未校准模型置信度语义。
8. 增加可信测试运行登记、自响应反馈控制、事件级预算/停止条件和恢复资源预留。
9. 补全有界队列/留存/丢失统计、数据全路径出域、工作流参数保护和站点离线处理。
10. 将第一条演示链收敛为 SCN-LAB-AUTH-01 合成认证异常→临时范围限制→独立安全/业务复测；SCN-LAB-AUTH-02为修复扩展设计。
11. 增加固定编排与AI的公平对照、A01–A15平台验收、M0–M5里程碑。Atomic/CALDERA改为第一条场景非必需的扩展能力，避免无必要地同时集成。
12. 形成可生成 JSON Schema 的 Pydantic 契约、合成样例、包自检与哈希清单；自检不代表平台验收。

## ai.3 保留的关键决策

五平面部署、Linux主控与跨OS数据面、独立Linux/Windows验证池、Durable Workflow、Policy-as-Code、Workload Identity、分层存储、HA/DR与图投影单事实源。ai.4将这些作为按规模选择的完整概念配置，V1仍保持模块化单体。

## ai.2 保留的关键决策

EnvironmentProfile、SensorHealth/Coverage、最小身份/审批、出域控制、版本溯源、独立验证、时间一致性、幂等、环境上线基线与冲突补偿。

## 长期保留与否决方向

保留：事件先压缩再模型、外置状态与三层记忆、证据约束、规则兜底、受控授权执行、持续验证。

后移/否决：通用安全知识库作为核心、Anthropic-Cybersecurity-Skills运行时依赖、默认多Agent、V1完整数字孪生/图数据库、模型直持高权限凭据、精确预测攻击者下一步、未授权公网自主攻击。

## 2026-09-12 — ai.5 Engineering Freeze

- 将 `TargetRef` 替换为跨平台 `ResourceRef`，Scope 从 IP/Port 专用结构提升为资源级授权 + 可选网络约束。
- `NormalizedEvent` 增加 CloudEvents-like envelope 与安全活动语义（activity/outcome/actor/source/target/observable），保留 OCSF mapping 路径而不强依赖完整 OCSF。
- `EventGroup` 与 `CorrelationDecision` 成为一等契约，事件压缩必须可解释、可版本化。
- Incident / Task / ActionAttempt 增加可测生命周期时间与租约/worker 字段；新增 `WorkerLease`。
- `ValidationScenario` 不再保存自然语言验证规则；新增可执行 `VerificationSpec` / `VerificationCheckSpec` / `AssertionSpec`。
- 新增 `AuthorizationContext`，AuthorizationDecision 必须可追溯当时的环境、Scope、风险、业务影响和传感器状态输入。
- 新增 `ModelRun`，模型/provider/prompt/context/token/latency/schema-validity 进入正式审计与评测对象。
- Capability 静态定义与动态 `CapabilityHealth` 分离，并补充权限、Secret 引用、并发、锁、取消/dry-run/验证与补偿信息。
- 新增最小 `AuditEntry` 与 `OutboxMessage` 合约，为 M1/M2 的 durable intent、审计和事务 outbox 提供基线。
- ai.5 状态定义为 `FROZEN_FOR_IMPLEMENTATION`；之后核心契约变更必须由实现、测试、安全或实测瓶颈驱动。
