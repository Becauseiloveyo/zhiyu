# Project Plan Baseline Audit

审计日期：2026-09-28。范围：计划符合性，只读审查既有源码、测试、迁移、运行记录与正式材料；只新增本次三份审计文档。未重新运行测试、启动 Lab、修改原计划或实施 v0.9。

## 1. 来源选择与权威边界

本机检索到的最新正式参赛资料为 2026-09-16 下载的配套 DOCX/PDF。两份资料 §10.1 的版本路线一致；PDF 第 17–18 页已渲染目视复核。文件修改时间只作为检索线索，不视作签署或批准时间。本审计没有声称检索了负责人其他设备、云盘或未提供的版本。

| 来源 | 定位与用途 | SHA256 / 版本 |
|---|---|---|
| [正式计划书 DOCX](<C:/Users/wc/Downloads/智御-网络安全自主决策与持续验证平台-参赛项目计划书（排版优化版） (1).docx>) | 最新参赛计划，§10.1 为版本路线，§8.2 为 G1/G2 方法；保留当时的状态表述 | `06e0ab1f93af39ff8113116282328ef2911c127501d87333e6317140429d9f12` |
| [正式计划书 PDF](<C:/Users/wc/Downloads/智御-网络安全自主决策与持续验证平台-参赛项目计划书.pdf>) | 22 页，§10.1 第 17–18 页；§8.2–8.3 第 15 页，指标续表第 16 页 | `79a399f690d64c23e9cb796abe53ae5b855d6def8312148556319ebae9438f79` |
| 9 月 11 日旧稿 `Downloads/Compressed/智御_网络安全自主决策与持续验证平台_项目计划书.docx` | 历史背景；其阶段图不能替代新版的明确版本表 | `88b3ea8e6e253871b06ba96437e014cb92a90cf0826ca8108ae31067942d111b` |
| [ai.5 冻结上下文](AI_CONTEXT_ai.5.md) / [原验收路线](../../zhiyu_ai5/docs/07_实验验收与路线.md) | 工程语义、M0–M5、A01–A15 与对照实验；冻结文档中的“未执行”是历史状态 | ai.5 Engineering Freeze |
| [v0.6 Final Report](VALIDATION_REPORT_v0.6.0.md) / [A01–A15 Matrix](A01_A15_ACCEPTANCE_MATRIX.md) / [Final Evidence Index](FINAL_EVIDENCE_INDEX_v0.6.0.md) | 当前实际验收及证据，不能反向改写原计划 | RC7 / CONTROLLED LAB |
| [V0.9_IMPLEMENTATION_PLAN.md](V0.9_IMPLEMENTATION_PLAN.md), [V0.9_REQUIREMENTS_TRACEABILITY.md](V0.9_REQUIREMENTS_TRACEABILITY.md), [V0.9_API_GAP_ANALYSIS.md](V0.9_API_GAP_ANALYSIS.md), [V0.9_GRAPH_DATA_MODEL_PLAN.md](V0.9_GRAPH_DATA_MODEL_PLAN.md), [V0.9_DEMO_SCENARIO_PLAN.md](V0.9_DEMO_SCENARIO_PLAN.md) | 当前 v0.9 Inspect + Plan；规划不是实现 | PLANNED |

来源优先级按问题区分：原目标看正式计划；安全语义看 ai.5；当前实现看代码及对应运行证据；具体后续变更看负责人明确指令。文档中的建议或未来目标不是本轮执行授权。本轮最新审计指令覆盖早先“继续完成 0.9”的实施请求。

## 2. 原始版本路线（原文目标，不以实际倒推）

| Version | Planned objective | Planned deliverables | Planned boundaries / exclusions | Planned acceptance / evidence | Dependency / order |
|---|---|---|---|---|---|
| v0.2 | Deterministic Event Intelligence（PASS） | Suricata/Wazuh Adapter、EventGroup、CorrelationDecision、Incident | 确定性聚合；原始告警不直接送 LLM；Adapter 不等于真实 Sensor 验收 | §10.1 当时列 147/147 + Docker 50/50；§7 保留样本及 lineage | 先统一数据与事件，再形成控制链 |
| v0.3 | Deterministic Response Control（PASS） | Plan、Task Graph、Capability、Authorization、Risk、Scheduler/Lease、Action Gateway | Proposal 不授予权限；不允许 LLM 直接执行；不能以回执成功推断安全成功 | §10.1 当时列 201/201 + Docker 81/81 | 依赖 v0.2；先确定性控制后 AI |
| v0.4 | Continuous Verification & Re-plan（PASS） | 三维独立 Verification、State Update、bounded Re-plan | 观测不足 INCONCLUSIVE；无新证据/预算耗尽停止；遏制不等于根治关闭 | §10.1 当时列 245/245 + Docker 135/135 | 依赖 v0.3 的执行及证据链 |
| v0.5 | AI Decision Layer（开发中） | Gate A Context/State、Gate B Model Gateway + 真实本地模型；Gate C 继续分析/建议校验及后续 Gate | §5、§7 明确 FACT/INFERENCE、证据引用、预算、只经原执行链；不宣称引用合法即语义正确 | 原计划状态 A/B PASS、C 进行中；完整 AI 评估待完整 Gate 后报告 | 确定性基线先成形；AI 非单点 |
| v0.6 | Reliability & AI Value | 真实 Sensor、G1/G2、Prompt Injection/模型/Worker/Sensor 故障、负载与安全加固 | §8.2 相同 Sensor/Capability/Authorization/Risk/Gateway/Verification；安全边界不得因比较而关闭 | 双源真实链；故障/负载记录；AI 价值比较需报告质量、拒绝、时延、Token/成本、Verification 与 fallback；无足够证据不能宣称增益 | 依赖 v0.5；先可靠性与价值证据，再比赛包装 |
| v0.9 | Competition-ready Demo | Dashboard、时间线、Attack/State Graph、报告、完整演示脚本 | 展示真实事实与限制；不能将模型假设画成攻击事实；原 §10.1 未指定 UI 框架或图数据库 | 完整可复现演示，结合 ai.5 M5 的实际时间线、数据图表、限制/复现材料；具体 UI 设计不是原计划已交付物 | 复用核心闭环，不重建安全引擎 |
| v1.0 | Stable Prototype | A01–A15 全面验收、文档、安装/升级与安全基线 | Stable Prototype 不等于生产 SLA 或多租户企业版；后续增强不自动纳入 | 原计划明确 A01–A15 在此版本全面验收；安装/升级与安全文档形成交付 | 在比赛展示之后做稳定原型最终验收 |

