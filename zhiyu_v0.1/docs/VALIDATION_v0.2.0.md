# v0.2.0 — Deterministic Event Intelligence 验证报告

验收日期：2026-09-14。结论：**v0.2.0 PASS / M2 Event-to-Incident Phase PASS**。本报告对应最终代码 `0.2.0`，权威运行记录为 [result.json](m2-runtime/zhiyu-smoke-89199b674d14/result.json)。Task / Risk Gate / Action / Verification / AI 运行时不属于本次通过范围。

## Environment

| 项目 | 实际环境 |
|---|---|
| 宿主 / 容器 | Windows，Docker Desktop WSL2；Linux x86_64 |
| Docker | Desktop 4.90.0；Engine 29.7.2 linux/amd64；Compose 5.5.1 |
| Kernel | 6.6.87.2-microsoft-standard-WSL2 |
| Python | 3.12.14，容器非 root UID 10001 |
| PostgreSQL | 17.11 Debian，数据库时区 UTC |
| 性能环境 | 容器可见 16 个逻辑 CPU；共享开发机，未进行 CPU/内存独占隔离 |
| 最终运行 | 2026-09-14 02:47:57–02:54:19 UTC（北京时间 10:47:57–10:54:19） |

容器镜像按 digest 锁定；依赖版本未升级。Windows JUnit 保留宿主进程自己的时区标记；运行记录及源事件以 UTC 为准。日志里的故障注入错误属于被断言的负例，不能仅按日志中出现 ERROR 判定整个验收失败。

## Version

当前代码：**0.2.0**。Architecture / Engineering Contract：**ai.5 Engineering Freeze**。AI：**DISABLED**；主动安全执行：**DISABLED**。

最终 Docker benchmark 记录的源码 SHA256 为 `282b8104c17cb5a96520c3f14c2d023d27444e9d185a3ab84fc72f355875d772`，交付前已按同一算法核对当前 `src/**/*.py`。算法为按路径排序，拼接各文件相对 `src` 的 POSIX 路径与原始字节后计算 SHA256；不是 Git commit 或 ZIP 摘要。

与保留的 M1.1 DockerRuntime ZIP 比较，下列文件字节完全一致：

| 冻结文件 | SHA256 |
|---|---|
| `src/zhiyu/domain/contracts.py` | `663a7a597d2ef03fd2db25278858c25a5ce92fe30e55f0d3f21125503a9d85fb` |
| `migrations/versions/0001_m1_1_m1_1_ai_5_initial_postgresql_schema.py` | `e7efd4139a0c2e4c9c89fc21da3b214803b37b8d5a84ce3ad1a7447eaf3bac9f` |
| `schema/0001_initial_postgresql.sql` | `9fe5476330de0cf497cc0ab7386a35b1a6ab8731d230f5760d672a613e7bb704` |

冻结模型与 JSON Schema 一致性、全部 Golden 对象校验也包含在最终测试中。

## Gate A — M2.1

**PASS**。正式实现 Suricata EVE alert/http/dns/tls/flow 和未知合法类型；Wazuh authentication/SSH/web/application/Windows-Sysmon/generic alert。AdapterRegistry 显式注册，Adapter 仅 Parse / Validate / Normalize / Map，复用 ai.5 NormalizedEvent。

12 组 raw/expected Golden Mapping、severity/时钟边界、缺失字段、坏 JSON/IP/protocol、未知类型和 provenance 均通过。源数据没有的 ATT&CK 信息不推断。Severity 映射有版本且保留原值；不可信时间按记录拒绝，不伪造时间。原始字节、摘要、每次投递结果和结构化错误持久化；单条映射失败不影响合法邻居，存储故障回滚整批。

先通过 [Gate A](GATE_A.md) 的 112 项非 Compose 测试和真实 Docker 回归，再开始 Gate B。最终完整测试再次覆盖其实现与后续边界修复。

## Gate B — M2.2

**PASS**。实现版本化 CorrelationKeyBuilder、固定 UTC 窗口、关系型 membership/checkpoint、EventGroup 和 CorrelationDecision。跨源认证按环境、来源/actor、用户、目标、服务/transport、活动、结果与时间关联；不同用户、目标、来源、环境、窗口及 validation context 有负例。

