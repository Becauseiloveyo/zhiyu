# Executive Summary

项目主方向仍是“确定性控制链 + AI 受约束决策 + 独立持续验证”，未发现已实施的大型基础设施扩张或 ai.5 架构漂移。现有 80 例 G2 SHADOW 规划层实验符合 [负责人 v0.6 开发与验证指令 §22–24](<C:/Users/wc/.codex/attachments/14cab7db-0d3f-471a-abab-f815d8347a0b/pasted-text.txt>) 明确限定的范围；它不是未经批准的缩水。完整闭环收益仍无证据，原 M4 的 G0、SBOM 及最终产品交付也不能被当前工程 PASS 自动覆盖。

**PLAN_CONFORMANCE: MINOR_DEVIATION；ENGINEERING_ALIGNMENT: ALIGNED；DOCUMENT_ALIGNMENT: STALE。** 已确认的偏差主要为 LEVEL 1 文档滞后与 LEVEL 2 有依据的里程碑/实验顺序变化；SBOM 和更广价值实验缺少后续出口，属于需明确归属的交付风险，尚无证据把它们判为逾期违约。v0.2–v0.5 核心目标 MATCHED；v0.6 对原较宽目标 PARTIALLY_MATCHED、对负责人限定的本阶段目标 MATCHED；v0.9 仅 PLANNED。A01–A15 从 v1.0 前移到 v0.6 是合理的 MOVED_EARLIER，不是错误。

本次只新增三份审计文件，未改源码、tests、migration、五份 v0.9 规划、计划书原件或历史证据；未运行新测试/新 Lab。381/182/15 是读取并核对既有证据的结果。

# Source Baseline

原目标取 [正式计划书 PDF](<C:/Users/wc/Downloads/智御-网络安全自主决策与持续验证平台-参赛项目计划书.pdf>) §10.1（第 17–18 页）及配套 DOCX，原文/哈希/边界详见 [Baseline Audit](PROJECT_PLAN_BASELINE_AUDIT.md)。冻结工程语义取 [ai.5 冻结上下文](AI_CONTEXT_ai.5.md)；实际验收取 [v0.6 Final Report](VALIDATION_REPORT_v0.6.0.md)、[A01–A15 Matrix](A01_A15_ACCEPTANCE_MATRIX.md)、[Final Evidence Index](FINAL_EVIDENCE_INDEX_v0.6.0.md)；五份 v0.9 文件只作当前规划依据。

当前 RC7：310 个 controlled files、28 个 frozen files 本次逐文件哈希匹配；source `f60a06b0db456ac2c7e282c5522241165747ab65592d64f5d06bd871e5c1aa05`；head `0016_lab_remediation`；72 张表含 Alembic。正式 v0.6 ZIP 哈希匹配 `3afd802e3bee0945591d3b7f1e02303bafda33a63679e4fe543a4a72609003a5`。源码 110 个 Python 文件、7 个路由文件、47 个显式操作；未发现前端工程或 v0.9 migration。

现有 381 项来自 [final-test-results.xml](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-test-results.xml) 的 380 与 [宿主 JUnit](m6-runtime/rc/RC7-host-final-tests.xml) 的 1，均无失败/跳过；[result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/result.json) 含 182 runtime checks。[80 例配对原始记录](m6-runtime/gate-c-selected-results.json) 本次直接复核 80 个配对 Context 与 SHADOW 标记。不是用 README、版本号或报告标题代替核验。

证据冲突单列：最终 `result.json` 顶层仍留 `real_sensor_runtime=NOT_RUN`、`platform_acceptance_A01_A15=NOT_RUN`，与独立 Sensor 子结果及 Gate E 总判定不一致。综合实际子结果、15 项矩阵、RC/source 身份，确认这些是遗留摘要字段，不能忽略，也不能据此抹去真实已运行证据。列为 F04 / LEVEL 1，建议以后通过说明/新索引消歧，不篡改封存原始 JSON。

# Original Roadmap

§10.1 顺序：v0.2 确定性事件智能 → v0.3 确定性响应控制 → v0.4 持续验证/重规划 → v0.5 AI Decision Layer → v0.6 Reliability & AI Value → v0.9 Competition-ready Demo → v1.0 Stable Prototype。

