# RC7 Remediation Final Update

当前 v0.6.0 PASS / CONTROLLED LAB。[sensors/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/result.json)；[sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json)。新鲜双源覆盖 /attack 与 /health，原始证明和五项修复均在最终 RC 重跑；CONTAINMENT 与 DETECTION 明确分开。

---

以下是 RC3 及更早的历史报告，原封存内容保留，当前结论以上方及最终报告为准。

# Real Sensor Runtime — Gate A

结论：**REAL SENSOR RUNTIME = PASS / CONTROLLED LAB**。整体版本仍为 **v0.6.0 NOT PASS / IN_PROGRESS**，后续 Gate 尚未全部完成。

验收入口：[gate-a-acceptance.json](m6-runtime/gate-a-acceptance.json)；14 个不同断言，214 个证据文件 SHA256。重核命令：`python tools/m6_finalize_gate_a.py`。历史失败见 [M6_RUNTIME_FINDINGS.md](M6_RUNTIME_FINDINGS.md)，保留原目录，不计入成功数量。

## 环境与真实来源

Docker Desktop / Linux WSL2，隔离内部网络 `10.89.60.0/24`。Lab Client 为 `.20`，Target 为 `.10`，独立验证源为 `.30`。传感器/管理器/目标均无宿主端口映射，无宿主日志或 Docker socket 挂载。Wazuh 只监控本次应用实际写出的认证日志。

| 组件 | 实际观测 |
|---|---|
| Suricata | 7.0.10 RELEASE，真实进程，EVE 文件、配置、包版本、容器镜像 ID 均保留 |
| Wazuh Manager | v4.14.7，二进制自报 revision `rc1`；固定官方 digest 的最小 Lab 派生镜像 |
| Wazuh Agent | Linux Agent 001，真实注册并 Active；原始注册输出保留 |
| PostgreSQL | 17.11，72 张表，隔离 control 网络；Lab 专用 trust 认证，不作为生产配置 |
| Python | Linux 3.12.14；验证 runner 执行本工作区实际源码 |
| Windows Wazuh | NOT_RUN |
| Production / Cloud / OT | NOT_RUN |

精确镜像摘要、容器 ID、启动时间、hostname、端口状态在每次 capture 的 `manifest.json`。Suricata 共享 Target 网络命名空间，其 hostname 不能当作自己的容器 ID。当前成功采集在同时重建 target/Suricata 后执行；不得把旧目录文件重新归属到后来新建的传感器。

## SCN-LAB-AUTH-REAL-01

每轮只执行 4 次错误认证、1 次正确认证、1 次 DNS 查询、1 次 TLS 握手。账户为公开一次性 Lab 数据。Target 实际返回 401/200、写入 JSON 日志；Suricata 从网络抓包产生 EVE；Linux Agent 将应用日志交给 Wazuh Manager，规则 110001/110002 产生告警。网络规则 SID 9900001 仅告警，不阻断。

| 成功采集 | flow | dns | http | tls | alert | Wazuh alert | NormalizedEvent | Incident |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sensor-007 | 6 | 4 | 10 | 2 | 10 | 5 | 37 | 2 |
| sensor-008 | 0 | 2 | 5 | 1 | 5 | 5 | 18 | 1 |

007 包含同一实际容器早先一轮流量；008 在采集截止时 flow 尚未发出，不虚填数量。全部五种网络事件的真实 Adapter 入库由 007 证明，008 用 request_id 精确对照本轮请求。两次均出现真实 Suricata/Wazuh 双来源认证 EventGroup 和 Incident。

008 完整链保存 18 RawRecord、18 NormalizedEvent、8 EventGroup、8 CorrelationDecision、1 Incident、8 Evidence。Incident 为 `inc-b0d36872df420249c2a3d90438f4b874240e1efc22ff5936eb9aed806ae98008`。行级对象、分组解释、原始记录引用和 SQL 读回数据均在 [sensor-008/result.json](m6-runtime/sensor-008/result.json)。