同 fingerprint 的独立 provenance 保留全部事件；转发独立性由服务端 provenance root 配置。迟到、过期、未来事件隔离且不可升级；已关闭窗口不重开。乱序到达、积压分批、两个 worker 竞争、事务故障及重启重试均通过。决策保存关联理由、版本、维度、来源多样性与有界排除候选；confidence 表示证据维度覆盖，不是攻击概率。

在进入 Gate C 前，[Gate B](GATE_B.md) 的 122 项非 Compose 测试通过。最终 Docker 真实重启/重放补充验证持久化行为。指标来自数据库实际记录；压缩比指成员数/组数，未删除证据。

## Gate C — M2.3

**PASS**。实现确定性 Incident Promotion Policy、带解释的多因子风险计算、受状态/时间/策略版本约束的合并，以及 Incident → Group → Event → Evidence/raw_ref 回溯。未满足升级条件的结果也持久化并解释。

支持 NEW → TRIAGED → INVESTIGATING，使用 expected_version、来源/Evidence/Scope 守卫与幂等重试。只声明这些阶段；后续状态没有虚构 runtime。Incident 及 lineage API 支持 keyset 分页、稳定排序、环境授权、状态/风险过滤，无权限对象与不存在对象均返回 404。

同环境行锁、唯一约束、检查点与事务覆盖并发建立、失败回滚和恢复；Incident、Evidence、Audit、Outbox 保持原子提交。[Gate C 记录](GATE_C.md) 给出最终证据。

## Database Changes

保留原 30 张 Contract 表及 4 张基础设施表，新增 10 张内部存储/关系表；共 **44 张业务/基础设施表 + 1 张 alembic_version = 45 张**。最终数据库实际检测到 90 个 FK、31 个 unique constraint、296 个 CHECK、52 个索引。

| Migration | 新结构 |
|---|---|
| `0002_adapters` | `raw_records`、`raw_deliveries`；原始 BYTEA/SHA256、投递结果、映射证明、不可变触发器 |
| `0003_correlation` | `event_group_state`、`event_group_members`、`correlation_decision_inputs`、`intelligence_runs` |
| `0004_incidents` | `incident_analysis`、`incident_groups`、`incident_events`、`incident_promotions`；Evidence 同 Incident 所有权约束 |

Head 为 `0004_incidents`。固定 Alembic migration 实际执行 upgrade → downgrade → upgrade、无 ORM 漂移；旧 M1.1 事件升级后可读取并幂等重放。新完整 SQL 为 [0004 快照](../schema/0004_event_intelligence_postgresql.sql)，原 0001 SQL 保留。

Downgrade 会移除新增内部数据，不是无损业务回滚；实际业务回退需要备份。本次 roundtrip 仅用于隔离测试数据库。

## Tests

最终独立测试案例合计 **147 / passed 147 / failed 0 / skipped 0**。

| 分类 | Passed | 执行位置 |
|---|---:|---|
| Pure / static / in-process tests | 85 | Linux test 容器 |
| PostgreSQL integration | 61 | Linux test 容器 + 真实 PostgreSQL，每例独立 schema |
| Docker Compose orchestration | 1 | Windows 宿主，驱动 Linux 容器和真实 HTTP |
| 合计 | **147** | 两个 pytest 进程的不同案例，不重复累计 |

容器 [JUnit](m2-runtime/zhiyu-smoke-89199b674d14/test-results.xml)：146 passed，0 failed，0 skipped，31.938 秒。宿主 [JUnit](m2-final-compose.xml) / [输出](m2-final-compose.txt)：1 passed，146 deselected，0 failed，0 skipped，383.07 秒。Deselected 为职责分开后的排除项，已在容器中执行，不算 skip，也不重复计数。宿主耗时包含整个编排与 benchmark，不与容器时间相加。

Warnings：**2 种上游弃用警告**，两个最终 pytest 进程各出现 2 条，共 4 次：Starlette 对 httpx TestClient 的弃用提示；AnyIO BlockingPortal alias 弃用提示。未屏蔽警告，也未为消除提示擅自升级锁定依赖。

