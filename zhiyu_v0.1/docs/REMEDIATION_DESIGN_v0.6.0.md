# v0.6.0 Remediation Cycle — implementation boundary

正式结论仍为 **NOT PASS**。RC4 只修复项目自身版本；以下实现尚待最终 RC 的完整 Gate E。旧 RC3 的 PASS 子项不是当前源码的最终证据。

## 契约与风险

ai.5 `ActionRequest`、`ActionAttempt`、`CapabilityManifest` 和 `VerificationSpec` 已能表达所有权、代次、TTL、核对、补偿和 CONTAINMENT。冻结契约和历史迁移均不修改。新增 0016 只允许内部执行回执标记 `LAB_PATH`；仍为 71 张业务/内部表。

新增能力 `lab_http_containment` 属于 R2 的很小范围可恢复动作：仅控制独立、可丢弃 Lab HTTP 服务的固定 `/attack` 路径，TTL 为 5–60 秒；`/health` 不随遏制改变。它不是主机或网络防火墙。无 shell、目标 URL、任意路径、凭证更改、生产接入或攻击功能。默认目录安装、autonomy、AI 权限和部署均不自动启用它。

必须同时满足：显式 Registry 安装、LAB/IT/ISOLATED_ONLY/CONTROLLED_AUTONOMY、当前 Scope 网络约束、能力权限、R2 风险策略、健康与证据、受保护的目标地址/端口/控制令牌绑定，以及现有 Gateway 的授权快照和 Worker lease/fencing。

## 执行与恢复

参数严格包含目标 epoch、预期 generation、before-state 摘要、操作和 TTL。目标端用 owner + generation + digest 的 CAS 检查；Action identity + digest 的回执用于幂等。不同 Action 的过期/重复命令不能覆盖后续 owner。目标最多保留 4096 条回执，满后拒绝新变更，不能通过驱逐回执重新放行重放。

变更执行与控制面回执分开提交。网络错误或丢失回执进入 `EXECUTION_UNKNOWN`；超时 Worker 不走只读任务的重放路径。恢复只读取目标状态和目标回执，比较 Action、epoch、所有权、generation、before/intended/after；保留原 ActionAttempt 的 UNKNOWN 历史及核对结果，Audit/Outbox 记录全过程。无法归因进入人工核对，不凭当前 restricted 位推定成功。

TTL 由目标的本地单调时钟和定时器执行；控制面/数据库离线不会延长。目标重启恢复开放路径，并生成新 epoch，旧命令失效。不持久化访问或遏制状态。补偿也通过同一个能力和完整授权链执行，必须引用同环境/目标/Scope 的原 Action。

## 独立验证和过期复核

CONTAINMENT 必须含固定三维条件：独立 Worker 新发 HEAD `/attack`=403、HEAD `/health`=200 且可达、所需 Sensor 健康且输入证据新鲜、窗口完整。禁止使用原执行 Worker，也禁止把 state snapshot 或 DETECTION 结果替代攻击路径检查。PASS 的有效期不超过目标 TTL，不声称 REMEDIATION 或 CLOSED。

Verification Worker 从持久化的执行回执扫描并登记 active 与 TTL-expired 两轮检查；重启后能补登记，重复扫描幂等。TTL-expired 检查有明确 not-before，新采集 Evidence；初次 PASS 过期不能替代复核。观测不足 INCONCLUSIVE，业务 HTTP 不可用或测试路径未受限 FAIL。

## 预留容量与 Gate D 影响

复用 `TaskRuntime.task_type` 分类 BACKGROUND、SECURITY_CRITICAL、RECOVERY，无第二套队列。显式开启的策略绑定独立 Worker 类别和正数容量；每环境事务锁下读取真实有效 lease，Task 与 Verification 共同计算 recovery 容量。后台不能借用关键/恢复槽；共享能力有关键待执行项时后台让出。未获准任务保留在数据库，记录 deferred；队列统计报告 admitted/backlog/running/completed/cancelled/dropped，未实现丢弃路径，dropped=0。

默认未开启预留策略的旧路径仍有改动，因此最终源码需重跑受影响的 100/1000 task benchmark；新路径单独做 saturation。事件 100k 管线未变；是否追加 10000 task 或 soak，以新基准实际差异和异常决定，不能沿用旧 RC 证明新路径。

## 当前证据边界

新增单元/集成测试使用真实 HTTP 与 PostgreSQL，事件和 Sensor 状态明确标为 SYNTHETIC。它们证明软件机制，不能冒充 Real Sensor 最终验收。全部旧 360 个测试保留；正式矩阵、ZIP 和 PASS 必须等待最终 RC 上完整 Gate E。

## 最终 RC 验证

RC7 完整 Gate E、真实双 Sensor 五项补验和末轮 381 测试已通过。详见 [最终报告](VALIDATION_REPORT_v0.6.0.md)。上面的实现约束仍有效。
