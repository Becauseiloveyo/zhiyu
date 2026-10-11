# v0.4.0 — Continuous Verification & Re-plan Validation Report

## Environment / Version

Version **0.4.0**, Architecture **ai.5 Engineering Freeze**.
Host: Windows-11-10.0.26200-SP0; Docker Desktop 4.91.0.239619; Docker Compose version v5.5.1.
Docker Engine 29.8.0; Linux Python 3.12.14; PostgreSQL 17.11 (Debian 17.11-1.pgdg13+2); uid 10001; DB timezone UTC.
Actual environment: [host evidence](m4-host-environment.json), [Docker result](m4-runtime/zhiyu-smoke-b57553d275bd/result.json).

## Gate A — PASS

复用 frozen VerificationSpec / VerificationCheckSpec / AssertionSpec / Evidence / Scenario / Run。
Security 独立查询上下文；Business 新发 HEAD /health；Observation 独立检查 sensor health、Evidence
freshness、coverage、lag/loss、采样和窗口。执行 SUCCEEDED 与 assertion PASS/FAIL/INCONCLUSIVE
分开持久化，检查支持超时、错误、取消、限次恢复、租约 generation fencing 和幂等。
[初始 Gate A 验收](M4_GATE_A.md)，最终测试另包含取消与边界补强。

## Gate B — PASS

先验证证据资格，再按冻结三维规则聚合。Sensor unavailable/stale、缺失/冲突/过期 Evidence、
未完成检查/窗口、采样不足均阻止 PASS，保留 raw assertions 并产生 INCONCLUSIVE。
原始安全或业务断言在证据充分时失败，则 FAIL。判决有效期不晚于支撑证据/健康/运行窗。
Effectiveness 独立解释目标、业务、可观测性、残余风险和下一步。
[初始 Gate B](M4_GATE_B.md)，[时效与 Scope 复核](M4_RUNTIME_FINDINGS.md)。

## Gate C — PASS

使用 frozen StateEntity 保存独立 OBSERVATION，效果判断另存 INFERENCE。只读 DETECTION PASS
停留 VERIFYING，不宣称 CONTAINED / RESOLVED / CLOSED。FAIL/INCONCLUSIVE 可创建新只读
计划，保留 parent_plan_id / trigger_verification_id / policy / reason / count。
默认最多 2 次 replan、12 个预留动作、600 秒、零自动风险升级；R0 ceiling 不能自动生成 R1
升级任务。次数、动作数、时间、无新语义证据或重复行动导致停止；需审批时不执行升级动作。
每个新 Task 再次经过原授权、Risk Gate 和 Gateway。双 Worker、回调重放、事务中断恢复均验证。
[Gate C](M4_GATE_C.md)、[运行与 API](CONTINUOUS_VERIFICATION.md)。

## Gate D — PASS / Docker Runtime

**135/135 runtime checks PASS**。实际 build/up/migration/bootstrap/full tests，保留 M1–M3
回归并完成 `SCN-LAB-AUTH-01 v0.4 Closed Loop` 的四个受控 Synthetic/Lab 场景。
原始事件 → 标准事件 → 分组/关联 → Incident → Plan → Task → Authorization/Risk → Action
→ ActionResult → 独立三维检查 → VerificationResult → StateEntity → PASS 或 bounded replan。

| 场景 | Plan / Task / Action / ActionResult | Check / Evidence / Verification | 最终 Incident | 后续 |
|---|---|---|---|---|
| pass | 1 / 4 / 4 / 4 | 3 / 4 / 1 | VERIFYING | NO_REPLAN |
| security | 2 / 5 / 5 / 5 | 3 / 4 / 1 | EXECUTING | CREATED |
| offline | 2 / 5 / 4 / 4 | 3 / 4 / 1 | PLANNED | CREATED |
| business | 2 / 5 / 4 / 4 | 3 / 4 / 1 | PLANNED | CREATED |

每条链均为一个 Incident。每个 Verification 有 3 份独立检查 Evidence，另有 1 份决策时资格诊断
Evidence；诊断不替代探测。HTTP 服务日志确认 Action 后新增一个独立 HEAD，请求不复用执行回执。
每条链还保存 1 个 VerificationSpec、3 个持久化 Check、1 个 EffectivenessDecision、
4 个 StateEntity（3 个 OBSERVATION + 1 个 INFERENCE）和 1 个 ReplanDecision；
NO_REPLAN 也有决策记录。上表 Action 数量明确区分新任务已执行和仍待执行。
高风险动作实际执行数 **0**；AI/model calls **0**；REAL SENSOR RUNTIME **NOT_RUN**。

## PASS Chain

四个 Action 实际执行，三维检查 PASS，Effectiveness VERIFIED_EFFECTIVE，残余风险保留。
DETECTION PASS 只确认只读上下文和业务健康；冻结状态机没有 detection_pass 修复/遏制边，
因此 Incident 保持 VERIFYING。没有虚构威胁已消除。

## FAIL Chain / Re-plan

动作全部 EXECUTION_SUCCESS，独立 Security binding-version 断言故意不满足，结果 **FAIL**。
Plan v1 → Verification FAIL → Plan v2，新的只读 Task 通过新 AuthorizationDecision 并实际执行。
原 Plan/Action/Verification 保留，未覆盖失败历史。恢复/重放不产生第二个逻辑 Plan v2。

## INCONCLUSIVE Chain / Business Safety

传感器 OFFLINE 映射为 UNAVAILABLE，使原始观测失去资格，最终 **INCONCLUSIVE**，仅安排
补充只读观测，不关闭 Incident。另有 Security PASS + Business HTTP 500 + Observation PASS
场景，Action/Check 均可执行成功但 Business assertion FAIL，最终必须 **FAIL**。

