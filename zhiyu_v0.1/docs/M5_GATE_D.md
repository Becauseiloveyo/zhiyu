# Gate D — PASS

> 本文件保留该 Gate 完成时的阶段快照；后续完整验收与当前版本结论见 [v0.5 Validation](VALIDATION_REPORT_v0.5.0.md)。

`m5-gate-d-tests.xml`：24 passed / 0 failed / 0 skipped，53.67 s，真实 PostgreSQL / HTTP fixture。最终全量回归另见 Gate E。

验证 Proposal → 原有 AIPlan / TaskGraph → 原有 Authorization；未知 Capability、目标、参数、命令字段、环/缺失依赖、重复动作、累计数量/影响、能力定义变化、Scope 撤回、健康失效、过期 Context、非 Lab ASSISTED、Autonomy 限制均拒绝。SHADOW 不生成任务。两 worker 只有一条接受的 lineage。

AI Re-plan 复用 ResponseCycle / ReplanBudget / ReplanDecision，保持最大次数、总动作、时间、风险上限、新证据/重复计划约束。模型预算为零时，确定性 Re-plan 继续创建新计划并通过原有授权执行。Verification PASS 不触发 AI Re-plan。

固定 migration `0014_ai_proposals`；不修改 ai.5 Contract。完整 v0.5 尚未验收。
