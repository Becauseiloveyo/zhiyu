# v0.6.0 Final Acceptance Report

**v0.6.0 PASS / CONTROLLED LAB。** RC7 完整 Gate E 与 A01–A15 全部通过；正式包的 CRC、逐文件 Manifest/SHA、秘密排除和 source-image-ZIP 原始字节对应均通过；见 [打包校验](PACKAGE_VALIDATION_v0.6.0.json)。最终 ZIP SHA 位于包外校验文件，避免递归。

修复范围是 A05/A06/A07/A09/A11 的最小软件前置条件。ai.5 冻结契约与旧 360 个测试保持原字节；仅 uv.lock 的项目自身版本由 0.5.0 修正为 0.6.0，无依赖升级。

## 冻结与回归

- source：`f60a06b0db456ac2c7e282c5522241165747ab65592d64f5d06bd871e5c1aa05`；head：`0016_lab_remediation`；72 张表（含 Alembic）。
- [RC freeze](../RC_STATE_v0.6.0.json) 冻结代码、工具、配置、测试和锁；[静态检查](m6-runtime/gate-e-final-static.json)、[360 旧测试保留关系](m6-runtime/gate-e-test-retention.json)、[1594 项历史证据哈希](m6-runtime/gate-e-historical-integrity-final.json) 全部通过。
- 最后完整回归：**381 passed / 0 failed / 0 skipped**，其中 380 个镜像内非 Compose 测试使用真实 PostgreSQL，1 个宿主 Compose 测试包住完整 Gate E。[final-test-results.xml](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-test-results.xml)；[host JUnit](m6-runtime/rc/RC7-host-final-tests.xml)。预备回归不重复累计。
- 新 migration 仅扩大 internal ActionResult side-effect CHECK 以记录 LAB_PATH；往返和无 schema 漂移通过，有 Lab receipt 时降级明确拒绝以保留证据。[final-migration.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-migration.json)。

## 真实运行

全新 `zhiyu-smoke-771744b23fbb`，182 项 runtime 检查；源码烘焙进镜像，无工作区源码覆盖。[result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/result.json)、[image-source-correspondence.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/image-source-correspondence.json)。

真实 Suricata / Wazuh、原始行 SHA、双源 lineage、故障及恢复在新 sensor project 复验。[sensors/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/result.json)、[sensors/sensor-faults/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/sensor-faults/result.json)、[sensors/a10-database-outage/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/a10-database-outage/result.json)。

五项修复由 [sensors/remediation/result.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/sensors/remediation/result.json) 记录：实际修改后回执丢失和只读核对、旧 Worker/重复/外 owner 补偿保护、三项独立遏制验证与反例、数据库停止时原生 TTL 和新证据复核，以及背景饱和时新鲜真实 IDS 告警处理与恢复容量。

A11 的 recovery 实测 23.062 秒；完整 queue depth、admitted、deferred、dropped、有效租约及关键完成数保存在原始记录。这是受控观测值，不承诺 SLA。

## 受影响的调度复验

[remediation-task-benchmark.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/remediation-task-benchmark.json)：

| 执行任务 | 逻辑 Action | 秒 | 未执行尾部任务 |
|---|---|---|---|
| 100 | 100 | 17.010 | 2 |
| 1000 | 1000 | 173.741 | 2 |

扩容与 soak 是否追加，见 [调度影响评估](m6-runtime/gate-e-scheduler-impact-review.json)。最终判定须使用已完成的评估，不能只因小样本通过就声称旧大负载证据对新源码有效。

## 安全和版本边界

[boundary-index.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/boundary-index.json) 的 26 项 SCRIPTED_NOT_AI 与 [ai-evaluation.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/ai-evaluation.json) 的真实模型评估分开统计。模型离线、异常输出、伪造证据、越界、风险上限、崩溃恢复及数据库故障均有拒绝/恢复证据。[final-database-snapshot.json](m6-runtime/gate-e-final/zhiyu-smoke-771744b23fbb/final-database-snapshot.json) 的 Audit 链有效，高风险自动执行 0；[秘密扫描](m6-runtime/gate-e-secret-scan.json) 检查已知私密值及格式命中。

仅 CONTROLLED LAB；未验证 Production、客户环境、长期 SLA、Cloud、Windows Sensor 或 OT/ICS。AI 默认 OFF，启用默认 SHADOW；REFERENCE_GROUNDED 只证明引用约束，不等于模型语义正确。Lab 状态能力仅限显式安装和授权的固定目标，不支持任意 shell/firewall/credential/persistence/lateral movement。高风险自动执行为 0。

历史 Gate D 的 4 并发模型请求有 2 次 TIMEOUT 安全回退；资源采样尾部缺口 153.813523 秒；Outbox 398200 pending（无消费端），45 个有意保留任务。这些原始限制仍然保留。旧 30 分钟 soak 和 10000 任务结果属于旧源码，未冒充新 RC 的结果。

## 历史和交付

RC5 网络构建超时、一次被取代的构建和 RC6 旧模块数断言失败原样保留。RC7 只修正验收模块清单比较，产品源码与 RC6 相同；最终完整运行重新执行。RC3 旧结论保存在 [历史文档归档](m6-runtime/rc3-final-documents/archive-manifest.json)，其 NOT PASS 不能被误当作当前结论，也未被覆盖。

[完整矩阵](A01_A15_ACCEPTANCE_MATRIX.md) · [证据索引](FINAL_EVIDENCE_INDEX_v0.6.0.md) · [文件变化](FILES_CHANGED_v0.6.0.md) · [正式 Gate E](m6-runtime/gate-e-acceptance.json)。No ai.5 architecture change required。本轮到 Gate E 为止，不进入 v0.9。