前四行测试数是计划书对当时结果的记录，不是给未来版本设置的固定测试总数。原计划没有为所有未来项目指定量化出口，不从现有 381 个测试倒造原计划门槛。

## 3. 计划横向约束

§4–5：单一 PostgreSQL 事实源、模块化单体、受控 Capability、Scheduler/Router/Risk 分责、独立 Verification、模型失败保留确定性链、数据出域受控。§5.8/风险章节要求固定第三方版本及 SBOM；依赖锁不自动等于 SBOM。

§8.2–8.3 与 ai.5 对照设计：G1 固定编排和 G2 AI 闭环共用聚合、状态、工具、授权、验证与资源预算。规划层 SHADOW 比较能回答建议合法性/成本问题，不能直接回答 AI 执行后的实际验证收益。ai.5 同时列 G0 工具/人工基线与 G3 定向消融；G0 属 M4 比较内容，G3 是对照设计选项，不能把每个建议实验都宣布为已逾期硬门槛。

§10.2 将 Zeek/OpenCTI、Tetragon/eBPF、Strix 深度集成、CALDERA/Atomic 扩展、Durable Workflow、Event Bus、Policy-as-Code、Workload Identity、Windows Validation Pool、OT Offline Lab、HA、多站点和多租户列为核心稳定后的增强。它们不是当前版本漏做的必交清单。

## 4. 已发生的后续变更与原计划分开登记

| 变更 | 可追溯依据 | 对原计划的影响 |
|---|---|---|
| A01–A15 提前到 v0.6 全面跑通 | [负责人 Remediation Cycle 指令](<C:/Users/wc/.codex/attachments/c7d34273-564d-44d1-a066-a0f6c821898b/已粘贴的文本.txt>) 明确要求最小增量消除 A05/A06/A07/A09/A11 阻断，且不得降低标准；[A01–A15 Matrix](A01_A15_ACCEPTANCE_MATRIX.md) | MOVED_EARLIER；需要同步路线，不回滚能力 |
| Lab 可逆状态能力、ownership/TTL/reconcile、恢复容量 | 同一负责人指令；旧 RC3 五项 NOT_RUN；RC7 实际状态变更和饱和恢复证据 | 满足冻结验收的具体实现，不是通用防火墙平台 |
| v0.9 先 Inspect + Plan、UI 等待设计 | 五份现有 v0.9 规划均明确 PLANNED，实施未开始 | 阶段约束；不能称 Competition-ready Demo 已完成 |
| G2 对照限定 SHADOW | [负责人 v0.6 开发与验证指令 §22–24](<C:/Users/wc/.codex/attachments/14cab7db-0d3f-471a-abab-f815d8347a0b/pasted-text.txt>) 明确 G2 为 `AI-assisted / SHADOW`，相同 Incident/Context，列比较指标；实际 80 例可核验 | JUSTIFIED_CHANGE；本阶段实验范围有明确负责人依据。它没有证明或取消长期闭环收益目标，后续归属尚需明确 |

## 5. 当前证据身份与审计限制

当前 RC7 `source_digest=f60a06b0db456ac2c7e282c5522241165747ab65592d64f5d06bd871e5c1aa05`，migration head `0016_lab_remediation`。本次重算 310 个 controlled files、28 个 frozen files 的 SHA256，全部匹配 RC_STATE。正式 v0.6 ZIP 重算 SHA256 为 `3afd802e3bee0945591d3b7f1e02303bafda33a63679e4fe543a4a72609003a5`。

381 = 最终镜像内 380 + 宿主 Compose 1；两个 JUnit 均 0 failed/0 skipped，不将宿主包裹的 runtime 检查重复算测试。182 runtime checks 与 A01–A15 是不同口径。历史 Gate C/D 与 RC7 定向复验按各自版本解释，不声称当前重新执行全套。

审计方法为静态代码/配置/迁移审查、历史原始证据复算与文档追溯；不是新的渗透测试、生产认证或全路径形式化证明。NO_EVIDENCE 表示在已提供并检查的工程/交付物中未找到；不证明其他未提供环境绝对不存在。
