# Gate B — Capability + Authorization + Risk — PASS

进入 Gate C 前：完整非 Compose 回归 **180 passed / 0 failed / 0 skipped**，随后补充健康历史幂等和不可变快照两项测试，最终专项 **27 passed / 0 failed / 0 skipped**。两次覆盖的不同非 Compose 案例共 182 项；不重复累计专项。证据：[完整 JUnit](m3-gate-b-tests.xml)、[完整输出](m3-gate-b-tests.txt)、[最终专项 JUnit](m3-gate-b-final-focused.xml)、[专项输出](m3-gate-b-final-focused.txt)。Ruff、mypy 66 源码文件通过。Compose 留到最终集成验收。

CapabilityManifest 与 CapabilityHealth 分离，显式结构化输入，版本/定义摘要、资源/环境支持范围、权限、autonomy、风险、业务影响、只读重试策略和健康历史持久化。跨环境安装同一全局能力使用数据库互斥；同时间健康重复幂等，冲突和旧观察拒绝。

ScopeEvaluator 与 RiskPolicyGate 使用服务端资源、Scope、当前 profile/policy、传感器、Evidence、budget 和 lease 构造不可变 AuthorizationContext / AuthorizationDecision 及完整内部快照。R0/R1 与 Lab R2 允许，Production R2 要求审批，R3/R4/R5 拒绝。参数摘要篡改、Scope/目标绑定变化、失效能力/传感器、autonomy、业务影响、policy/source 变化、未知版本、过期控制和租约及跨环境拒绝已验证。

无法解析到合法 Capability/Environment/Resource 的请求在 Action admission 阶段拒绝，不伪造满足 FK 的 AuthorizationContext；合法 Action 的策略决策完整留存。ActionRequest、授权、预算、Audit/Outbox 保持同事务；注入故障无部分 intent。此 Gate 没有调度或 executor 调用。

0006_authority 新增六张内部表，复用既有能力、健康、ActionRequest、AuthorizationContext/Decision 契约表。Scope、Action 参数和冻结 ai.5 不变。当前阶段通过不代表 v0.3 最终通过。
