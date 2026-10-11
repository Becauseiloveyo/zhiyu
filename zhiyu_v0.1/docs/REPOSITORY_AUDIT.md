# Repository Audit — 2026-09-12

范围：收到的 v0.1/M1 Skeleton；设计依据为 ai.5 的状态、30 个 Contract、JSON Schema、状态机、合成 Golden Chain、Verification Cases、A01–A15。合成示例不是授权或实测证据。本轮只做 M1.1，不实现 M2 调度/响应或 M3 模型。

## 初始事实

- FastAPI health、事件批量入口、Incident 读取入口；23 张 ORM 表及 DDL 快照。
- Domain Contract 与 ai.5 models.py 字节一致；原始两份 zip 保留用于复核。
- EventIntelligenceEngine.correlate 明确抛出 NotImplementedError（M2 占位）。Verification 仅汇总三个输入 verdict，没有探针。
- Alembic 有 env.py，无任何 revision；Dockerfile 没打包 migrations；Compose 没有 migration job。
- 4 个测试只覆盖 health、两个纯契约情形及 SQLite 重复输入；没有 PostgreSQL、事务回滚、并发、恢复测试。

## 发现及处置目标

| 问题 / 根因 | 影响 / ai.5 关系 | 本轮修复 | Contract 升级 |
|---|---|---|---|
| 所有 IntegrityError 当作 duplicate | FK/约束失败被误报成功；违反准确接收与 fail closed | 使用 PostgreSQL conflict insert，仅确认已存在的相同事件为重复；冲突报错 | 否 |
| Repository 自行 commit；没有 Audit/Outbox | 无法原子提交、回滚或恢复事件处理 | Service 控制事务，事件/收据/审计/outbox 同提交 | 否 |
| 接口无认证、无环境/Collector 绑定 | 可跨环境读写、伪造来源/测试标签 | 默认关闭业务 API；配置摘要令牌与最小服务权限 | 否 |
| JSON 代替 JSONB；大量字段仅藏在 body | 缺少数据库约束与生命周期查询 | 明确标量列、嵌套 JSONB；去除重复 body 真值 | 否，存储实现选择 |
| 缺少 SensorHealth、StateEntity/Relation、Approval、Scenario/Run、Policy 表 | 30 个契约只覆盖 23 种 | 补齐持久结构，不开启未来模块运行时 | 否 |
| 生命周期列、CHECK、环境复合 FK、乐观版本不足 | 无法可靠查询/约束状态、跨环境悬挂引用 | 固定迁移、合法值/时间约束、环境绑定及 row_version | 否 |
| 初始 migration 缺失；Dockerfile 不含迁移 | 新数据库不能直接运行 API | 固定 0001 revision，upgrade/downgrade 与 schema drift 检查 | 否 |
| health 没有对应 readiness | 无法区分进程存活与 DB/迁移可用 | 独立且有超时的 /ready，DB 故障仍能 /health | 否 |
| 重复测试使用 SQLite，外键未启用 | 无法证明 PostgreSQL 事务与并发行为 | 真实 PG 隔离 schema；显式 skip/必跑开关 | 否 |

## 冻结语义解释

- Task 成功值继续用 SUCCEEDED；观察维度用 OBSERVATION。
- ActionStatus 不增加 VERIFIED/ROLLED_BACK：EXECUTED 与 VerificationResult 是两个独立状态轴；补偿使用 COMPENSATED。
- Provenance 相同的跨 Collector 转发仍保留原始事件，M2 再标记为非独立证据。M1 去重只处理稳定来源身份的重发，不以内容相似度删除。
- Bootstrap 只登记配置，不代表环境已具备主动验证权限。本轮启动样例为 OBSERVE_ONLY / active_validation=DISABLED。
- Scope、Policy、Approval、lease/fencing 的运行时 Gate 仍属于 M2；有字段、FK 或 enum CHECK 不代表状态机守卫已经实现。

## 不进入本轮

双源真实 Adapter、窗口关联、EventGroup/CorrelationDecision 业务、Incident 生命周期转换、Deterministic Plan、Task Worker/Fencing、Action Gateway、独立探针、SCN-LAB-AUTH-01 实机闭环属 M2。LLM/Model Gateway 属 M3。A01–A15 平台级验收全部保持 NOT_RUN。

## 实现后复查 — 2026-09-13

上表中的 M1 修复目标均已写入代码；结果与限制见 [VALIDATION.md](VALIDATION.md)。

- 所有 30 个 Contract 字段都有显式列（嵌套字段为 JSONB），往返转换与完整 JSON Schema 一致性已测试。Domain 与 baseline 原文保持字节一致。
- 迁移实际 upgrade、downgrade/upgrade 和 PostgreSQL schema drift 检查通过。新增 FK 没有要求改变宏观架构。
- 并发测试发现 Resource/Scope 的 Contract 字段声明顺序与“环境优先”的 Repository 查询顺序不同；已改为显式字段映射，并以实际 DB 往返和 Resource CAS 回归验证。
- 新增证据缺口：合成 Golden Chain 的 `rel-target-control.destination_entity_id=lab-gateway` 没有对应 StateEntity。包级自检没有检查这一类引用闭合。本轮未将该合成快照直接当种子库；M2 场景准备须补齐真实 Gateway 资源/状态。Contract 能表达该实体，不需要升级 ai.5。
- Outbox 的租约测试只证明消息投递基础设施的代次与恢复；不能外推为 Action 设备侧 fencing 或 A05/A06 已验收。
- 本地可运行环境为 Windows Python 3.12.14 / PostgreSQL 17.11；PG 中文目录 initdb 失败，使用独立英文临时目录恢复。HTTP 故障脚本曾在重启 PG 时遗漏临时端口，已修正测试脚本并得到真实 PASS；这是验证脚本问题。
- Docker Compose v5.5.1 的 `config --quiet` 通过，但 Docker Engine named pipe 不存在，未完成镜像 build/容器网络/容器 smoke。
- 对空审计流的验证已改为 false，避免对未 Bootstrap 环境给出“审计链有效”的结论。

## Docker Runtime 复查 — 2026-09-13

Docker Desktop 安装后的真实 Linux Runtime 已验收为 PASS，详见 [DOCKER_RUNTIME.md](DOCKER_RUNTIME.md)。无缓存镜像构建、37 项运行检查、所有 33 项 PostgreSQL 测试及其余测试已实际完成。此前“Docker Engine 不存在”的结论仅对应首次本地验证。

实测修复发生在验收脚本：随机宿主端口在 API restart 后改变，旧脚本缓存端口导致误报超时；重新发现端口后，API 和 Compose 重启的数据摘要均一致。此次未修改业务源代码、migration、已有测试或冻结 Contract；没有证据要求升级 ai.5。
