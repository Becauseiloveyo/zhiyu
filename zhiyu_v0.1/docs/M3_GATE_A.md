# Gate A — Deterministic Plan + Task Graph — PASS

2026-09-14，进入 Gate B 前执行：155 passed / 0 failed / 0 skipped；1 个 Compose orchestration 案例留到最终 Docker E2E。旧 v0.2 的 146 项非 Compose 案例全部保留，新增 9 项。证据：[JUnit](m3-gate-a-tests.xml)、[输出](m3-gate-a-tests.txt)。Ruff check、mypy 61 源码文件通过。两种既有上游弃用警告保留。

复用 AIPlan/ContextBundle/Task 契约；没有模型调用。稳定计划 identity、Incident 快照/策略冲突检查、版本变化、关系成员/依赖、DAG cycle/missing/cross-plan/capability/target 检查、状态表与冻结 ai.5 精确一致、依赖就绪/终止失败传播、并发规划、Audit 失败全回滚及重建 Session/Engine 后幂等均通过。

0005_plans 仅新增 response_plan_metadata、task_runtime、task_graph_edges 三张内部表；Plan 快照及图边有不可变保护，双向图边外键使用不同显式名称，修复首次生成迁移的命名冲突。完整 migration roundtrip、无 metadata 漂移通过。数据库重启后的随机端口已重新发现，本机测试 helper 不再缓存旧端口。

Gate A 不执行 Task 动作；lease 领取、运行守卫和真实 executor 将分别在 Gate C/D 验收。当前版本仍是开发中的 v0.3 工作区，不据此宣称整个 v0.3 通过。
