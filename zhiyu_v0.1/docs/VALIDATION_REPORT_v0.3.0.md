# v0.3.0 — Deterministic Response Control Validation Report

## Environment

- Host: Windows-11-10.0.26200-SP0；Docker Desktop WSL2 Linux 容器。
- Docker Desktop: 4.91.0.239619；Docker Compose: 5.5.1，见 [宿主环境实测](m3-host-environment.json)。
- Docker Engine: 29.8.0 / linux / amd64。详细 Client/Server 版本见原始 runtime JSON；未凭配置推断运行结果。
- Runtime Python: 3.12.14；PostgreSQL: 17.11 (Debian 17.11-1.pgdg13+2)；DB timezone: UTC；容器 uid: 10001。
- 验收时间：2026-09-15T05:47:05.531608+00:00 → 2026-09-15T05:56:04.833062+00:00。
- [原始 Docker 验收记录](m3-runtime/zhiyu-smoke-c85b15ffaa87/result.json)，含逐条命令、返回码、耗时及脱敏日志。

## Version

**v0.3.0 — Deterministic Response Control**。Architecture / Engineering Contract: ai.5 Engineering Freeze。冻结 contracts.py、baseline、0001–0004 migration、历史 SQL、requirements 锁文件保留；未重新生成仓库。

## Gate A

PASS — DeterministicResponsePlanner 复用 AIPlan；零模型调用。Incident/version/planner/policy 唯一身份、解释和输入快照、关系化 Task DAG、合法状态转换、依赖就绪、事务回滚、重启和版本测试通过。[Gate A](M3_GATE_A.md)。

## Gate B

PASS — 固定 CapabilityManifest 与独立 CapabilityHealth；完整 AuthorizationContext/执行输入快照和可解释决定；Scope/身份/目标/参数/digest/风险/健康/证据/预算/TTL fail-closed。[Gate B](M3_GATE_B.md)。R0/R1 依策略允许，Lab R2 按 Scope 和模式允许，Production R2 REQUIRE_APPROVAL，R3–R5 与 STATE_CHANGE 不执行。

## Gate C

PASS — PostgreSQL 锁与 SKIP LOCKED、两个 Worker 身份、租约到期、递增 generation、旧 ACK 拒绝、有界退避；唯一 ActionRequest、durable dispatch、真实只读 executor、不可变回执、同事务 Audit/Outbox、API 分页与隔离均通过。[Gate C](M3_GATE_C.md)。

## Gate D

PASS — 全新随机 Compose project 实际 build/up/migrate/bootstrap，HTTP API → Scheduler → Authorization → Gateway → HEAD /health 实际运行。Worker 子进程在持久化 lease 后以退出码 23 中断；重启后有效 lease 未重复领取，到期+backoff 后 generation 2 继续完成。API/Gateway 重启后的重放未再次探测；PostgreSQL 停止时 health=200/ready=503，恢复后数据摘要一致、调度 IDLE。

## Database Changes

- 复用 30 张 ai.5 Contract 表；新增 11 张 internal runtime 表：0005 三张、0006 六张、0007 两张；另给 task_runtime 添加 retry_allowed。
- 现有 44 张业务/内部表增加为 55 张；包含 alembic_version 共 **56 张**，head **0007_execution**。
- Plan unique identity、同环境/同 Plan 复合 FK、Task 图关系、Action 幂等、action/generation dispatch 唯一、不可变授权与回执、状态/时间/hash CHECK 已落库。
- 真实 0004 → head → 0004 → head 保留已填充 v0.2 raw/event/group/decision/incident/evidence/audit/outbox 的逐表 JSON 字节摘要。降级删除 M3 runtime 元数据，不作为业务无损撤销方法。
- [Schema](SCHEMA.md)；[完整 0007 SQL](../schema/0007_response_control_postgresql.sql)。

## Tests

| 指标 | 结果 |
|---|---:|
| total / passed | **201 / 201** |
| failed / skipped | **0 / 0** |
| PostgreSQL integration | 114 |
| pure/static/in-process | 86 |
| host Compose acceptance | 1 |
| 新增测试相对 v0.2 | 54 |
| 原有测试保留 | 147 |

Linux 容器中 200 项非 Compose 测试全部通过；宿主 1 项 Compose 测试实际启动整套验收。合计按唯一测试计数，未把 Gate 重跑次数累加。两类上游 TestClient 弃用告警（httpx/Starlette、anyio BlockingPortal），不影响结果；完整告警与测试时间见 JUnit/日志。没有删除旧测试，旧 schema inventory 与宿主 timeout 随实际工程规模更新。