## Restart / Concurrency / Audit

真实 Verification worker 领取后退出 23；两个独立配置的 Worker 完成其余检查；过期旧 Worker
被 fencing，重启 Worker 以 generation 2 恢复。数据库 stop 时 health=200/ready=503，恢复后
闭环继续。Verification 提交后进程退出 24、Re-plan 提交后退出 25，API 重启/重复回调返回
同一逻辑结果。测试另覆盖事务提交前崩溃回滚以及两个 replanners 的数据库竞争。
观测与 Evidence 的 PostgreSQL xmin 一致，Audit 哈希链有效，Audit / Outbox 事件配对。

## Database Changes

新增固定 Alembic `0008_verification → 0009_decisions → 0010_replan`；8 张内部表，复用
30 张契约表，总 63 张业务/内部表 + alembic_version。FK、唯一约束、租约 CHECK、托管 Spec /
Check identity / Observation / VerificationResult / Effectiveness / Replan 不可变守卫经过测试。
`0007 → head → 0007 → head` 保留已落库 v0.2/v0.3 数据；完整 base/head roundtrip 无元数据漂移。
降级删除新增元数据，不能代替业务数据库备份。ai.5 与原 0001–0007 迁移及旧 SQL 原样保留。

## Tests

**245 total / 245 passed / 0 failed / 0 skipped**。
原 201 个测试全部保留；新增 44 个节点。Linux non-Compose 244 passed，
宿主真实 Compose 1 passed。Linux pytest 实际报告 **2 warnings**，为两类上游 TestClient deprecation warning（Starlette httpx、anyio
BlockingPortal）保留，未屏蔽。Ruff、format、mypy、compileall、schema snapshot 另由包验收检查。
[完整 Linux JUnit](m4-runtime/zhiyu-smoke-b57553d275bd/test-results.xml)、[宿主 JUnit](m4-host-compose-tests.xml)。

## Performance

100 / 1,000 个合成 verification runs 分别执行 300 / 3,000 个独立检查，使用真实本地 HTTP 和
PostgreSQL，顺序执行；性能夹具明确配置本地回环 Scope 的 100 RPS 上限，正式闭环使用原
1 RPS Scope，独立探测共享 Action 的速率配额。每组最后一次故意 FAIL 并实际创建一个 re-plan，其余为 PASS/no-replan。
总耗时：19.758 / 157.873 秒。

| 实测阶段 | 100 runs：样本数 / mean / p95 ms | 1,000 runs：样本数 / mean / p95 ms |
|---|---:|---:|
| spec_generation | 100 / 9.797 / 11.590 | 1000 / 7.688 / 10.366 |
| check_scheduling | 300 / 17.761 / 19.607 | 3000 / 13.644 / 17.993 |
| security_check | 100 / 7.053 / 8.428 | 1000 / 5.534 / 7.781 |
| business_check | 100 / 11.235 / 13.624 | 1000 / 8.766 / 11.994 |
| observation_check | 100 / 9.545 / 11.552 | 1000 / 7.628 / 10.155 |
| decision | 100 / 13.762 / 16.251 | 1000 / 11.172 / 14.803 |
| state_update | 100 / 7.100 / 8.952 | 1000 / 5.337 / 7.678 |
| replan_evaluation | 100 / 25.048 / 29.567 | 1000 / 19.255 / 25.724 |
| replan_creation | 1 / 56.988 / 56.988 | 1 / 36.917 / 36.917 |

这是服务阶段基线，部分计时不含外层 HTTP 和最终事务提交，不能推导生产并发吞吐或 SLA。
`replan_creation` 每组 1 次，明确区分大多数 no-replan 评估样本。
[全部原始样本](m4-runtime/zhiyu-smoke-b57553d275bd/verification-benchmark.json)。旧 v0.3 性能报告保留，未把历史数据当成本次测量。

## Security / Runtime Findings

修复：判决有效期可能长于支撑证据、检查后 Scope 撤销遗漏、连续计划激活后的请求重放、
路由匹配冲突、PostgreSQL JSON 维度聚合，以及独立探测遗漏 Scope 共享速率预算。
独立验证取消不制造 Evidence。性能夹具来源与目标地址冲突被 Scope 正确拦截后也已修正。
首次 Docker run 的 239 Linux tests 通过，但 API 重启后随机宿主端口改变导致验收地址失效；
独立容器复现端口变化后，验收改为每次重新发现地址。失败日志保留，不计作通过。
[完整 Findings](M4_RUNTIME_FINDINGS.md)。

## Architecture Findings

**No ai.5 architecture change required.** 资格过滤、DETECTION PASS 的合法停留状态、M3 的
后续生命周期集成边界均先记录解释，再做最小实现衔接：[Architecture Findings](M4_ARCHITECTURE_FINDINGS.md)。

## Remaining / Milestone / Deliverables

AI / LLM / Model Gateway 未实现；真实 Sensor Runtime、A01–A15、生产负载/SLA 未验收。
**v0.4.0 PASS**；本轮没有进入 v0.5 实现。

完整 ZIP `智御_Project_v0.4.0_Continuous_Verification_Replan.zip`、本报告、
[Files Changed](FILES_CHANGED_v0.4.0.md)、外部 SHA256SUMS_v0.4.0.txt 与
PACKAGE_VALIDATION_v0.4.0.json。包内 MANIFEST 覆盖所有其他文件；包检查另验证旧测试保留、
冻结文件、历史 ZIP、已知本机凭据排除、源码对应关系、逐文件哈希和 ZIP CRC。

## Source correspondence

[源码对应校验](m4-source-correspondence.json)：实际测试镜像与性能镜像源码摘要一致。最终工程与镜像的所有源码经统一换行后逐字节一致；原始字节也全部一致。最终源码静态检查另行通过。
