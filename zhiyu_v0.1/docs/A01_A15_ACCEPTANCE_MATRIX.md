# A01–A15 Final Acceptance Matrix

RC7 / CONTROLLED LAB。PASS 15 / FAIL 0 / NOT_RUN 0。原文逐项取自冻结 AI_CONTEXT_ai.5.md，标准未改写。

| ID | 原始 requirement | 结果 |
|---|---|---|
| A01 | 两个真实来源入统一 Schema，重复血缘可识别 | PASS |
| A02 | 关联保留异常与矛盾，地址更换不误关联旧资产 | PASS |
| A03 | 非法 JSON、伪造 Evidence ID、未知能力和循环依赖被拒绝 | PASS |
| A04 | Scope 外、过期授权、变更摘要、高影响自动请求被拒绝 | PASS |
| A05 | 实际变更后回执丢失进入 UNKNOWN 并核对 | PASS |
| A06 | 旧 Worker/重复消息不重复修改；补偿不覆盖他人变更 | PASS |
| A07 | 攻击受限、正常业务可用、观测有效才 PASS | PASS |
| A08 | 业务中断是 FAIL；观测缺失是 INCONCLUSIVE | PASS |
| A09 | 临时遏制不会自动变成修复/关闭；TTL 到期复核 | PASS |
| A10 | 模型离线/数据库异常不令底层防御失效，不新增无审计变更 | PASS |
| A11 | 高负载下保留关键处理与恢复容量，损失显式可见 | PASS |
| A12 | 可信测试运行可关联，伪造测试标签不能免检 | PASS |
| A13 | 重规划无新证据/达预算后停止并转人工 | PASS |
| A14 | 全链路可重建，敏感数据没有进入云模型/工作流历史/日志 | PASS |
| A15 | 环境清理后恢复基线，闭环能重复运行 | PASS |

## A01 — PASS

- **original_requirement**：两个真实来源入统一 Schema，重复血缘可识别
- **original_expected_evidence**：原始样本、解析版本、source/origin/provenance
- **prerequisite**：两套真实采集器、原始日志、运行中的映射链。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：采集→原始行哈希→统一事件→分组→Incident；随后重放相同样本。
- **observed_result**：双来源 OBSERVED 事件与 lineage 保留，重放不创建重复逻辑事件。
- **limitation**：仅受控 Linux Lab；非真实客户流量。
- **evidence**：[sensors/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/result.json)；[sensors/sensor-faults/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/sensor-faults/result.json)
- **发布阻断**：否；没有使用 scope 外豁免。

## A02 — PASS

- **original_requirement**：关联保留异常与矛盾，地址更换不误关联旧资产
- **original_expected_evidence**：输入/输出、时间与实体绑定
- **prerequisite**：版本化资产绑定、原始事件、真实 PostgreSQL。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：绑定 v1→v2；旧地址与新地址分别入库；完整 suite 检查关联排除、矛盾与时间窗口。
- **observed_result**：旧地址新事件不再绑定 target-a，新地址事件绑定正确；历史事件不被改写，Audit 有效。
- **limitation**：证明当前端点重绑定；未证明任意历史 DHCP/IP 复用还原。
- **evidence**：[a02-binding-result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/a02-binding-result.json)；[final-test-results.xml](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-test-results.xml)
- **发布阻断**：否；没有使用 scope 外豁免。

## A03 — PASS

- **original_requirement**：非法 JSON、伪造 Evidence ID、未知能力和循环依赖被拒绝
- **original_expected_evidence**：计划拒绝记录，无外部副作用
- **prerequisite**：计划校验、证据/能力目录、无副作用拒绝路径。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：非法结构/伪造引用/未知能力/循环图定向拒绝；检查无 Action 副作用。
- **observed_result**：无效 JSON、Evidence、Resource、Capability 和循环/缺失依赖被拒绝。
- **limitation**：SCRIPTED_NOT_AI 用于安全边界；不计入真实模型语义准确率。
- **evidence**：[boundary-index.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/boundary-index.json)；[final-test-results.xml](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-test-results.xml)
- **发布阻断**：否；没有使用 scope 外豁免。

## A04 — PASS

- **original_requirement**：Scope 外、过期授权、变更摘要、高影响自动请求被拒绝
- **original_expected_evidence**：决策与审计
- **prerequisite**：Scope、授权快照、摘要校验及风险上限。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：越界、过期、摘要变化、高风险请求及组合风险检查。
- **observed_result**：拒绝已持久化且有审计；高风险自动执行为 0。
- **limitation**：生产环境授权规则只做受控反例，不是生产部署验收。
- **evidence**：[boundary-index.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/boundary-index.json)；[final-test-results.xml](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-test-results.xml)
- **发布阻断**：否；没有使用 scope 外豁免。

## A05 — PASS