- [Linux JUnit](m3-runtime/zhiyu-smoke-c85b15ffaa87/test-results.xml)
- [宿主 Compose JUnit](m3-final-compose.xml) / [完整宿主日志](m3-final-compose.txt)
- Ruff check/format、mypy **74** source files、compileall、schema snapshot consistency 均通过，见 [静态检查](m3-final-static.json)。

## Docker Runtime

**81/81 PASS**：完整功能/性能运行的 80 项检查，加上修正 profile 退出清理后实际重验的 1 项容器清理检查。保留 M1/M2 功能运行检查，并新增受控响应、8 组负例、重启/重试、实测性能。旧 1k/10k 事件基准未重复计入本轮，历史 v0.2 报告仍保留；本轮性能项改为实际 100/1,000 次响应任务。没有把只跑 unit test 作为 Docker 通过。数据库未发布宿主端口；API 只绑定 loopback；HTTP target 无宿主端口、只读根文件系统、drop ALL capabilities；全部运行于验收项目专用网络。验收结束：stopped_removed_volume_retained，命名测试卷保留。

退出核对发现 response-test profile 的目标容器被默认 down 遗漏；清理入口现显式启用该 profile，并查询项目标签确认零残留容器。修正后的清理函数已对本次及前次残留测试项目实际运行；相关命令追加到原始报告，cleanup_revalidated_at 独立记录。未重新计入功能或性能样本。

初次完整验收在 PostgreSQL 重启恢复的健康等待超时处失败，未计为 PASS。数据同步/恢复日志和修复记录保留在 [Runtime Findings](M3_RUNTIME_FINDINGS.md)；最终结论只采用修复后完整重跑的结果。

## Golden Chain

**1 SecurityIncident → 1 Plan → 4 Tasks → 8 AuthorizationContexts → 8 PolicyDecisions → 4 ActionRequests → 4 EXECUTION_SUCCESS receipts**。

每个动作有首次授权及 Gateway 新鲜授权重检。5 个 WorkerLease 包含中断的 generation 1 和恢复的 generation 2。3 次数据库只读查询 + 1 次实际 HTTP HEAD /health；HTTP 服务日志确认仅收到 1 次 HEAD，完成后 API/Gateway 重放没有再次调用。Incident 仍为 TRIAGED；VerificationResult=0；高风险执行次数=0。

源链仍为 SYNTHETIC：4 Raw → 4 NormalizedEvent → 2 EventGroup → 2 CorrelationDecision → 1 SecurityIncident，3 Evidence，风险 62/P2。真实源地址/端口和当前输入保存在 m3-effective-inputs.json；传感器健康为明确标注的测试断言，**REAL SENSOR RUNTIME=NOT_RUN**。

| Case | 实际结果 | 执行器调用数 |
|---|---|---:|
| correct_scope | EXECUTION_SUCCESS | 1 |
| wrong_target | DENIED | 0 |
| wrong_environment | REJECTED | 0 |
| mutated_digest | DENIED | 0 |
| offline_capability | DENIED | 0 |
| r3_risk | DENIED | 0 |
| expired_worker | REJECTED | 0 |
| duplicate_action | EXECUTION_SUCCESS / DUPLICATE on replay | 1 |

负例使用同样的 Incident→Plan→Task→Authorization→Gateway 服务链。R3 为新隔离验收数据库中的暂时风险配置故障注入，拒绝后恢复目录；没有实现 R3 执行器。HTTP 200/302 不跟随/timeout、执行后回执前中断、旧 generation ACK 拒绝另由真实 PostgreSQL/本机 HTTP 测试覆盖，并在 Linux 全套测试中通过。

## Performance Baseline

| 实测阶段 | 100 次：样本数 / mean / p95 ms | 1,000 次：样本数 / mean / p95 ms |
|---|---:|---:|
| Plan generation | 34 / 10.399 / 15.938 | 334 / 10.472 / 12.625 |
| Task graph creation | 34 / 22.637 / 30.661 | 334 / 21.749 / 25.933 |
| Authorization inputs | 100 / 13.581 / 17.425 | 1000 / 13.647 / 16.086 |
| Risk / Policy Gate | 100 / 0.042 / 0.073 | 1000 / 0.041 / 0.073 |
| Scheduler lease | 100 / 19.181 / 24.212 | 1000 / 19.540 / 23.810 |
| Gateway overhead | 100 / 84.025 / 103.316 | 1000 / 86.629 / 101.943 |
| Safe database read executor | 100 / 1.900 / 2.714 | 1000 / 1.880 / 2.938 |

