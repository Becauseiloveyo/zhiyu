# Deterministic Response Control — v0.3.0

本阶段提供确定性计划、PostgreSQL 任务调度、执行授权与受控只读执行。ai.5 保持冻结；计划复用 AIPlan，`total_model_calls=0`、`model_run_id=null`。执行器只返回动作结果，不创建 VerificationResult，也不关闭 Incident。

## 启动与身份

按 README 配置受保护的 `ZHIYU_DATABASE_URL` 和 `ZHIYU_SERVICE_TOKENS`，完成 `python -m alembic upgrade head`。普通 Bootstrap 仍只注册 OBSERVE_ONLY / active_validation=DISABLED 环境。响应启用必须使用已由运维管理的 Environment、ResourceRef、Scope 和策略版本。

服务凭据的权限分别为 `response:read`、`response:plan`、`response:execute`、`response:admin`。执行还要求对应 `capability:<id>` 权限。每个 Worker 使用独立 principal_id；网络执行时 ResponsePolicy.worker_sources 将其绑定到真实本机源 ResourceRef。凭据不能只因知道 task_id 获得其他环境的权限。

本地操作员可以安装固定能力目录：

```text
python -m zhiyu.response.admin --environment <environment-id> --principal <configured-operator-id> --install-catalog
python -m zhiyu.response.admin --environment <environment-id> --principal <configured-operator-id> --file <control-request.json>
python -m zhiyu.response.admin --environment <environment-id> --principal <configured-operator-id> --refresh-health
```

`ControlRequest` 为严格 JSON：environment_id、expected_version（首次为 0）、policy_version（必须匹配 Environment）、enabled、configuration（ResponsePolicy）、valid_from、valid_until。时间必须为带时区 ISO 格式，配置窗口不超过一天。`configure` 使用版本 CAS；更新不会扩大 Environment / Scope 权限。Capability health 测量只证明本地结构化适配器和数据库可用，不证明目标可达。传感器状态必须来自可信运维接入；本版本未实现真实传感器运行服务，默认缺失/过期均拒绝。

```text
python -m zhiyu.response.worker --environment <environment-id> --principal <configured-worker-id>
python -m zhiyu.response.worker --environment <environment-id> --principal <configured-worker-id> --poll
```

默认只跑一个 tick，`--poll` 持续轮询。进程退出后的任务由租约到期和下一 Worker 恢复；持久化状态保存在 PostgreSQL。遇到数据库或配置错误，进程失败退出，交由本机进程管理器重启。配置中未声明的 principal_id 不能用于 CLI。

## 能力与安全边界

| Capability | 分类/风险 | 参数 | 实际执行 |
|---|---|---|---|
| collect_resource_context | PASSIVE_READ / R0 | limit: 1–100 | 查询已登记目标信息 |
| query_event_history | PASSIVE_READ / R1 | limit: 1–100 | 查询当前环境目标事件 |
| query_incident_evidence | PASSIVE_READ / R1 | limit: 1–100 | 查询该 Incident 已授权 Evidence |
| check_service_reachability | ACTIVE_CHECK / R2 | protocol: http/https; timeout_ms: 100–3000 | 向登记端口建立 TCP 连接 |
| safe_http_probe | ACTIVE_CHECK / R2 | protocol: http/https; timeout_ms: 100–3000 | 固定 HEAD /health |

所有参数禁止额外字段；没有 command、URL、header、shell、SSH 或任意脚本入口。TCP/HTTP 目标和端口取自已登记 ResourceRef，源地址由 Worker 绑定。numeric IP only；不做 DNS、不使用代理、不跟随重定向，限制响应头长度和时间，HTTPS 使用系统信任链与主机/IP 校验。其结果不代表业务/安全验证成功。HTTP/TCP 虽为只读，但按 ai.5 ACTIVE_CHECK/R2 管理，OBSERVE_ONLY 不可执行。