## 血缘与身份语义

逐条将数据库 RawRecord 内容及 SHA256 对回原始文件行，同时核对 sensor 容器 ID/provenance root、collector、origin_event_id、raw_ref、实际 source timestamp、ingest timestamp、parser 与 mapping version。来源标记 OBSERVED，无改写原始时间戳或合成传感器输出。

本次唯一产品接线修复是 Suricata Adapter 的显式 Basic 请求头观测用户名映射。用户名是观测到的声明，不代表认证/授权；密码和完整请求头不进入归一化输出，异常不回显凭证。仅该分支版本升级，旧输入映射保持兼容，精确关联键与 ai.5 不变。原始 EVE 中公开 Lab 凭证为血缘证据；不要将该请求头日志配置用于真实客户凭证。

## 健康、故障与恢复

[gate-a-002/result.json](m6-runtime/gate-a-002/result.json) 记录 2026-09-17 13:18:37–13:23:26 UTC 的完整物理实验：

| 实验 | 预期与实际 |
|---|---|
| Suricata stop / start | INCONCLUSIVE → 新流量覆盖后 PASS |
| Wazuh Manager stop / start | INCONCLUSIVE → 新告警到达后 PASS |
| Linux Agent stop / start | INCONCLUSIVE → logcollector 就绪、新告警到达后 PASS |
| Collector 不更新，真实等待 131 秒 | INCONCLUSIVE |
| Agent pause，发送本轮请求 | INCONCLUSIVE，缺失本轮事件可见 |
| Agent unpause，实际补传 | 收齐本轮 request_id 后 PASS |
| PostgreSQL restart | 72 张表有序行哈希与数量完全一致 |
| 原始 008 replay | 全部 DUPLICATE，0 新接收/错误/待分组事件，10 类逻辑表不变 |
| Audit / 高风险自动执行 | 全环境链有效；高风险自动执行 0 |

健康来自真实进程/暂停状态、心跳、当前事件、request_id 覆盖、丢包/解码统计。Running 或心跳单独不足以判健康；过期记录不能被当前采集时间重新变新。恢复结论是上述时间窗口观测，不代表现在或持续健康。

## 只读响应与验证

3 个既有只读 Action 经过 Planner、Scheduler、Authorization、Risk Gate、Action Gateway，均 EXECUTION_SUCCESS、side_effect NONE。独立 Verification 执行数据库状态检查、实际 HTTP HEAD 与观测健康检查，DETECTION 结论 PASS。

该结论只确认只读上下文与业务可达性，**不证明隔离、修复、攻击阻断或恶意意图**。Incident 未被自动宣称 FIXED/CLOSED，模型未参与此链。详情：[initial verification](m6-runtime/sensor-008-health-initial/verification.json)。

## 回归与限制

新增解析/身份/健康单测已有独立 JUnit；完整回归结果另存 `sensor-preflight/full-regression.xml`。最终 v0.6 Docker 全量回归在 Gate E 收口，本报告不拿 v0.5 的 190 项冒充本轮结果。

没有 ai.5 架构变更；未新增核心能力，未执行 R3/R4，未测试 Windows/生产环境。所有失败原始输出保留；其中早期活跃 JSONL 尾部解析失败没有保留当时完整坏尾部，已明确证据限制。

## Gate E 最终复验

RC3 全新随机 sensor project，runner 使用最终源码烘焙 tests image。[sensors/result.json](m6-runtime/gate-e-final/zhiyu-smoke-7883dbeef67f/sensors/result.json)；[sensors/sensor-faults/result.json](m6-runtime/gate-e-final/zhiyu-smoke-7883dbeef67f/sensors/sensor-faults/result.json)。真实双源、原始 lineage、stop/recovery、131 秒 stale、补传、PostgreSQL restart/replay 通过。仍仅 CONTROLLED LAB / DETECTION。整体 v0.6.0 NOT PASS，原因见 [最终 Matrix](A01_A15_ACCEPTANCE_MATRIX.md)。
