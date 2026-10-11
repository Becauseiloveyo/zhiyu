# RC7 Remediation Final Update

当前 v0.6.0 PASS / CONTROLLED LAB。[remediation-task-benchmark.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/remediation-task-benchmark.json) 和 [sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json) 分别覆盖默认队列与显式预留容量。

| 执行任务 | 逻辑 Action | 秒 | 未执行尾部任务 |
|---|---|---|---|
| 100 | 100 | 17.010 | 2 |
| 1000 | 1000 | 173.741 | 2 |

[调度影响评估](m6-runtime/gate-e-scheduler-impact-review.json)。下方大负载与 soak 是旧源码的历史结果。

---

以下是 RC3 及更早的历史报告，原封存内容保留，当前结论以上方及最终报告为准。

# v0.6.0 Performance / Resource Baseline

**Gate D：PASS_CONTROLLED_LAB。本机受控 Lab 的合成负载实测，不是生产 SLA 或长期稳定性证明。**

所有原始数据位于 [gate-d-001](m6-runtime/gate-d-001/result.json)。真实传感器链已在 Gate A 单独验收，本性能实验中的事件与健康夹具仍标为 SYNTHETIC。使用真实 PostgreSQL、只读执行器、独立 HTTP HEAD 和本地模型；没有外部目标扫描。

数据库复用 B/C 专用 Lab，保留已有数据；各负载创建独立实验环境。soak 在 9 月 18 日完成，其后分级负载跨日继续，各阶段实际起止时间在原始 JSON 中；中间空闲时间不计入 soak。源码只读挂载在已验证依赖镜像中，最终烘焙镜像验收属于 Gate E。

## 事件负载

Adapter 归一化另作一次独立计时；ingest 自身也包含归一化、数据库和事务开销，两者不可相加冒充独立流水线阶段。分组/关联合并计时；下表累计耗时排除准备工作、最终指标读取与明确记录的暂停。批次 p50/p95/p99 的单位是每 1000 条事件批次，不是单事件延迟。

| 请求条数 | 实际条数 | 状态 | ingest s | group/correlate s | promotion s | pipeline s |
|---:|---:|---|---:|---:|---:|---:|
| 1000 | 1000 | COMPLETED | 15.65 | 1.28 | 2.03 | 18.97 |
| 10000 | 10000 | COMPLETED | 132.64 | 15.61 | 22.50 | 170.79 |
| 100000 | 100000 | COMPLETED | 1025.66 | 132.31 | 363.63 | 1522.68 |

100k 首段采用 1200 秒预算，在完整批次边界结束，66,000 条记录保留为 PARTIAL_TIME_BUDGET。暂停后用原时间戳继续，输入已跨过固定窗口及迟到宽限，正确变成大量 LATE 单事件隔离，测量中止并保留；其 73,000 条已提交事件和审计经复核完整，pending 已清零。这些慢样本不冒充正常分组吞吐。新的 [events-streaming.json](m6-runtime/gate-d-001/events-streaming.json) 在独立环境以每批实际生成时间完整重测 100k，保持相同关联/迟到策略；上表只在其完成后采用新结果。原始首段、续跑和迟到诊断分别保留在 events.json、events-completed.json 与 late-continuation-review.json。

## 只读响应与独立验证负载

响应每批最多 300 个任务，验证每批最多 100 组三维检查，使用新 Incident/Scope 控制夹具有效期。该分区方法不能外推为同一租户或 Incident 的容量。验证的 100/1000/10000 表示 individual checks；每组含三项，因此实际数量向上取三的倍数。每批末次检查故意让安全断言 FAIL，检验独立判定和一次诊断 replan；不能把预期的安全断言 FAIL 算作执行故障。

| 类别 | 请求 | 实际 | 状态 | 累计秒 | 有意保留的后续任务 |
|---|---:|---:|---|---:|---:|
| response | 100 | 100 | COMPLETED | 18.93 | 2 |
| response | 1000 | 1000 | COMPLETED | 182.50 | 2 |
| response | 10000 | 10000 | COMPLETED | 1595.82 | 2 |
| verification | 100 | 102 | COMPLETED | 8.78 | 1 |
| verification | 1000 | 1002 | COMPLETED | 70.24 | 4 |
| verification | 10000 | 10002 | COMPLETED | 705.66 | 34 |