R0/R1 仍须符合当前 max_auto_risk、Scope、能力权限、证据/传感器健康和预算。R2 仅在允许主动检查的 LAB 且策略允许时自动执行；非 LAB 默认要求审批。R3–R5 和 STATE_CHANGE 本版本不执行。需要审批的 Task 停在 WAITING_APPROVAL；没有审批后高风险执行流程。

## API

| Endpoint | 权限/语义 |
|---|---|
| POST /v1/incidents/{id}/plans | response:plan；environment_id、expected_version、scope_id、include_http_probe |
| GET /v1/plans/{id} | response:read；原始计划与输入/解释 |
| GET /v1/tasks?environment_id=… | response:read；limit/cursor/status；稳定时间+ID分页 |
| GET /v1/tasks/{id} | response:read；当前状态、代次、ready_at、失败和回执 |
| GET /v1/capabilities?environment_id=… | response:read；limit/cursor；稳定 ID+version 分页、当前健康和历史时间 |
| GET /v1/actions/{id} | response:read；请求/digest/授权快照/决策/执行回执 |
| POST /v1/response/claim | response:execute；environment_id；返回有效 WorkerLease |
| POST /v1/tasks/{id}/lease/renew | response:execute；environment_id、generation |
| POST /v1/tasks/{id}/authorizations | response:execute + capability 权限；当前代次生成授权 |
| POST /v1/tasks/{id}/execute | response:execute + capability 权限；environment_id、generation、authorization_id、action_digest |
| POST /v1/response/worker/tick | response:execute；完整单次调度与执行 |

未授权环境的详情返回 404，集合/写入权限不足返回 403；结构/引用错误 422，过期代次和版本冲突 409。此阶段不支持任意创建 ActionRequest，只能从已计划 Task 创建。

## 恢复与事务

PlanCreated/TaskCreated 与计划和图在同一事务；授权快照/决策先于执行持久化。Gateway 再检查当前 lease、principal、digest、Scope/资源版本、能力、策略、预算、证据与健康，再保存 dispatch。调用执行器前再次检查授权，环境锁覆盖有界只读调用。最后回执、Task 状态、Audit、Outbox 原子提交。

默认 lease 20 秒、最多 3 次 attempt、1/2/4 秒退避（配置可缩小在模型边界内）。renew 不延长最初 attempt 的总截止时间。能力并发上限按环境/版本执行；探测按 Scope 请求速率预留。数据库使用环境行锁，吞吐具有保守串行化特征。

完成的重放返回 DUPLICATE 及原回执，不再调用执行器。相同 logical Action 保留固定 idempotency_key / digest。Worker 在调用后、回执提交前中断会留下 EXECUTION_UNKNOWN 历史；只有内置只读 READ_ONLY_REPLAY 允许下一 generation 重读。旧 generation 永远不能 ACK。未来有副作用的能力需要设备级去重、协调和验证，本版本禁止其分发。

## 验证与限制

Gate A/B/C 证据见对应报告，Docker 验收见 M3_GATE_D / VALIDATION_REPORT_v0.3.0。`tools/compose_smoke.py --benchmark` 使用全新随机 Compose project 和独立 volume，结束删除容器、保留测试 volume，不删除已有项目数据。`response-target` 仅在 response-test profile 启动，不发布宿主端口。

`tools/response_fixture.py`、`response_negatives.py`、`response_benchmark.py` 明确只供 SYNTHETIC acceptance；拒绝在非 m3-* / 非测试 owner 环境写入健康断言。R3 runtime 负例对新验收数据库短暂故障注入风险元数据，并恢复原值；其目的为验证拒绝，未注册任何高风险执行器。

性能报告分离 100/1,000 次真实只读任务的各阶段耗时。每组一个新 Incident，34/334 个合成策略版本分别生成 102/1,002 个 Task，最后两个 Task 未执行；不是 100/1,000 个真实 Incident，也不是生产 SLA。真实网络探测耗时单列 Golden Chain。

Verification、Re-plan、AI、Real Sensor Runtime、A01–A15 均未实现/未运行。数据库管理员仍属于可信管理边界；Audit 哈希链未接外部签名或异地锚定。