原计划明确把真实 Sensor、G1/G2、故障、负载与安全加固放在 v0.6，把 Dashboard/Timeline/Attack-State Graph/Report/完整演示脚本放在 v0.9，把 A01–A15 全面验收、文档、安装/升级、安全基线放在 v1.0。细化的边界/排除/依赖见 [Baseline Audit §2](PROJECT_PLAN_BASELINE_AUDIT.md#2-原始版本路线原文目标不以实际倒推)。原文当时的 v0.5 开发中是历史事实，不反向删改。

# Current Actual Roadmap

v0.2–v0.5 已形成递进的事件、控制、验证、AI 层。v0.6 RC7 完成真实双源、受控状态操作、故障与恢复、15/15 验收；大量性能/模型评估属于明确标记的合成输入或历史源码。实际 AI 默认 OFF，启用默认 SHADOW，未建立生产或通用 AI 语义收益证明。

v0.9 只有五份规划，UI 等待负责人设计；不存在完整产品 Dashboard、跨对象 Timeline、图投影、报告导出和比赛编排。v1.0 尚未形成最终安装/升级、操作文档、发布冻结和最终产品验收，前移 A01–A15 并未令其空心化。

# Version-by-Version Comparison

| Version | Planned Objective | Planned Deliverables | Actual Implementation | Evidence | Status | Deviation |
|---|---|---|---|---|---|---|
| v0.2 | Deterministic Event Intelligence | 双 Adapter、Group、Correlation、Incident | 0002–0004；确定性聚合/血缘/Incident | [VALIDATION_v0.2.0.md](VALIDATION_v0.2.0.md) | MATCHED | LEVEL 0；Sensor 实际采集按原计划留到 v0.6 |
| v0.3 | Deterministic Response Control | Plan、Task Graph、Capability、Authorization/Risk、Lease/Gateway | 0005–0007；受控只读执行链 | [VALIDATION_REPORT_v0.3.0.md](VALIDATION_REPORT_v0.3.0.md) | MATCHED | LEVEL 0；未把计划/回执当安全成功 |
| v0.4 | Continuous Verification & Re-plan | 三维验证、State Update、bounded Re-plan | 0008–0010；独立判定/生命周期/有限重规划 | [VALIDATION_REPORT_v0.4.0.md](VALIDATION_REPORT_v0.4.0.md) | MATCHED | LEVEL 0；真实状态副作用场景在 v0.6 补齐 |
| v0.5 | AI Decision Layer | Context、Gateway、真实模型、分析/提案/回退 | 0011–0015；AI 使用既有控制链 | [VALIDATION_REPORT_v0.5.0.md](VALIDATION_REPORT_v0.5.0.md) | MATCHED | LEVEL 1 状态文档滞后；不表示通用语义正确率已证明 |
| v0.6 | Reliability & AI Value | 真实 Sensor、G1/G2、故障、负载、安全 | 可靠性通过；80 例规划层配对；G2 未执行；0016 最小 Lab 支持 | [v0.6 Final Report](VALIDATION_REPORT_v0.6.0.md); [80 例配对原始记录](m6-runtime/gate-c-selected-results.json) | PARTIALLY_MATCHED | LEVEL 2：负责人已限定 SHADOW，长期闭环收益仍未验证；按该阶段范围 MATCHED |
| v0.9 | Competition-ready Demo | Dashboard/Timeline/Graph/Report/Demo | 仅五份 Inspect + Plan，底层事实可复用 | [V0.9_REQUIREMENTS_TRACEABILITY.md](V0.9_REQUIREMENTS_TRACEABILITY.md) | PARTIALLY_MATCHED | 阶段未完成，不是已交付；UI 等待设计，未发现实施越界 |
| v1.0 | Stable Prototype | A01–A15、文档、安装/升级、安全基线 | A01–A15 前移；最终产品/发行交付未完成 | [A01–A15 Matrix](A01_A15_ACCEPTANCE_MATRIX.md); [final-migration.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-migration.json) | PARTIALLY_MATCHED | 验收子项 MOVED_EARLIER；未来安装/升级/文档仍有意义 |


## Version Boundary Findings

| 检查 | 发现及证据 | 等级 |
|---|---|---|
| v0.2 是否做了 v0.5 核心 | 0002–0004 为事件/关联/Incident；AI 运行迁移在 0011–0015，历史 v0.2 报告限定确定性 | LEVEL 0 |
| v0.5 是否重做 v0.3 | AI Proposal/Context 为输入与可审计记录，复用 Authorization/Task/Gateway；未发现第二执行链 | LEVEL 0 |
| v0.6 是否为测试造第二产品 | Lab target 是有限测试目标/执行适配器，实际任务仍经原控制链；capacity 复用 TaskRuntime/租约；未见第二编排器 | LEVEL 0，新增内部实现属必要细化 |
| v0.9 Plan 是否提前写 UI | 无前端目录、组件/构建包或实现迁移；五文件明确 PLANNED/BLOCKED | LEVEL 0 |
| v1.0 是否空心化 | 只有 A01–A15 前移；完整产品、安装/升级、文档、安全发布仍未完成 | LEVEL 2 的合理顺序变化 + LEVEL 1 路线待更新 |
| v0.6 AI Value 是否与工程 PASS 同步 | [负责人 v0.6 开发与验证指令 §22–24](<C:/Users/wc/.codex/attachments/14cab7db-0d3f-471a-abab-f815d8347a0b/pasted-text.txt>) 批准 SHADOW；配对实测符合阶段范围，长期闭环收益的后续出口未明确 | LEVEL 2 / 文档需明确 |

# Requirement Traceability

完整原子交付项及 A01–A15 追溯见 [Requirement Traceability Matrix](PROJECT_PLAN_TRACEABILITY_MATRIX.md)。Plan Source → Implementation → Test → Evidence 分开，明确 NO_EVIDENCE。未将“定义了表/Contract”算成产品功能，也未将编排脚本或生成报告误当成 Dashboard/Report 产品接口。

# Milestone Movement

**A01–A15：MOVED_EARLIER（v1.0 → v0.6）。** 原计划 PDF p18 明确归 v1.0；[负责人 Remediation Cycle 指令](<C:/Users/wc/.codex/attachments/c7d34273-564d-44d1-a066-a0f6c821898b/已粘贴的文本.txt>) 随后明确要求修复 A05/A06/A07/A09/A11 的实际软件前置条件，不改标准、不扩 ai.5。[A01–A15 Matrix](A01_A15_ACCEPTANCE_MATRIX.md) 逐项保留原 requirement；冻结 28 文件哈希相同。[sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json) 提供真实变更、UNKNOWN 核对、ownership/补偿、TTL、双 Sensor 三维验证与恢复容量证据；[a15-reset/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/a15-reset/result.json) 提供两次重置。

未发现降低冻结标准的证据，15 项均有受控 Lab 证据，不等于生产泛化；A02/A14 等局限已保留。结论是合理前移，需要更新 roadmap，不应回滚实现。A01–A15 也必须在最终 v1.0 候选上做影响评估/相应回归，旧版本 PASS 不能自动覆盖未来改动。

明确变更与长期证据缺口分开：[负责人 v0.6 开发与验证指令 §22–24](<C:/Users/wc/.codex/attachments/14cab7db-0d3f-471a-abab-f815d8347a0b/pasted-text.txt>) 已批准当前 G2 为 SHADOW，故本阶段较宽闭环实验目标被具体阶段范围 SUPERSEDED，而非未经批准的 OMITTED。没有查到将长期完整比较分配到特定后续版本的记录，不虚构 MOVED_LATER 的目标版本。v0.9 UI 是已声明设计等待，原计划没有固定截止日，不能凭未开发宣布延期。若负责人决定把完整比较放入 v1.0，届时才记正式 MOVED_LATER。

# Scope Creep Findings

以下“未发现”限定已审源码、migrations、依赖锁、Compose 与工具；分类说明该方向在基线中的地位，不代表已实现。

| 项目 | Classification | 实际发现 / 必要性 |
|---|---|---|
| 大型基础设施、新微服务平台 | PLANNED（当前约束为不引入） | 仍 FastAPI/SQLAlchemy/PostgreSQL 模块化单体；[依赖](../pyproject.toml)、[Compose](../docker-compose.yml) |
| 第二工作流、事件模型 | PLANNED（单链） | Task/Lease/Outbox 共享；没有第二事件源或运行引擎 |
| Multi-Agent / unrelated AI framework | EXPERIMENTAL（若未来探索） | 当前未发现 Agent 团队运行框架依赖或产品执行路径；模型 provider 接口不等于 Multi-Agent |
| Kafka / Temporal | EXPERIMENTAL（后续增强未承诺选型） | §10.2 仅未来 Event Bus/Durable Workflow；当前依赖/服务中未引入 |
| Neo4j 重构 | EXPERIMENTAL（未实施） | 图规划是 PostgreSQL 事实投影，未引入图数据库 |
| unrestricted pentest / arbitrary shell / arbitrary firewall | UNJUSTIFIED_SCOPE_CREEP（若出现） | 本次未发现产品能力；固定 Lab primitive 明确禁止这些能力；宿主验收命令不等于开放模型命令执行 |
| 重复 Dashboard backend | PLANNED（产品读层尚待做） | 当前只有指标/局部查询；v0.9 计划复用并投影，无重复实施 |
| 第二 State / Audit / Verification | PLANNED（复用基线） | AI snapshot/context 为有界不可变上下文；模型 State 为 INFERENCE；Audit/Verification 仍单一；未发现第二真值系统 |
| Lab state-changing remediation | JUSTIFIED_CHANGE | RC3 五项阻断 + 负责人明确修复指令；只为冻结 A05/6/7/9 |
| reserved recovery capacity / 0016 | JUSTIFIED_CHANGE | A11 无有效预留容量；旧 CHECK 仅允许 NONE，不能诚实记录实际 Lab 副作用；新迁移只增加 LAB_PATH |
| G2 SHADOW 实验范围 | JUSTIFIED_CHANGE | 负责人 §22 明确要求 AI-assisted / SHADOW；80 例同 Context 配对与此相符，不是报告自行削减要求 |
| 更多对抗样本/安全故障工具 | PLANNED | v0.6 故障/AI 评估目标内细化；真实模型与脚本分别标记 |

未发现已实施的 UNJUSTIFIED_SCOPE_CREEP。对“未引入”的候选列分类是说明其计划边界，不能统计为已发生的范围变更。

# Architecture Drift Findings

PASS 表示本次所审路径与记录支持遵守不变量，不是穷尽所有输入的形式化保证。所有证据属于工程/受控 Lab；没有 PRODUCTION_VALIDATED。

| Invariant | Result | Code | Test | Runtime / explanation |
|---|---|---|---|---|
| Raw alerts 不直接喂 LLM | PASS | [ai/context.py](../src/zhiyu/ai/context.py) | [test_ai_context.py](../tests/test_ai_context.py) | [ai-evaluation.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/ai-evaluation.json)；先聚合/结构化投影、来源摘要/预算；不否认选取的日志片段可作为不可信数据进入受限 Context |
| FACT / OBSERVATION / INFERENCE 分离 | PASS | [ai/analysis.py](../src/zhiyu/ai/analysis.py) | [test_ai_analysis.py](../tests/test_ai_analysis.py) | [boundary-index.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/boundary-index.json)；模型 State 固定为 INFERENCE/MODEL_INFERENCE；引用合法不等于事实 |
| AI Proposal != Authorization | PASS | [ai/plan_validation.py](../src/zhiyu/ai/plan_validation.py) | [test_ai_planner.py](../tests/test_ai_planner.py) | [boundary-index.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/boundary-index.json)；提案校验不授予权限，状态能力拒绝，需原授权链 |
| LLM 无直接 root / shell / firewall privilege | PASS | [response/executors.py](../src/zhiyu/response/executors.py) | [test_m6_lab_boundaries.py](../tests/test_m6_lab_boundaries.py) | [boundary-index.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/boundary-index.json)；有限 Executor 注册与参数；模型文本不能成为命令；验收宿主工具不等于 LLM 权限 |
| Action 必经 Authorization / Risk / Gateway | PASS | [response/gateway.py](../src/zhiyu/response/gateway.py) | [test_response_authorization.py](../tests/test_response_authorization.py) | [sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)；受控能力、当前 Scope/摘要/租约复核；Lab 仍走同一入口 |
| execution success != security success | PASS | [response/gateway.py](../src/zhiyu/response/gateway.py) | [test_verification_engine.py](../tests/test_verification_engine.py) | [boundary-index.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/boundary-index.json)；回执仅执行结果；模型说成功但验证可 FAIL |
| Verification 独立 | PASS | [verification/engine.py](../src/zhiyu/verification/engine.py) | [test_verification_runtime.py](../tests/test_verification_runtime.py) | [sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)；独立安全/业务/观测检查，不采纳模型成功声明 |
| Sensor insufficient => INCONCLUSIVE | PASS | [verification/engine.py](../src/zhiyu/verification/engine.py) | [test_real_sensor_health.py](../tests/test_real_sensor_health.py) | [sensors/sensor-faults/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/sensor-faults/result.json)；缺失、过期、失效观测保守判定 |
| Model failure 保留 deterministic baseline | PASS | [ai/brain.py](../src/zhiyu/ai/brain.py) | [test_ai_api_brain.py](../tests/test_ai_api_brain.py) | [ai-evaluation.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/ai-evaluation.json)；故障回退与原确定性任务链分离；另见 v0.5 Gate E/模型离线运行 |
| high-risk auto execution = 0 | PASS | [response/policy.py](../src/zhiyu/response/policy.py) | [test_response_boundary.py](../tests/test_response_boundary.py) | [final-database-snapshot.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-database-snapshot.json)；最终数据库与真实 Lab 都为 0；不外推未来所有环境 |
| active validation 仅授权 Lab | PASS | [response/lab_protocol.py](../src/zhiyu/response/lab_protocol.py) | [test_m6_lab_boundaries.py](../tests/test_m6_lab_boundaries.py) | [sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)；显式安装、固定目标、R2 受限状态原语；无通用 shell/firewall |
| PostgreSQL canonical source 保持 | PASS | [db/session.py](../src/zhiyu/db/session.py) | [test_schema_and_baseline.py](../tests/test_schema_and_baseline.py) | [final-migration.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-migration.json)；强制 postgresql+psycopg；71 ORM 表+Alembic，图/API 规划只是投影 |


未发现 LEVEL 4 架构漂移。冻结哈希相同只证明契约字节未改，本结论还检查了授权/执行/验证/状态的实际路径。状态变更后 UNKNOWN 的核对走既有 ActionAttempt 与只读查询，不以重放副作用猜测结果。AI 的有限状态/上下文持久化没有将 PostgreSQL 替换为模型记忆。

# Missing Planned Deliverables

| Finding | 原要求与现状 | 成熟度 / severity |
|---|---|---|
| F01 长期完整 G1/G2 闭环收益尚未验证 | ai.5 G2=AI 闭环；计划 §8.2–8.3/§10.1 要求 AI Value。[负责人 v0.6 开发与验证指令 §22–24](<C:/Users/wc/.codex/attachments/14cab7db-0d3f-471a-abab-f815d8347a0b/pasted-text.txt>) 随后明确本阶段 SHADOW。80 例真实比较已做，但 G2 80/80 executor_calls=0、NOT_RUN_SHADOW，不能主张闭环收益 | 已完成子集 CONTROLLED_LAB；长期子集 DOCUMENTED_ONLY。当前范围变更 JUSTIFIED_CHANGE / LEVEL 2；不判阶段遗漏 |
| F02 G0 与完整价值指标 | ai.5 M4 的同场景 G0 基线 NO_EVIDENCE；自然语言真值/unsupported claim 总量尚未建立，人工抽样不是独立标注；成本有 tokens 而实际费用可能未知 | NO_EVIDENCE 或局部证据；原 M4 未覆盖项，v0.6 新指令只要求 G1/G2；后续出口 UNKNOWN，不判已逾期 |
| F03 SBOM 交付 | 计划 p10/p19 写固定第三方版本/SBOM；有 uv/requirements 锁、镜像及 manifest，无独立可识别 SBOM 成品/生成验收证据 | 固定依赖 IMPLEMENTED_AND_TESTED；SBOM DOCUMENTED_ONLY；真实交付缺口，具体版本出口未明确，应纳入 v1.0；若声称当前完整安全交付已完成则构成 LEVEL 3 |
| v0.9 五类产品交付 + UI | 有事实、局部查询及设计；产品 API/读模型/图/导出/演示编排/页面未形成 | DOCUMENTED_ONLY（最终功能）；尚未实施，不当成过期版本的遗漏 |
| v1.0 最终安装/升级/文档/安全发布 | 有 Compose、迁移往返及报告；无最终完整产品的干净安装、带数据升级恢复、操作手册和发布验收 | 部分 IMPLEMENTED_AND_TESTED；最终交付 DOCUMENTED_ONLY，正常未来工作 |

### 关键能力成熟度汇总

| 能力 | 当前可支持的成熟度 | 不能据此宣称 |
|---|---|---|
| Real Sensor | CONTROLLED_LAB | 真实客户检出率、Windows/OT Sensor 完成 |
| AI Decision Brain | IMPLEMENTED_AND_TESTED + CONTROLLED_LAB 真实本地模型 | 自然语言普遍正确、实际 AI 修复增益 |
| Controlled Action | CONTROLLED_LAB，固定 Lab 目标、R2 有界状态 | 通用 firewall/生产自动处置 |
| Verification / Re-plan | IMPLEMENTED_AND_TESTED，Lab 正反例 | 所有网络的安全结果保证 |
| G1/G2 | CONTROLLED_LAB 的规划层配对；闭环收益 DOCUMENTED_ONLY | 80 例 AI 自动处置对照实验已完成 |
| Load | SYNTHETIC_RUNTIME；部分真实告警饱和 Lab | 生产吞吐/SLA |
| Soak | SYNTHETIC_RUNTIME，历史源码 30 分钟 | RC7 多日稳定/客户可用性 |
| Demo | CONTROLLED_LAB 组件；完整比赛脚本 DOCUMENTED_ONLY | Competition-ready 已完成 |
| Dashboard / Timeline / Graph / Report / UI | 产品层 DOCUMENTED_ONLY；局部查询已 IMPLEMENTED_AND_TESTED | 有数据表/验收 Markdown 即有可用产品页面 |

G1/G2 并非“完全没做”，SHADOW 还有明确负责人指令。不能将它判为无授权偏离，也不能据此宣布完整闭环收益已验证。当前结论认可本阶段实验完成；后续实验如何承接 ai.5 较宽目标，应由负责人明确，不需要为审计结论开启危险执行或修改历史证据。

# Unplanned Implemented Features

原计划未逐项写出所有机制，但 ai.5 的 A05/A06/A09/A11 已要求相应行为，不能把实现细节自动算成新需求。

| 已实现细节 | 类别 | 具体依据与实现 | 计划书更新建议 |
|---|---|---|---|
| Lab 状态原语与只读 reconcile | A 为满足冻结 Acceptance 的必要实现 | RC3 A05/6/7/9 缺前置条件；[负责人 Remediation Cycle 指令](<C:/Users/wc/.codex/attachments/c7d34273-564d-44d1-a066-a0f6c821898b/已粘贴的文本.txt>)；[response/lab_client.py](../src/zhiyu/response/lab_client.py)、[response/lab_reconcile.py](../src/zhiyu/response/lab_reconcile.py) | 说明是固定隔离 Lab，不写成通用安全设备管理 |
| ownership / generation / before/current digest、补偿 CAS | A + B 工程加固 | A06 要求不覆盖他人变更；[response/lab_target.py](../src/zhiyu/response/lab_target.py) 与真实外 owner 反例 | 在安全边界/可逆性列实际实现 |
| native TTL、数据库断开仍到期、证据复核 | A | A09/A10；[sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)、[sensors/a10-database-outage/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/a10-database-outage/result.json) | 区分到期、遏制失效、修复/关闭 |
| reserved recovery capacity | A + B | A11；[response/capacity.py](../src/zhiyu/response/capacity.py) 复用共享租约，显式 opt-in；A11 队列 1001、真实 IDS 及恢复观测 | 更新负载边界，不外推 SLA |
| migration 0016 | A | [0016](../migrations/versions/0016_lab_remediation.py) 只拓展 ActionResult CHECK 为 NONE/LAB_PATH；新 receipt 存在时降级 fail closed | 写升级限制，不把拒绝破坏性降级当迁移缺陷 |
| 模型缓存限额、有限日志/回执与 canary 边界 | B | [G1/G2 方法与限制](ADVERSARIAL_EVALUATION_v0.6.0.md) 记录 OOM 后 prompt cache 8192→256 MiB；原失败保留，语义算法未因此变好 | 更新实际运行条件与已知局限 |
| A01–A15 整体验收提前 | C 后续里程碑前移 | 原 v1.0 与当前真实验收矩阵 | 更新 roadmap，保留最终版本再验收责任 |

未发现 D 类不必要扩展。上述机制没有新增通用工作流框架、第二事件模型或非目标 AI 平台。

# V0.9 Alignment

**V0.9_PLAN_ALIGNMENT: ALIGNED_WITH_MINOR_ADJUSTMENTS。** 五份规划覆盖原 §10.1 的全部五类交付，后端事实读取/API、timeline、graph、report、demo 分工合理；UI-independent 与 UI-blocked 分界清楚。没有源码实施，也没有自行修改 ai.5。

| 原交付 | 当前规划覆盖 | 边界 / 尚需调整 |
|---|---|---|
| Dashboard | M9.3/M9.6 overview、Incident/AI/Verification/health 只读 DTO | M9.9 页面等待设计；真实测量与注册配置分开 |
| Timeline | M9.4 异构事实与时间语义、分页、lineage | 原有局部 timeline 不是完整产品时间线 |
| Attack / State Graph | M9.5 证据关系投影 | StateRelation 有表无产品写入者；假设边不画成攻击事实，不需 Neo4j |
| Report | M9.7 JSON/Markdown、manifest、引用闭包/一致性快照 | 当前静态验收报告不是产品导出；PDF 样式/页面未确定 |
| Demo | M9.8 setup/trigger/status/reset、LIVE/REPLAY 分离 | 回放无副作用；现有 Lab 工具不能直接冒充一键产品演示 |

小调整一：[V0.9_REQUIREMENTS_TRACEABILITY.md](V0.9_REQUIREMENTS_TRACEABILITY.md) §1 的版本来源只追溯到负责人本轮指令和未写 v0.9 的 ai.5 路线。现在已找到正式计划 p18 明文，需补充该来源；其“冻结路线文档无 v0.9”本身不等于错误，但当前溯源不完整。

小调整二：拟议 `demo_runs/demo_run_steps` 只用于恢复/幂等/清理状态，仍需未来 ADR/最小迁移评审，不能扩成第二事实库。短事务一致性快照、TTL 有界导出、Scope 读权限是防泄露和可复现需要，不是大型基础设施；保持同步有界导出，只有实际阻塞证据才引入异步任务持久化。

小调整三：演示说辞应直接引用本审计的 AI Value 限制，不因 v0.6 PASS 宣称 G2 已实证优于固定编排。总体规划可沿用；本轮未更改五份原文件。

# V1.0 Remaining Scope

建议保留原版本号，将 Stable Prototype 的出口具体化为 Final Product Acceptance / Install & Upgrade / Documentation / Release Freeze / Competition Release；这是建议，不是已批准新基线，不新增版本。

1. 先完成 v0.9 的产品读模型/API/权限、完整时间线、证据图、报告、可恢复可清理的演示编排；收到设计后做 UI 与端到端验收。
2. 对原 G1/G2 闭环价值要求作正式处置：补充受控、同边界/预算、成对执行与独立验证的实验（含失败/成本/恢复），或明确批准缩小为规划层辅助价值并修订主张。G0 是否纳入及重复/标注方案一并明确。不能以提高 autonomy 或关闭安全检查换取好看结果。
3. 在最终产品候选上复验 A01–A15 与所有受影响功能；现有 v0.6 15/15 作为基础，不重复造执行/验证引擎。
4. 干净安装、配置/权限/秘密引导、带历史数据升级、备份恢复、失败升级处置；明确 0016 有 LAB_PATH 证据时不能破坏性降级。迁移往返成功不代替完整产品升级验收。
5. 形成操作/部署/演示/故障恢复/限制文档、安全基线和 SBOM；锁定源、依赖、镜像、模型、Prompt/策略、场景和证据 manifest，完成最终打包可复现检查。
6. Competition Release 给出真实与回放区分、已验证范围、测量样本和未完成项；不包装成 Production/企业 HA/多租户交付。

# Plan Document Staleness

**PLAN_DOCUMENT_STALENESS: STALE。** 方向和五类交付仍有效，过期的是工程状态/里程碑定位；不将历史数字全部替换为最新数字。

| 位置 | 原描述 | 已确认当前事实 / 应更新事项 |
|---|---|---|
| 摘要、§3、§5.3、§7、结尾；§10.1 p17 | v0.5 开发中、A/B PASS、C 进行中 | v0.5 最终 PASS，保留引用完整性/语义质量局限 |
| §7 的当前状态和指标表 | Real Sensor / A01–A15 NOT_RUN | RC7 Real Sensor CONTROLLED LAB、A01–A15 15/15；冻结 ai.5 原件的历史 NOT_RUN 不应直接改写 |
| §10.1 v0.6 | Reliability & AI Value 未来项 | 可靠性工程 PASS，价值实验规划层已做、闭环缺口单列；不能整行粗改为完全兑现 |
| §10.1 v0.9 | 未来 Competition-ready Demo | 已 Inspect + Plan，PLANNED；Implement/UI 未开始 |
| §10.1 v1.0 p18 | 首次全面 A01–A15 验收 | v0.6 已前移；v1.0 保留最终候选回归及安装/升级/文档/发布 |
| §7/结尾的“当前”245/135 等数字 | 当前工程仍按 v0.4 | 如表述当前需补 381/182/15 及各分母；v0.2 147/50、v0.3 201/81、v0.4 245/135 作为历史数据仍有效 |
| §8.2–8.3 / AI 指标 | 正式 AI 价值评估留待完整 Gate 后报告 | 已有 80 例规划层配对、147 ModelRuns；G2 闭环验证/真值指标未齐，不写成未做任何比较或已证实增益 |
| v0.9 追溯 §1 | 五类交付来源主要为负责人指令 | 补充正式计划 p18 来源链接/哈希，保留 ai.5 不同命名的解释 |
| 当前 runtime 摘要字段 | 最终 result.json 顶层两项 NOT_RUN | 子结果与最终 Gate E 已 PASS；后续说明/索引明确字段适用层次，保留原始证据不静默改写 |

计划书日期较旧不意味着当时造假；当前使用它介绍进展时需要更新。核心目标、确定性优先和生产未验证等描述仍有效。未找到客户/商业数据新证据，不能建议替换为虚构订单或效果。

# Risks

| 风险 / finding | 等级 | 影响 |
|---|---|---|
| F01/F02：未来把工程 Gate PASS 当 AI 闭环收益 PASS | 当前 LEVEL 2 范围/顺序变化；夸大宣称会形成 LEVEL 3 | 当前报告已标 SHADOW 和语义限制，未发现实际作出提升宣称；长期实验出口仍需明确 |
| F03：SBOM 成品缺证据、发布出口不明确 | 当前归属 UNKNOWN；最终遗漏为 LEVEL 3 风险 | 计划中的供应链交付可能遗忘；锁/manifest 不能无说明替代 SBOM；不虚构已过截止日期 |
| F04：摘要/路线/版本来源滞后 | LEVEL 1 | 自动读取 result.json 会误判 Sensor/A 验收状态；人工也可能引用旧 v0.5 状态 |
| A01–A15 前移但 v1.0 未重定义 | LEVEL 2（合理移动） | 未来可能误以为 v1.0 无事可做；无需回退实现 |
| 旧 Gate D 大负载/soak 被当作 RC7 新实测 | LEVEL 1 的表述风险 | 影响评估是工程判断，不是统计等价；原报告已诚实保留限制 |
| 模型引用合法被当语义正确 | 已知质量限制；不是新架构漂移 | [G1/G2 方法与限制](ADVERSARIAL_EVALUATION_v0.6.0.md) 已记误推断，当前继续 SHADOW 有合理依据 |

未发现 LEVEL 4 或 LEVEL 5 证据。历史 Gate D 的 4 并发中 2 TIMEOUT、资源采样缺口 153.813523 秒、Outbox 398200 pending（无消费端）及有意保留任务仍是限制，不构成“生产稳定”结论；亦不自动要求引入 Kafka/Temporal。

# Recommended Corrections

只提出纠正建议，未经本轮自动执行：

1. 优先明确 F01/F02：将“规划层配对已完成”和“闭环收益未验证”写入统一状态表；记录本阶段 SHADOW 已获批准；由负责人决定长期闭环实验的后续归属，并分配到现有 v0.9/v1.0 出口，不默默遗忘。
2. 更新计划书当前状态、A01–A15 前移和 v1.0 责任；保留历史版本测试数字及 CONTROLLED LAB 限制。SBOM 纳入最终安全发布交付。
3. 补 v0.9 正式计划来源与上述小调整。继续保持 Inspect/Plan 完成、Implement 未开始，UI 设计等待，不因本审计自行启动开发。
4. 对 F04 使用有版本的新说明/索引澄清顶层 NOT_RUN 与子运行 PASS 的层次，不改历史运行证据来消除矛盾；后续实现时再修正产生摘要的代码。

# Final Judgment

**PLAN_CONFORMANCE: MINOR_DEVIATION**。仍沿原方向；A01–A15 前移、G2 阶段限定 SHADOW 均有明确依据。长期 G0/闭环价值实验和 SBOM 仍缺证据或明确出口，不能仅更新文字为“全部完成”。没有充分依据把已批准的 SHADOW 判成 MATERIAL_DEVIATION，也没有证据支持 OFF_TRACK。实际阶段顺序和实验范围发生变化且需承接未覆盖目标，因此比纯文档更新多一步路线确认。

**ENGINEERING_ALIGNMENT: ALIGNED**。v0.2–v0.5 与负责人限定的 v0.6 可靠性/安全/真实 Sensor/SHADOW 比较符合方向，12 条所审架构不变量 PASS；不等于全部未来产品/实验交付已齐。v0.6 PASS / CONTROLLED LAB 的既有工程判定保留。

**DOCUMENT_ALIGNMENT: STALE**。原方向、架构和 v0.9 五类交付仍有效，当前状态/验收版本/溯源需更新；没有证据支持 SEVERELY_STALE 所隐含的整体不可用程度。

**V0.9_PLAN_ALIGNMENT: ALIGNED_WITH_MINOR_ADJUSTMENTS。**

| 必答问题 | 结论 |
|---|---|
| 1. 整体仍沿原主线？ | 是；确定性控制、受限 AI、独立验证保持，存在长期价值实验及发布交付待明确事项 |
| 2. 哪些版本完全匹配？ | v0.2/v0.3/v0.4/v0.5 的版本核心目标 MATCHED；仅指当期边界，不把真实 Sensor/生产/语义准确率提前计入 |
| 3. 哪些提前？ | A01–A15 从 v1.0 前移 v0.6，合理 MOVED_EARLIER |
| 4. 哪些推迟？ | 当前 G2 改为 SHADOW 已获批准；更广闭环/G0 实验尚未安排到具体版本，不虚构延误日期。UI 设计等待未见日期违约 |
| 5. 有无遗漏？ | 原目标当前未覆盖：更广闭环/G0 证据、SBOM 成品；G2 本阶段 SHADOW 有批准依据，不能算未经批准漏做；未来产品项另列 |
| 6. 明显 Scope Creep？ | 未发现已实施的无依据扩展；Lab/TTL/ownership/capacity/0016 有明确阻断与授权依据 |
| 7. Architecture Drift？ | 未发现；12 条所审不变量 PASS，仅限证据覆盖范围 |
| 8. v0.9 Plan 一致？ | ALIGNED_WITH_MINOR_ADJUSTMENTS；五类覆盖、无新核心引擎/UI 偷跑，补正式计划溯源与价值限制 |
| 9. 计划书过时何处？ | v0.5 状态、真实 Sensor/A 验收、当前测试口径、v0.6/v0.9 进度、v1.0 责任；历史数字本身保留 |
| 10. 到 v1.0 真正剩余？ | 五类产品交付和 UI、长期价值实验归属确认、最终候选验收、安装/升级/恢复、文档/SBOM/安全发布/比赛冻结 |

审计到此停止。是否更新计划书、收缩或补齐实验、调整既有路线，由负责人决定；本报告不是实施批准。