原始样本覆盖 Scheduler lease、Authorization、Risk Gate、Action Gateway/Executor，以及 verification scheduling/execution/decision/Evidence/State update。汇总同时给 p50/p95/p99，样本数较小时尾分位只能视为观察值。排队未执行的尾部任务与诊断后续任务如实列出；不声称已经排空所有业务队列。

最大已测档的阶段延迟（ms；事件为 1000 条批次，任务/检查为各次阶段操作）：

| 负载 | 阶段 | 样本 | p50 | p95 | p99 |
|---|---|---:|---:|---:|---:|
| events-100k | ingest_ms | 100 | 10213.52 | 10774.88 | 11137.23 |
| events-100k | group_correlate_ms | 100 | 1322.04 | 1609.77 | 1668.62 |
| events-100k | promotion_ms | 100 | 3681.33 | 6428.85 | 6754.79 |
| response-10k | plan_generation | 3334 | 8.93 | 12.00 | 13.76 |
| response-10k | task_graph_creation | 3334 | 18.19 | 23.63 | 26.32 |
| response-10k | authorization | 10000 | 12.06 | 15.92 | 17.79 |
| response-10k | policy_gate | 10000 | 0.03 | 0.06 | 0.09 |
| response-10k | scheduler_lease | 10000 | 16.89 | 22.27 | 25.12 |
| response-10k | gateway_overhead | 10000 | 78.00 | 94.86 | 106.83 |
| response-10k | safe_executor | 10000 | 1.59 | 2.47 | 3.55 |
| verification-10k | spec_generation | 3334 | 9.58 | 11.32 | 17.82 |
| verification-10k | check_scheduling | 10002 | 16.37 | 19.54 | 24.54 |
| verification-10k | security_check | 3334 | 6.83 | 8.37 | 9.21 |
| verification-10k | business_check | 3334 | 11.01 | 12.93 | 14.10 |
| verification-10k | observation_check | 3334 | 9.39 | 11.02 | 12.02 |
| verification-10k | decision | 3334 | 13.59 | 15.56 | 17.19 |
| verification-10k | state_update | 3334 | 6.90 | 8.38 | 9.13 |
| verification-10k | replan_evaluation | 3334 | 24.72 | 28.18 | 45.86 |
| verification-10k | replan_creation | 34 | 49.88 | 53.68 | 53.97 |

## AI 小负载

保持单模型 slot、6 线程、1200 输出 tokens、110 秒客户端超时，测 10 次顺序与 2/4 请求同步小并发，不提高并行 slot。provider_ms 包含传输、排队和推理，Gateway overhead、Context build 单独计量。当前接口未单独暴露逐请求排队时长，故标为 NOT_SEPARATELY_MEASURED；以同时到达/完成时间、超时与服务器 slot 日志反映排队行为。

| 模式 | 请求 | 可计量响应 | 结果 | p50/p95/p99 总分析 ms |
|---|---:|---:|---|---|
| sequential | 10 | 10 | {"REFERENCE_GROUNDED": 8, "REJECTED": 2} | 38946.27, 46424.83, 46424.83 |
| concurrent2 | 2 | 2 | {"REFERENCE_GROUNDED": 2} | 58267.04, 77416.08, 77416.08 |
| concurrent4 | 4 | 2 | {"REFERENCE_GROUNDED": 2, "FALLBACK": 2} | 94484.32, 110283.38, 110283.38 |

| 模式 | 已计量 input / output tokens | 传输/排队/推理 p50 / p95 / p99 ms | Gateway overhead p50 / p95 / p99 ms |
|---|---|---|---|
| sequential | 30835 / 7124 | 38888.44 / 46298.38 / 46298.38 | 32.42 / 77.58 / 77.58 |
| concurrent2 | 6144 / 1425 | 58195.69 / 77341.27 / 77341.27 | 42.85 / 48.84 / 48.84 |
| concurrent4 | 6179 / 1465 | 94355.68 / 110102.35 / 110102.35 | 75.48 / 103.68 / 103.68 |