Ruff check / format --check、mypy（56 源码文件）、compileall、Schema snapshot --check 均通过。冻结 Contract 的类型检查边界沿用 M1.1，不宣称已对冻结文件做类型修整。

## Docker Runtime

**50/50 PASS**：完整保留原 37 项 M1.1 运行检查，并增加 13 项 M2 检查。实际执行 image build、Compose up、migration/roundtrip、bootstrap、Linux 全部测试、真实 HTTP raw ingest → correlation → incident、查询和状态转换；另执行数据库停机/恢复、API 重启、Compose down/up 卷持久化、M2 API/DB 重启和重复投递。

容器以非 root 运行，API 仅绑定 loopback，数据库不对宿主发布端口。存储故障与迁移/bootstrap 失败可被 readiness/响应观察到；Audit/Outbox 和 lineage 验证通过。所有测试容器/网络在结束后停止移除，命名卷 `zhiyu-smoke-89199b674d14_zhiyu_pg` 保留；该卷保留数据库数据，ZIP 不包含数据库凭据或运行中服务。

全部检查名、结果和脱敏命令日志见 [最终运行目录](m2-runtime/zhiyu-smoke-89199b674d14/result.json)。先前 M1.1、Gate A、首轮 M2 以及中断/失败尝试保留作为历史；`zhiyu-smoke-01f68ba367a0` 的 135 项测试及旧代码 benchmark 不是最终验收数据。

**REAL SENSOR RUNTIME = NOT_RUN**。**A01–A15 = NOT_RUN**。

## Golden Chain

**SYNTHETIC GOLDEN CHAIN**：1 条 Suricata HTTP 401 认证事实 + 2 条 Wazuh 自定义 application authentication failure + 1 条不同用户的无关 Wazuh 事件。固定 [fixture](../tests/fixtures/golden_chain_m2.json) 与本次 UTC 时间替换后的 [实际输入](m2-runtime/zhiyu-smoke-89199b674d14/golden-effective-inputs.json) 均保留；未声称实际运行传感器。

**4 Raw → 4 NormalizedEvent → 2 EventGroup → 2 CorrelationDecision → 1 SecurityIncident**。

相关组保留 3 条事件、2 个独立 provenance root，Incident 引用 3 条 Evidence；无关用户形成独立 1 条事件的组，被排除在 Incident 之外，其数据仍完整保存。风险 **62 / P2**：severity 24 + independent_sources 10 + asset_criticality 4 + repeated_behavior 4 + activity 10 + evidence_quality 10 + validation_context 0。

生命周期真实通过 NEW → TRIAGED → INVESTIGATING。API/数据库重启和重放后，仍为 2 Group / 2 Decision / 1 Incident / 3 Evidence，lineage 和对象快照一致。4 条重发变为 duplicate，唯一 raw/event 数仍是 4；因此累计 raw 投递指标为 8，duplicate 为 4，而不是 8 个不同源事件。

| Golden 环境持久化结果（含 bootstrap 与重放） | 数量 |
|---|---:|
| Audit CREATE | 5 |
| Audit INGEST / NORMALIZE | 8 / 4 |
| Audit EventGroupCreated / CorrelationDecisionCreated | 2 / 2 |
| Audit IncidentCreated / IncidentUpdated | 1 / 2 |
| Audit 合计 | 24 |
| Outbox EventIngested / EventGroupCreated / CorrelationDecisionCreated | 4 / 2 / 2 |
| Outbox IncidentCreated / IncidentUpdated | 1 / 2 |
| Outbox 合计 | 11 |

Audit hash chain、Evidence 所有权和完整 lineage 均有效。这里的 VERIFIED_ORIGIN 表示已鉴别采集身份、原始字节完整性与确切映射证明，不等于传感器数字签名或攻击成立证明。

## Performance Baseline

以下是最终 `0.2.0` 在上述共享开发环境中测得的 **SYNTHETIC 服务级基线**。包含真实 Linux 服务调用、PostgreSQL 事务和 Audit/Outbox，不含 HTTP 序列化开销。归一化单独测量；完整 pipeline 从 ingest 到 promotion 计时，已包括 ingest 内部的归一化，不能再加一次独立归一化耗时。