- **original_requirement**：实际变更后回执丢失进入 UNKNOWN 并核对
- **original_expected_evidence**：设备记录、ActionAttempts、没有重复规则
- **prerequisite**：隔离 Lab HTTP 状态、持久 ActionAttempt、只读 reconciliation、owner/generation/digest。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：真实修改后执行器进程在回执提交前退出；过期租约进入 UNKNOWN；读目标回执及当前状态后生成终态；检查重复消息、旧 Worker ACK 和历史 Attempt。
- **observed_result**：目标 mutation 仅一次；未直接重放状态修改；同一 Action 只生成一个逻辑结果，UNKNOWN 历史与核对终态同时保留，Audit 有效。
- **limitation**：仅显式启用的隔离 Lab HTTP 状态；不是生产防火墙、任意命令、客户环境或生产 SLA 验收。
- **evidence**：[sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)；[final-test-results.xml](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-test-results.xml)
- **发布阻断**：否；没有使用 scope 外豁免。

## A06 — PASS

- **original_requirement**：旧 Worker/重复消息不重复修改；补偿不覆盖他人变更
- **original_expected_evidence**：租约代次、规则 ownership 和设备状态
- **prerequisite**：明确 owner、generation、before/current digest 的 Lab 补偿能力。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：A 建立状态，重复提交和旧 Worker 回执；合法撤销后 B 建立新状态，再提交 A 的补偿。
- **observed_result**：重复提交未增加 mutation；旧 Worker 被 fencing 拒绝；A 的补偿不能覆盖 B，B 的合法补偿可以执行。
- **limitation**：仅显式启用的隔离 Lab HTTP 状态；不是生产防火墙、任意命令、客户环境或生产 SLA 验收。
- **evidence**：[sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)；[final-test-results.xml](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-test-results.xml)
- **发布阻断**：否；没有使用 scope 外豁免。

## A07 — PASS

- **original_requirement**：攻击受限、正常业务可用、观测有效才 PASS
- **original_expected_evidence**：三类独立检查
- **prerequisite**：CONTAINMENT 专用 SECURITY/BUSINESS/OBSERVATION 三项独立验证及新鲜双传感器证据。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：实际 /attack 受限与 /health 可用；用独立验证身份采样；分别注入业务故障、攻击仍可达和 Wazuh Agent 离线。
- **observed_result**：三项均 PASS 才给 CONTAINMENT PASS；业务故障和攻击可达分别 FAIL；观测离线 INCONCLUSIVE。拒绝用 DETECTION 替代或用动作 Worker 自证。
- **limitation**：仅显式启用的隔离 Lab HTTP 状态；不是生产防火墙、任意命令、客户环境或生产 SLA 验收。
- **evidence**：[sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)；[final-test-results.xml](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-test-results.xml)
- **发布阻断**：否；没有使用 scope 外豁免。

## A08 — PASS

- **original_requirement**：业务中断是 FAIL；观测缺失是 INCONCLUSIVE
- **original_expected_evidence**：反例输入和判定
- **prerequisite**：独立业务检查与观测健康检查。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：业务端返回 500、停止采集器、真实等待 stale、恢复新流量再验证。
- **observed_result**：业务失败→FAIL；观测丢失/过期→INCONCLUSIVE；恢复并取得新证据后才 PASS。
- **limitation**：已验证只读 DETECTION 和新增 Lab CONTAINMENT 的三态边界；不包括任意生产业务。
- **evidence**：[sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)；[sensors/sensor-faults/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/sensor-faults/result.json)
- **发布阻断**：否；没有使用 scope 外豁免。

## A09 — PASS

- **original_requirement**：临时遏制不会自动变成修复/关闭；TTL 到期复核
- **original_expected_evidence**：Incident/Verification 时间线
- **prerequisite**：目标原生单调时钟 TTL，独立的活动期与到期复核任务。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：活动期取得 PASS；实际停止 PostgreSQL，等待目标 TTL 原生到期；恢复数据库，以新观测执行到期复核。
- **observed_result**：控制数据库停止期间状态仍自动恢复开放；到期复核 FAIL，前后 Evidence ID 不相交，Incident 不 CLOSED；过期证据不能给 PASS，离线只能 INCONCLUSIVE。
- **limitation**：仅显式启用的隔离 Lab HTTP 状态；不是生产防火墙、任意命令、客户环境或生产 SLA 验收。
- **evidence**：[sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)；[final-test-results.xml](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-test-results.xml)
- **发布阻断**：否；没有使用 scope 外豁免。

## A10 — PASS

- **original_requirement**：模型离线/数据库异常不令底层防御失效，不新增无审计变更
- **original_expected_evidence**：故障注入与恢复记录
- **prerequisite**：独立运行的 Lab 底层观测/业务服务；数据库和模型故障注入。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：停止模型后确定性只读闭环；DB 故障时拒绝无审计操作，恢复后核对持久化数据；sensor DB stop 时真实流量仍产生 Suricata/Wazuh 原始记录，数据库恢复后成功双源入库。
- **observed_result**：模型离线安全 fallback；数据库恢复持久化不丢；独立 Lab 服务可用，无新无审计修改。
- **limitation**：底层为本 Lab 的独立观测/业务服务；不证明生产防火墙/OT 控制器高可用。
- **evidence**：[result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/result.json)；[sensors/a10-database-outage/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/a10-database-outage/result.json)；[sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)
- **发布阻断**：否；没有使用 scope 外豁免。