超时而未返回 usage 的请求不能据零计量推断零服务器计算；服务端原日志保留排队、处理与取消记录。

预算耗尽必须在第二次 Gateway 请求处阻止 provider 调用；不把拒绝计作一次模型推理。SHADOW 始终无 AI Executor 调用。实际 token、失败码、模型输出与数据库快照保留，不发布语义准确率。

## 30 分钟 soak

状态 COMPLETED，实际 1800.000 秒，完成 30 轮；每轮四条新事件及四次重放、三个只读任务、三项独立检查。每十轮一次真实模型分析。

最终数据库/队列指标：`{"database_size_bytes": 83769011, "connections": 3, "database_activity": {"active": 1, "idle": 2}, "tasks_states": {"SUCCEEDED": 90}, "verification_checks_states": {"SUCCEEDED": 90}, "model_requests_states": {"COMPLETED": 3}, "pending_outbox": 1992, "active_task_leases": 0, "expired_running_tasks": 0, "python_rss_status": ["VmHWM:\t   92468 kB", "VmRSS:\t   92468 kB", "VmSwap:\t       0 kB"], "observed_at": "2026-09-18T10:56:51.609472+00:00"}`

未配置 Outbox 消费者，待发布消息增长是明确的持久化积压，不冒充已投递或零队列。业务任务与验证检查的状态另行记录。10 秒 pilot 因未装载模型凭证发生 CREDENTIAL_UNAVAILABLE；修正入口后正式 soak 重新使用独立身份，失败预检仍保留。

## 资源观测

| 阶段 | 样本 | 模型 cgroup 最大观测 bytes | 模型 RSS 最大观测 bytes | swap 最大观测 bytes | OOM / restart counts |
|---|---:|---:|---:|---:|---|
| ai | 34 | 2442100736 | 2440302592 | 0 | False / [0] |
| events-finish | 48 | 2442256384 | 2439888896 | 0 | False / [0] |
| events | 80 | 2442407936 | 2439888896 | 0 | False / [0] |
| events-streaming | 87 | 2447564800 | 2439888896 | 0 | False / [0] |
| late-review | 1 | 2441297920 | 2439888896 | 0 | False / [0] |
| pilot | 1 | 2447642624 | 2445168640 | 0 | False / [0] |
| response | 94 | 2442813440 | 2439888896 | 0 | False / [0] |
| soak | 105 | 2450894848 | 2447990784 | 0 | False / [0] |
| verification | 45 | 2442141696 | 2439888896 | 0 | False / [0] |

资源采样与实际负载的覆盖缺口（秒；正常采样周期也会留下边缘间隔）：

- ai：开始前未覆盖 0.00，结束前未覆盖 1.59。
- events：开始前未覆盖 0.00，结束前未覆盖 13.47。
- events-streaming：开始前未覆盖 0.00，结束前未覆盖 10.93。
- pilot：开始前未覆盖 0.00，结束前未覆盖 13.58。
- response：开始前未覆盖 0.00，结束前未覆盖 153.81。
- soak：开始前未覆盖 0.00，结束前未覆盖 3.88。
- verification：开始前未覆盖 0.00，结束前未覆盖 9.53。

[resource-review.json](m6-runtime/gate-d-001/resource-review.json) 保留各容器 CPU 峰值、Docker 内存首尾、采样范围与采集错误数；原 JSONL 保留全部实际读数。Docker stats 内存与 cgroup/RSS 口径不同，不能混用。短期观测未增长不等于证明没有内存泄漏；没有数据的时段不作稳定性结论。