| Events | 独立归一化 events/s | Ingest events/s | Ingest 秒 | Correlation 总秒 | Promotion 总秒 | Pipeline 总秒 | Groups / Incidents | 压缩比 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 12,524.89 | 82.01 | 12.194 | 1.284 | 1.561 | 15.040 | 10 / 10 | 100:1 |
| 10,000 | 13,850.12 | 84.66 | 118.125 | 12.602 | 14.968 | 145.696 | 100 / 100 | 100:1 |

| Events | Correlation 持久化 run 样本 / mean / p95 ms | Promotion 样本 / mean / p95 ms |
|---:|---|---|
| 1,000 | 1 / 1261.47 / 1261.47 | 10 / 154.64 / 188.19 |
| 10,000 | 10 / 1237.45 / 1308.24 | 100 / 148.62 / 195.81 |

总秒数来自完整服务调用；持久化 latency 样本的计时边界较窄，不能直接等同。每 100 条事件属于一个合成 actor，两个来源；版本化配置 `ei-config/benchmark-1h` 将 auth window 显式设为 3600 秒，以容纳本次长批处理，其余配置写入 [benchmark.json](m2-runtime/zhiyu-smoke-89199b674d14/benchmark.json)。默认业务 auth window 仍为 300 秒。全部源事件、组成员和 Evidence 保留，错误/duplicate/pending 均为 0。

这里只建立初始基线，样本不是独立重复试验，p95 不是生产 SLA。Ingest 明显比纯归一化耗时，但未做足够 profiling 来归因到某个 SQL 或建议新基础设施。

## Problems Found

| 问题与根因 | 实际修复与验证 |
|---|---|
| 重放时 clock_status 随接收时间变化，被错误算作源内容冲突 | replay comparison 排除接收时派生属性，并从旧契约对象重新计算比较；旧 M1.1 数据升级重放和时钟变化测试通过 |
| ResourceRef 使用 `address`，endpoint 不能仅按 IP 绑定 | 按 ai.5 locator 读取，endpoint 必须匹配 address/port/protocol；歧义不绑定，边界测试通过 |
| 非法 Unicode / 映射后 NUL 可触发数据库级失败 | raw 使用 BYTEA，映射字符串校验后逐条拒绝；原始输入保留，合法邻居继续处理 |
| 关联 key 缺失 actor_resource / transport 时存在误合并可能 | 纳入确定性 key，负例断言覆盖身份与协议差异 |
| 单有 raw_ref 不能证明该 NormalizedEvent 来自这些原始字节 | 验证不可变 raw delivery 的确切映射证明；伪造引用不能获得 VERIFIED_ORIGIN，增加回归测试 |
| Evidence 引用必须属于同一 Incident | 新增同环境、同 Incident 的复合所有权 FK，非法跨 Incident 关联被数据库拒绝 |
| 策略变更可能改写旧 Incident 却保留旧策略元数据 | 新策略不静默改写原策略 Incident；按策略版本合并与 no-merge 测试通过 |
| 初次 Scope 负例使用契约不允许的空 targets | 修正测试输入，用合法的 Environment.scope_ids 变更触发真实 Scope 守卫；生产逻辑不因测试而放宽 |

最终未发现阻塞本阶段验收的未修复失败。明确限制仍包括：同一源的字节相同独立事件需采集游标才能区分；转发来源独立性依赖运营配置；排除候选仅最早 100 个同窗样本；处理需调用 API/服务驱动；每环境串行锁尚未提供水平扩展承诺。

## Architecture Findings

**No ai.5 architecture change required.**

未新增第二套 Event / Incident Contract，未更改冻结模型、JSON Schema 或状态机。风险、窗口版本和关系索引是内部存储元数据。旧基线 Golden StateRelation 引用 `lab-gateway` 却缺少对应 StateEntity 的既有 fixture 问题沿用之前的审查记录，未将其伪装成真实世界状态，也未借本轮修改 ai.5。

