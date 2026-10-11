# Gate C — PASS

2026-09-14 最终代码 `0.2.0`：**147 passed / 0 failed / 0 skipped**（Linux 146 + 宿主 Compose 1），**Docker runtime 50/50 PASS**。Ruff check / format、mypy 56 源码文件、compileall、Schema snapshot 校验通过。两种上游弃用警告保留。

Incident Promotion Policy、多因子风险与解释、状态/时间/版本受限合并、Evidence 来源和所有权、NEW→TRIAGED→INVESTIGATING 守卫/CAS/重试、环境隔离及 keyset 分页已实现。并发创建、事务中断、重启、旧策略 no-merge、不同 Incident 的 Evidence 拒绝、raw_ref 伪造来源和 validation/production/OT 边界均测试通过。

固定合成链路在真实 Docker HTTP 中得到 4 Raw → 4 NormalizedEvent → 2 EventGroup → 2 CorrelationDecision → 1 Incident，3 Evidence、风险 62/P2。无关用户留在独立组中；API 和数据库重启、重放后不重复建组/决策/Incident，Audit/Outbox 和 lineage 保持有效。

Migration `0004_incidents` 增加 incident_analysis、incident_groups、incident_events、incident_promotions 和 Evidence 所有权 FK。数据库现为 44 张业务/内部表加 Alembic 版本表。upgrade/downgrade/upgrade、旧 M1.1 数据保留和无 ORM 漂移通过。

最终依据为 [验收报告](VALIDATION_v0.2.0.md)、[运行 JSON](m2-runtime/zhiyu-smoke-89199b674d14/result.json)、[Linux JUnit](m2-runtime/zhiyu-smoke-89199b674d14/test-results.xml)、[宿主 JUnit](m2-final-compose.xml) 与 [1k/10k 实测](m2-runtime/zhiyu-smoke-89199b674d14/benchmark.json)。早期 gate-c-tests 与首轮 M2 runtime 是历史证据，未代替最终代码验收。

当前结论为 **M2 Event-to-Incident Phase PASS**。REAL SENSOR RUNTIME / A01–A15：NOT_RUN。AI、Task/Risk Gate/Action/Verification runtime 未实现；冻结 ai.5 不变。