| 阶段 | 容器 | CPU 最大观测 % | Docker 内存首值 | Docker 内存末值 |
|---|---|---:|---|---|
| ai | api | 49.26 | 93.58MiB / 13.55GiB | 149.9MiB / 13.55GiB |
| ai | postgres | 16.52 | 2.075GiB / 13.55GiB | 2.075GiB / 13.55GiB |
| ai | local-model | 602.58 | 1.237GiB / 4GiB | 1.237GiB / 4GiB |
| events-finish | api | 102.89 | 117.3MiB / 13.55GiB | 211.5MiB / 13.55GiB |
| events-finish | postgres | 115.76 | 718.8MiB / 13.55GiB | 1020MiB / 13.55GiB |
| events-finish | local-model | 0.01 | 1.237GiB / 4GiB | 1.237GiB / 4GiB |
| events | api | 109.11 | 98.11MiB / 13.55GiB | 217.3MiB / 13.55GiB |
| events | postgres | 150.99 | 95.18MiB / 13.55GiB | 709.6MiB / 13.55GiB |
| events | local-model | 4.49 | 1.237GiB / 4GiB | 1.238GiB / 4GiB |
| events-streaming | api | 103.30 | 128.2MiB / 13.55GiB | 210.3MiB / 13.55GiB |
| events-streaming | postgres | 140.72 | 1.052GiB / 13.55GiB | 1.739GiB / 13.55GiB |
| events-streaming | local-model | 3.23 | 1.237GiB / 4GiB | 1.237GiB / 4GiB |
| late-review | api | 48.58 | 98.85MiB / 13.55GiB | 98.85MiB / 13.55GiB |
| late-review | postgres | 0.01 | 1014MiB / 13.55GiB | 1014MiB / 13.55GiB |
| late-review | local-model | 0.00 | 1.237GiB / 4GiB | 1.237GiB / 4GiB |
| pilot | api | 52.39 | 97.08MiB / 13.55GiB | 97.08MiB / 13.55GiB |
| pilot | postgres | 0.00 | 85.1MiB / 13.55GiB | 85.1MiB / 13.55GiB |
| pilot | local-model | 0.01 | 1.242GiB / 4GiB | 1.242GiB / 4GiB |
| response | api | 92.95 | 118.9MiB / 13.55GiB | 152.2MiB / 13.55GiB |
| response | postgres | 66.77 | 1.741GiB / 13.55GiB | 1.943GiB / 13.55GiB |
| response | local-model | 3.26 | 1.237GiB / 4GiB | 1.237GiB / 4GiB |
| soak | api | 50.98 | 119.9MiB / 13.55GiB | 141.2MiB / 13.55GiB |
| soak | postgres | 28.34 | 85.83MiB / 13.55GiB | 114.9MiB / 13.55GiB |
| soak | local-model | 601.47 | 1.242GiB / 4GiB | 1.237GiB / 4GiB |
| verification | api | 90.24 | 90.98MiB / 13.55GiB | 156.8MiB / 13.55GiB |
| verification | postgres | 74.84 | 1.961GiB / 13.55GiB | 2.094GiB / 13.55GiB |
| verification | local-model | 3.17 | 1.237GiB / 4GiB | 1.237GiB / 4GiB |

各阶段数据库体积与连接数（包含先前 Lab 数据，连接数为边界采样，不是持续峰值）：

| 阶段 | 初始 bytes | 最终 bytes | 初始连接 | 最终连接 |
|---|---:|---:|---:|---:|
| events | 83769011 | 857945779 | 2 | 2 |
| events-streaming | 1591662259 | 2596558515 | 2 | 2 |
| response | 2596558515 | 3118823091 | 2 | 3 |
| verification | 3118823091 | 3341547187 | 2 | 3 |

## 瓶颈与剩余

阶段耗时用于定位 ingest 的 ORM/事务开销、分组/关联和 promotion 的相对占比；它们尚不能单独证明某条 SQL 是根因。单 slot 的模型服务会串行处理请求，较长队列可能触发客户端超时并安全回退。未引入新的消息中间件或调度架构。最终 Gate D 结论必须结合完整负载结果、Audit/幂等/安全检查与数据库快照；总版本仍以 VALIDATION_REPORT_v0.6.0.md 为准。

最终 [队列复核](m6-runtime/gate-d-001/load-queue-review.json)：128 个已记录实验环境，运行中任务 0，未分组事件 0，有意保留的后续任务 45，未发布 Outbox 398200。所有积压均保留并明确计数，没有为了得到零队列而清除数据。