## A11 — PASS

- **original_requirement**：高负载下保留关键处理与恢复容量，损失显式可见
- **original_expected_evidence**：配额、丢失统计、恢复任务完成情况
- **prerequisite**：BACKGROUND / SECURITY_CRITICAL / RECOVERY 预留配额，真实持久队列与有效租约。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：创建 1002 个背景任务并占满背景容量；再次背景领取被延迟；保持有效背景租约及至少 1000 条积压期间，入库新鲜真实 IDS 告警、关联 Incident、完成关键查询和遏制，再完成独立验证。
- **observed_result**：真实告警 accepted > 0、grouped processed > 0；关键任务完成且 Verification PASS；背景积压和 admitted/deferred/dropped/完成数显式记录，dropped = 0。
- **limitation**：仅显式启用的隔离 Lab HTTP 状态；不是生产防火墙、任意命令、客户环境或生产 SLA 验收。
- **evidence**：[sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)；[remediation-task-benchmark.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/remediation-task-benchmark.json)
- **发布阻断**：否；没有使用 scope 外豁免。

## A12 — PASS

- **original_requirement**：可信测试运行可关联，伪造测试标签不能免检
- **original_expected_evidence**：run registry、越界异常和正常检测
- **prerequisite**：可信 registry、Scope/来源/时间校验、普通原始事件检测。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：可信注册运行关联；伪造 run、来源越界、过期、data_origin 不符逐项拒绝；原始标签剥离测试。
- **observed_result**：合法运行接受 1 条，四类违规拒绝；Audit 有效，无外部 Action。
- **limitation**：registry 由测试管理员建立，不声称提供未实现的公开注册 API；不冒充真实 sensor 数据。
- **evidence**：[a12-registry-result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/a12-registry-result.json)；[final-test-results.xml](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-test-results.xml)
- **发布阻断**：否；没有使用 scope 外豁免。

## A13 — PASS

- **original_requirement**：重规划无新证据/达预算后停止并转人工
- **original_expected_evidence**：事件级预算与停止原因
- **prerequisite**：有限根事件预算、语义证据指纹、人工复核终态。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：重规划相同证据、预算耗尽、风险超额；检查停止原因和 Incident HUMAN_REVIEW。
- **observed_result**：无新证据或达预算停止发出新计划，转 HUMAN_REVIEW；重试幂等。
- **limitation**：不包括人工完成处理或外部通知系统验收。
- **evidence**：[boundary-index.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/boundary-index.json)；[final-test-results.xml](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-test-results.xml)
- **发布阻断**：否；没有使用 scope 外豁免。

## A14 — PASS

- **original_requirement**：全链路可重建，敏感数据没有进入云模型/工作流历史/日志
- **original_expected_evidence**：Context/版本/出域记录和数据检查
- **prerequisite**：不可变 Context/ModelRun/Audit/版本血缘及可检查日志。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：引用/版本/血缘复核、已知私密值扫描、canary 外泄拒绝、最终数据库 Audit 检查。
- **observed_result**：所有最终环境 Audit 有效；已知私密凭证无匹配；canary 仅在测试定义、精确脱敏规则和已保留的历史断言源码片段中，危险模型输出未持久化。
- **limitation**：数据源中的公开一次性 Lab 账户与真实 secret 分开；无云调用不等于已测试任意云策略。
- **evidence**：[final-database-snapshot.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-database-snapshot.json)；[image-source-correspondence.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/image-source-correspondence.json)；[boundary-index.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/boundary-index.json)；[Secret scan](m6-runtime/gate-e-secret-scan.json)
- **发布阻断**：否；没有使用 scope 外豁免。

## A15 — PASS

- **original_requirement**：环境清理后恢复基线，闭环能重复运行
- **original_expected_evidence**：场景版本、前后快照、资源清理
- **prerequisite**：可销毁并从相同版本重新创建的 Lab 拓扑与持久卷。
- **actual_environment**：RC7 / zhiyu-smoke-771744b23fbb，Docker Linux、真实 PostgreSQL；Lab 状态目标与 Suricata/Wazuh 证据。单元反例使用明确标记的 SYNTHETIC fixture。
- **actual_procedure**：两轮建库/迁移/bootstrap→SYNTHETIC Event/Incident→4 项只读 Action→独立 Verification；每轮清除所属容器/网络/卷。
- **observed_result**：两轮均 PASS，重建后基线计数与契约对象一致；所属资源清理后为空。
- **limitation**：两次同镜像 Lab 重建闭环，另有真实遏制补偿与原生 TTL 恢复；不声称恢复生产设备配置。
- **evidence**：[a15-reset/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/a15-reset/result.json)；[sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)
- **发布阻断**：否；没有使用 scope 外豁免。
