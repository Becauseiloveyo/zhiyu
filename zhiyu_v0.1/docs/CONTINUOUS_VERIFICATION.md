# Continuous Verification & Re-plan — v0.4

`EXECUTION_SUCCESS != SECURITY_SUCCESS`。ActionResult 是执行回执；Verification
通过后续独立数据库读取、独立 HEAD /health、独立传感器与证据检查形成结论。
当前只实现 DETECTION：确认资源上下文及业务可用性，不声称攻击被遏制或已修复。

## 契约与持久化

复用 ai.5 VerificationSpec、VerificationCheckSpec、AssertionSpec、VerificationResult、
Evidence、ValidationScenario、ValidationRun、StateEntity、AIPlan。OBSERVATION 是冻结
契约中可观测维度的名称。运行绑定、租约、原始断言、效果解释、预算和计划沿袭使用内部表。
迁移为 `0008_verification → 0009_decisions → 0010_replan`，总计 30 契约表和 33 内部表。

同一 spec/check 只有一个逻辑检查和观测。租约使用 PostgreSQL 时间与 generation；进程
崩溃后可重领，旧代次没有执行权。只读探测在崩溃后可能实际重试，但逻辑结果唯一。
观测与 Evidence 同事务写入，哈希校验，禁止静默 UPDATE/DELETE。没有 arbitrary shell
执行接口。Migration downgrade 删除新增运行元数据，不是业务数据备份恢复方案。

## 检查与结论

- SECURITY：新查询 ResourceRef，断言 resource_id / binding_version。
- BUSINESS：新发起 HEAD /health，记录 HTTP status、可达性与 latency；500 可以是执行
  SUCCEEDED、断言 FAIL。无任意 URL、DNS、代理、重定向或命令；使用绑定来源及登记端口。
- OBSERVATION：传感器状态、心跳/事件时效、coverage、丢失事件/lag、输入 Evidence 时效。
  冻结 OFFLINE/UNKNOWN 映射为有效 UNAVAILABLE，过期映射为 STALE，不修改冻结枚举。

固定执行器、3 秒以内单次检查、最多 5 次采样、最多 3 次恢复尝试、最多 300 秒运行窗。
主动验证只在明确授权的 LAB / IT / CONTROLLED_AUTONOMY / ISOLATED_ONLY / R2 环境工作；
生产环境当前不执行主动验证。该限制不授予任何真实环境权限。

独立 HTTP 检查与 Action 共享 Scope 请求速率预算。尚未到达可用时间时保持待调度，Worker
后续 tick 继续；执行边界再次检查并预留配额。IDLE 只表示当前没有可领取的检查，不代表全部
检查完成，调用者应结合 checks 状态。性能夹具单独声明本地回环 Scope 的 100 RPS 上限。

缺失/冲突/过期证据、未完成窗口、采样不足、超时或不可观测会先使维度结论失去资格，
得到 INCONCLUSIVE，再进入冻结聚合规则。原始 FAIL 仍可在 Effectiveness.raw_dimensions
和 Check assertions 中查看。诊断 Evidence 记录“证据不足”的观测，不替代缺失探测。

## 状态与重规划

显式启用的计划按 `TRIAGED → INVESTIGATING → PLANNED → EXECUTING → VERIFYING`
推进。Gateway 在新授权 ALLOW 后提交 EXECUTING，Action 边界仍校验准确 state_version。
未启用的 v0.3 计划保持原行为。冻结状态机没有 DETECTION PASS 的修复/遏制边，因此
PASS 保留 VERIFYING，写入已验证效果与残余风险；不自动 CLOSED。

FAIL 可重新查询事件证据；INCONCLUSIVE 可重新收集资源上下文。新计划的新 Task 必须
再次通过原 Capability / Authorization / Risk Gate / Gateway。预算默认最多 2 次重规划、
12 个预留动作、600 秒、零风险升级。R1 超过初始/当前 ceiling 时 REQUIRE_APPROVAL，
不生成可执行的升级任务。次数、总动作或时间耗尽，或出现重复计划/无新语义证据，停止并
进入 HUMAN_REVIEW。原 Plan、Action、Verification 和新的 parent/trigger lineage 均保留。

StateEntity 的 OBSERVATION 保存实际样本、来源、时间、质量和证据；INFERENCE 单独
保存效果判断。每个验证结果生成不可变状态快照，不由 Planner 虚构或覆盖观测事实。

## API 与 Worker

继续使用受保护的 `ZHIYU_SERVICE_TOKENS`。新增权限为 `verification:write/read/execute/replan`。
计划还需要 `response:plan`、生命周期需要 `incidents:write`；HTTP 检查需要原
`response:execute`、`capability:safe_http_probe` 和有效响应控制配置。

| API | 用途 |
|---|---|
| POST /v1/continuous-plans | incident_id / expected_version / scope_id / budget，创建并启用验证周期 |
| POST /v1/verifications | environment_id / action_result_id / frozen spec / runtime policy |
| POST /v1/verifications/{spec_id}/tick | 原子领取并执行一个独立检查 |
| POST /v1/verifications/{spec_id}/decide | 持久化三维判决与效果解释；重放返回原结果 |
| POST /v1/verification-results/{verification_id}/apply | 状态更新与有界重规划；同 trigger 幂等 |
| GET /v1/verifications/{spec_or_result_id} | 契约、绑定、结果、效果、状态、重规划 |
| GET /v1/verifications/{spec_id}/checks | definition / observation / assertions / Evidence ID；after/limit 分页 |
| GET /v1/incidents/{incident_id}/verifications | environment_id / cursor / limit，判决时间分页 |
| GET /v1/incidents/{incident_id}/timeline | 按计划时间分页，返回 Tasks、Actions、Results、Specs 沿袭 |
| GET /v1/verification-metrics | 环境隔离的验证/检查/重规划计数、时延和证据数 |

独立 Worker 使用已配置的 principal_id，不接收调用者自造授权：

```bash
python -m zhiyu.verification.worker --environment <registered-lab> --principal <configured-id> --poll
```

数据库不可用时进程退出，由外部进程管理器重启；数据库租约与逻辑结果仍保留。
默认无 `--poll` 只执行一个 tick。Operator 必须登记实际可信 sensor health；测试 helper
`tools/verification_fixture.py` 仅允许新建、明确标记的 SYNTHETIC 环境，不能证明真实传感器运行。

## 验证范围

验收入口：`tools/compose_smoke.py`，开启 `ZHIYU_RUN_COMPOSE=1` 与 `ZHIYU_BENCHMARK=1`
运行完整 Docker 检查及 100/1,000 组独立验证基线。每组包含三个独立检查，基线使用本地真实
HTTP 服务与 PostgreSQL，顺序调度；服务阶段时延不含所有外层 HTTP/事务提交开销。
每组最后一个验证故意安全断言失败，单独实测实际重规划创建时延，其余测量无重规划判定。
这些数据不构成生产吞吐或 SLA。失败运行日志保留，最终结论以 Validation Report 为准。

AI / LLM / Model Gateway、真实 Sensor Runtime、A01–A15、生产负载/SLA 仍未完成。