## Remaining

- Task / worker lease-fencing runtime、授权 Risk Gate、Action Gateway / Active Response、独立 Verification 与完整闭环尚未实现。
- AI / LLM / Planner / Model Gateway runtime 禁用；未引入 Kafka、Neo4j、Temporal 等新基础设施。
- Suricata/Wazuh 的真实运行采集、SCN-LAB-AUTH-01 实地闭环、A01–A15 平台验收：NOT_RUN。
- 更大规模、重复试验、HTTP 吞吐与 SQL profiling 尚未执行；两种上游弃用提示仍存在。

## Milestone

**v0.2.0 PASS**。

M1.1: PASS；M2.1: PASS；M2.2: PASS；M2.3: PASS；M2 deterministic event-to-incident path: PASS。阶段名称为 **M2 Event-to-Incident Phase PASS**。

最终 25 项 Gate 全部通过；主要测试证据如下，均包含在最终 147 项完整执行中：

| 最终 Gate | 结果 | 主要证据 |
|---|---|---|
| M1.1 无回归 | PASS | 原测试 + 原 37 项 runtime checks |
| Suricata Adapter | PASS | test_adapters / Golden Mapping |
| Wazuh Adapter | PASS | test_adapters / Golden Mapping |
| Golden Mapping | PASS | 12 组 raw/expected + 冻结契约校验 |
| malformed input isolation | PASS | test_raw_ingest / test_raw_edge_cases / HTTP bad-neighbor |
| provenance | PASS | independent/forwarded provenance + forged raw_ref negative |
| severity mapping | PASS | 双源版本化映射及未知值 fallback |
| timestamp | PASS | UTC/offset/naive/malformed/future/delayed |
| EventGroup | PASS | 关系成员、版本、唯一约束与持久化 |
| CorrelationDecision | PASS | 输入/排除关系、规则解释及版本 |
| positive correlation | PASS | test_event_intelligence + Docker Golden |
| negative correlation | PASS | identity/target/source/environment/window/transport |
| multi-source correlation | PASS | Suricata + Wazuh 同组、独立来源保留 |
| late event policy | PASS | out_of_order_window_close_late_expired_future |
| concurrent grouping | PASS | concurrent_workers_and_restart_no_duplicate_decisions |
| Incident promotion | PASS | promotion/no-promotion/environment profile policies |
| Incident merge policy | PASS | merge/update + closed/horizon/policy no-merge |
| Incident lifecycle | PASS | guards/CAS/retry + Docker 两次真实转换 |
| risk explanation | PASS | multifactor + Golden 风险贡献精确断言 |
| Evidence lineage | PASS | mapping attestation、ownership FK、HTTP lineage |
| Audit | PASS | hash chain、不可变约束、事务失败回滚 |
| Outbox | PASS | 同事务、故障回滚、并发与旧 worker 拒绝 |
| migration upgrade/downgrade/upgrade | PASS | Linux PostgreSQL roundtrip、M1 数据保留、无漂移 |
| Docker E2E | PASS | 50 个实际运行检查 |
| complete test suite | PASS | 147 passed / 0 failed / 0 skipped |

## Deliverables

完整工程 ZIP：`artifacts/智御_Project_v0.2.0_Deterministic_Event_Intelligence.zip`（位于工程目录的同级 artifacts 目录；解压根目录为 `zhiyu_v0.2.0/`）。

验证报告：本文件 `docs/VALIDATION_v0.2.0.md`。文件变更清单见 [FILES_CHANGED_v0.2.0.md](FILES_CHANGED_v0.2.0.md)。发布 ZIP 内含 `MANIFEST.sha256`，旁置 `SHA256SUMS_v0.2.0.txt` 与 `PACKAGE_VALIDATION_v0.2.0.json` 记录逐文件校验、ZIP 完整性和旧包保留核对。原始 M1.1 两个工程 ZIP 保留，不覆盖。

复现方式见 [README](../README.md)。交付不含缓存、构建产物、`.env`、本机虚拟环境或数据库凭据；所有性能和运行结果均有原始 JSON/JUnit/日志可追溯。