实测工作负载为每组 1 个合成 Incident，通过 34/334 个合成策略版本产生 102/1,002 个 Task，执行其中 100/1,000 个，末尾 2 个保留未执行。顺序服务调用，真实 PostgreSQL；3 种数据库只读能力。没有 HTTP 序列化、并发扩展性或生产 SLA 声明。Plan generation 与 graph creation 是两个单独采样阶段；authorization/policy 采样首次决定；Gateway overhead 包含重检、存储及结果提交并扣除 adapter 调用耗时，executor_ms 仅实际 adapter 调用。

两个工作负载总耗时分别为 17.076s / 173.606s。Golden Chain 实际网络 HEAD 的 executor latency 为 **1.128 ms**，status_code=200；样本数 1，不作网络性能分布推断。

[全部原始样本与环境](m3-runtime/zhiyu-smoke-c85b15ffaa87/response-benchmark.json)。实际 source_digest：`af39c0168e09855a187634e9d6bbbd5aeeeac72cb7452a275977bfcd0cb58043`。

## Security Findings

1. 授权后到 adapter 调用前仍存在暂停/状态变化窗口：新增执行前 lease、Task、Profile/Scope/资源、策略、能力配置/health、sensor freshness、evidence 和 budget 重检；环境锁覆盖有界只读调用。定向变更测试证明不调用 adapter。
2. 执行后回执提交前进程中断不可声称 exactly-once：持久化 dispatch 与历史 UNKNOWN，下一 generation 仅按 READ_ONLY_REPLAY 重读，logical Action 不增殖，旧 ACK 拒绝。未来有副作用的 adapter 默认禁止。
3. 策略撤销不能擦除已获得的回执：完成路径使用已持久化授权策略保存回执，同时继续验证活租约；定向撤销测试通过。
4. arbitrary command/URL、重定向、DNS/proxy、过长头和不受限超时被入口/adapter 排除；TLS 使用默认系统 CA 和主机/IP 验证。网络访问仅已注册 numeric source/target/port。
5. Capability health 与 sensor health 分离。默认无有效 Scope、policy、health、evidence 或身份时拒绝。测试断言不是真实 Sensor Runtime。
6. 授权控制仍依赖可信数据库/运维管理；Audit hash chain 未外部签名或锚定。性能采用环境级保守锁，尚未验收生产并发和大规模多租户吞吐。

## Architecture Findings

**No ai.5 architecture change required.**

AIPlan 名称保留，确定性 planner 记录 no-model 元数据；ActionResult 使用既有 ActionAttempt 的内部执行回执，没有建立另一套冻结领域 Contract。READY 为 Task QUEUED+依赖/时间/lease 谓词，LEASED 为 WorkerLease 事实，未新增枚举。WAITING_APPROVAL 经 ai.5 已有转换抵达，本版本不执行审批后高风险动作。

## Remaining

- Verification Engine（三维检查）— NOT_IMPLEMENTED。
- Re-plan runtime — NOT_IMPLEMENTED。
- AI / LLM / Model Gateway — DISABLED / NOT_IMPLEMENTED。
- Real Sensor Runtime — NOT_RUN。
- A01–A15 平台验收 — NOT_RUN。
- 真实靶场安全闭环、审批执行流程、生产负载/SLA — 未验收。

## Milestone

**v0.3.0 PASS**。范围为 Deterministic Response Control；execution success 不等于 security success。此次不进入 v0.4 实现。

## Deliverables

- 完整工程 ZIP：`智御_Project_v0.3.0_Deterministic_Response_Control.zip`。
- 本 Validation Report；[Files Changed](FILES_CHANGED_v0.3.0.md)。
- 外部 `SHA256SUMS_v0.3.0.txt` 和 `PACKAGE_VALIDATION_v0.3.0.json`。
- 包内 MANIFEST.sha256 覆盖除清单自身外每个文件；ZIP CRC、逐文件字节、重复名称、冻结文件、原有版本包、已知本机凭据排除及链接检查由发布脚本验证。包检查结果以独立 Package Validation 为准。
