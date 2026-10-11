# CHANGELOG

## 0.9.0 — 2026-10-04 — Competition-ready Product / Web Console

- 保留定稿前端与原 Logo，真实 Product API、Incident 全链路、时间线、来源图谱、报告和回放。
- 固定受控 A–E 场景、逐场景重置/清理/无副作用回放；演示元数据与安全事实分开。
- 464项完整回归、463项Linux测试、189项Docker运行检查、15项前端测试与浏览器验收通过；原381测试和28冻结文件保持。
- 最终交付逐文件SHA/CRC/秘密排除/字节对应通过；[验收报告](docs/VALIDATION_REPORT_v0.9.0.md)。
- ai.5保持，AI默认OFF/启用默认SHADOW，高风险自主执行0。CONTROLLED LAB，未进入v1.0。

## 0.5.0 — 2026-09-17 — AI Decision Brain

- 有界来源 Context、Model Gateway、持久化预算/回执、结构化分析与 Proposal 校验。
- SHADOW / Lab ASSISTED、旧执行链和独立 Verification、受预算限制的 AI re-plan 与确定性回退。
- 固定 0011–0015 迁移；343 tests / 190 Docker checks；24 个真实本地模型受控案例，不宣称通用 AI 准确率。
- ai.5 / 旧执行与验证核心保持不变；默认 AI 关闭；[Validation](docs/VALIDATION_REPORT_v0.5.0.md)。

## 0.4.0 — 2026-09-16 — Continuous Verification & Re-plan

- 独立三维验证、可解释断言、Evidence 资格过滤、Effectiveness 与 StateEntity 事实/推断分离。
- PostgreSQL 检查租约/fencing/恢复/幂等；有限重规划、风险 ceiling、循环检测和新授权。
- 0008–0010 增量迁移；245 tests / 135 Docker checks PASS；四条真实受控闭环与 100/1,000 verification runs 实测。
- ai.5 原样保留；AI / Real Sensor / A01–A15 / production SLA 仍未验收。见 [Validation Report](docs/VALIDATION_REPORT_v0.4.0.md)。

## 0.3.0 — 2026-09-15 — Deterministic Response Control

- ai.5 冻结基础上复用 Plan/Task/Lease/Capability/Authorization/Action 契约，完成确定性 Plan 和关系 Task DAG。
- 增加固定能力目录、独立健康、完整授权输入和风险解释、Scope/digest/租约/预算/证据守卫。
- PostgreSQL 调度、有界退避、代次 fencing、只读 Gateway、实际数据库查询与 HEAD 探测；完成回执与重放/中断恢复。
- 增量 migration 0005–0007，11 张内部表；旧 v0.2 数据往返迁移保留，未改变既有事件智能实现。
- 新增 54 个测试；总计 201 passed / 0 failed / 0 skipped；Docker 81/81 PASS；100/1,000 次真实任务性能留存。
- AI、高风险/状态改变动作、Verification、Re-plan、真实 Sensor Runtime 和 A01–A15 仍未启用或未运行。详见 [验证报告](docs/VALIDATION_REPORT_v0.3.0.md)。

## 0.2.0 — 2026-09-14 — Deterministic Event Intelligence

- 在 ai.5 冻结基线上实现正式 Suricata/Wazuh Adapter、逐条错误隔离、原始字节与来源留存、版本化严重度及时间映射。
- 新增确定性关联键、固定窗口、迟到/过期策略、关系化分组成员与可解释 CorrelationDecision；保留所有来源事件。
- 新增 Incident 晋升、限时合并、因素式风险解释、Evidence 归属/原始来源回溯、分页查询和 NEW→TRIAGED→INVESTIGATING 守卫。
- 以每环境行锁、唯一约束、检查点、CAS 和同事务 Audit/Outbox 保证重放、并发与失败重试的幂等。
- 增量迁移 0002/0003/0004，新增 10 张内部表；原始迁移、SQL 和 ai.5 Contract 不变。
- 完整合成 Golden Chain、Docker 重启/重放与 1k/10k 实测；准确结果见 [v0.2.0 验证报告](docs/VALIDATION_v0.2.0.md)。阶段名称为 M2 Event-to-Incident Phase；Task/Action/Verification/AI 和真实 Sensor Runtime 未实现或未运行。

## 0.1.1 — 2026-09-13 — M1.1 Docker Runtime 验收完成

- 实际通过 Docker Desktop 4.90.0 / Engine 29.7.2 / Compose 5.5.1 / WSL2 Linux 的 hello-world、无缓存 build、Compose 启动和 37 项运行检查。
- 扩展 `tools/compose_smoke.py`，由 `tools/runtime_acceptance.py` 执行真实 HTTP A–E、事务 ID 检查、迁移失败与正反向路径、Bootstrap 幂等、数据库恢复、API/Compose 重启、卷与数据摘要保持、容器内完整测试和脱敏证据输出。
- 修复实测发现的 smoke 脚本端口缓存问题：随机发布端口可在 API restart 后重新分配，现重新发现端口再验证。
- 使用当前子进程代理配置解决 Buildx 获取 Docker Hub 匿名令牌超时；未修改全局代理、业务代码、数据库迁移或 ai.5 Contract。
- 最终 Linux 测试 46 passed、0 skipped；宿主 Compose 测试 1 passed、0 skipped。保留早期失败/中断记录，更新当前状态为 M1.1 PASS。
- 验收结束仅清理本次容器/网络，命名卷保留；M2.1、真实 Sensor、A01–A15 仍未实施/未执行。

## 0.1.1 — 2026-09-13 — M1.1

- 审计收到的 M1 Skeleton；保持 ai.5 Contract 字节一致，不升级架构基线。
- 30 个契约对应 PostgreSQL 显式列与 JSONB，补齐 7 种缺失对象；4 张内部表承载收据、资源关联和审计链头。
- 固定 Alembic 0001_m1_1，明确复合 FK、CHECK、Unique、Index、乐观版本；循环外键与不可变触发器有明确反向迁移。
- Environment/Resource/Scope Repository 与被动 Bootstrap；重复运行无重复副作用，显式 Resource rebind 使用 CAS 与审计。
- 事件原子入库：环境/Collector/source_type 身份、资源与测试标签校验，来源去重、冲突拒绝、每次交付收据、同事务审计及 Outbox。
- 修复所有 IntegrityError 被当作重复的问题，以及测试发现的复合主键顺序读取错误。
- Audit 哈希链、并发链头；Outbox 有界重试、SKIP LOCKED、租约/代次、过期 ACK 拒绝。
- 业务 API 默认 fail closed；最小服务凭据权限；请求大小/耗时限制和错误内容清洗。
- Health/Readiness 分离，真实 HTTP 验证数据库离线启动、恢复及重发。
- 依赖锁文件、镜像 digest、非 root 容器、迁移/Bootstrap Compose 服务、DB/Compose 测试入口与工程状态文档。
- AI、主动安全执行、M2 闭环、A01–A15 验收仍未启用/未完成。
