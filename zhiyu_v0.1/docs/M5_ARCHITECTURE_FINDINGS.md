# v0.5 architecture interpretation

**No ai.5 architecture change required.**

冻结的 StateEntity 使用 OBSERVATION / INFERENCE；Context 的 MODEL_HYPOTHESIS 通过 INFERENCE + 明确 MODEL_INFERENCE 来源表达，无需修改冻结枚举。来源 unknown 与配置状态均保留标识，不升级成 FACT。

ContextBundle / ModelRun / AIPlan 等冻结契约继续保存领域对象；新增表仅保存不可变 Context body/manifest、模型调用身份、预算/回执、分析、Proposal 与决策协调信息。0011–0015 是固定 SQL 增量迁移，不从未来 ORM 动态生成历史迁移。

SHADOW/ASSISTED 是 AI 建议影响策略，与 EnvironmentProfile 的 autonomy_mode 分开。模型输出通过验证后成为普通计划，不携带预授权；AI re-plan 进入原 ResponseCycle，不能越过原风险/次数/时间/动作预算。

对于 Supported Finding，本版能验证 Evidence 引用、环境/Incident/Context 归属、来源内容摘要、资源与时间窗口，不能通用地证明自由文本被 Evidence 语义蕴含。因此接受标记为 REFERENCE_GROUNDED，模型产生的 State 永远为 INFERENCE，confidence 明示未校准。自然语言质量需逐例审查和后续更广评估。

现有只读 DETECTION 验证 PASS 仍停留 VERIFYING；模型建议或“成功”表述不引入新的关闭事件边。新增有副作用响应、正式审批执行、真实传感器和生产质量评估不属于本次实现。
