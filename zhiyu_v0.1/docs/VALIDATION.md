# 验证记录索引

当前版本 **v0.2.0 PASS / M2 Event-to-Incident Phase PASS**，最终 147 项测试与 50 项 Docker runtime 检查通过。当前权威结果见 [v0.2.0 验收报告](VALIDATION_v0.2.0.md)、[Gate A](GATE_A.md)、[Gate B](GATE_B.md)、[Gate C](GATE_C.md)。真实 Sensor Runtime 和 A01–A15 仍为 NOT_RUN。

以下为保留的 M1.1 历史验证记录；其中版本、测试数量、migration head 和早期 NOT_RUN 不表示当前工程状态。

## M1.1 验证记录 — 2026-09-13（历史）

当前结论：**M1.1 PASS**。后续 Linux Docker 验收已完成，37 项 runtime 检查、46 项容器内测试和 1 项宿主 Compose 测试通过，见 [Docker Runtime 报告](DOCKER_RUNTIME.md)。架构仍为 ai.5 / FROZEN，AI 和主动安全执行均禁用，A01–A15 平台验收仍未执行。

下面保留首次本地验证的历史记录；其中 Docker NOT_RUN 和 pytest skip 描述的是 Docker 安装前的那次执行，不是当前状态。

## 首次本地验证的实际环境和结果

| 检查 | 结果 | 证据与边界 |
|---|---|---|
| ai.5 包自检 | PASS | 原包校验器报告 234 checks / 53 个合成对象；不代表真实场景通过 |
| 冻结 Contract / JSON Schema | PASS | domain 与 baseline models.py 字节一致；30 种 Contract 的全部生成定义与冻结 Schema 一致，53 个 fixture 对象验证及映射往返通过 |
| Python 编译与导入 | PASS | Python 3.12.14；compileall、模块导入、数据库驱动不可用时的应用导入与 health 测试 |
| 类型检查 | PASS | mypy：39 个源码文件无错误；原封不动保留的 ai.5 Contract 未完整标注类型，明确排除其内部类型错误，不宣称冻结文件已经完成类型修整 |
| Lint / 格式 / Schema 快照 | PASS | Ruff check / format --check；固定迁移生成的 PostgreSQL SQL 和 Schema 文档可重现 |
| 最终完整 pytest | **46 passed, 1 skipped, 2 warnings** | 41.33 秒；[原始输出](test-run.txt)、[JUnit](test-results.xml)；唯一 skip 为显式关闭的真实 Compose smoke |
| PostgreSQL integration | PASS，33 项 | 独立 Windows x64 PostgreSQL 17.11、loopback 随机端口；强制 ZHIYU_REQUIRE_POSTGRES=1，无 SQLite 替代；每例独立临时 schema |
| migration upgrade / downgrade / upgrade | PASS | 固定 revision 0001_m1_1；30 张 Contract 表 + 4 张基础设施表 + Alembic 版本表，循环 FK 与不可变触发器的回退路径实际执行 |
| migration 与 ORM 漂移 | PASS | alembic check：No new upgrade operations detected；额外比较全部 CHECK 名称并用非法数据验证关键约束，因为 Alembic 默认不比较 CHECK 表达式 |
| Bootstrap / Audit CLI | PASS | 合成被动配置登记 1 Environment / 3 Resource / 1 Scope；重复无额外副作用，审计链校验通过 |
| 真实 HTTP / 数据库故障恢复 | PASS | 独立 Uvicorn 进程与真实 PostgreSQL；见 [六项结果](RUNTIME_SMOKE_RESULT.json) |
| Docker Compose 配置 | PASS | 官方独立 Compose v5.5.1：config --quiet；测试检查 migration/bootstrap 依赖、loopback 绑定和独立 test stage |
| Docker build / Compose runtime | **NOT_RUN** | 本机 Docker Engine named pipe 不存在；独立 Compose 客户端不能替代 Engine，未验证镜像构建、容器网络或 Linux 运行 |

两条警告来自上游 Starlette 对 httpx TestClient 和 AnyIO BlockingPortal alias 的弃用提示，没有把警告隐藏或作为测试通过的替代条件。

## 已验证的行为

- 原子 Bootstrap；跨环境引用、主动模式和内容不同的重复标识被拒绝；Resource 绑定更新使用 row_version 乐观并发。
- 同来源重发保留独立 receipt，但只有一个 canonical event 与一个 outbox 意图；跨 Collector 转发保留，时间戳或业务内容被修改的相同来源身份返回冲突。
- 事件、receipt、Audit、Outbox 同事务提交；审计或 Outbox 注入故障、FK 错误、连接中断与数据库锁超时均不能留下部分提交。
- 四个并发接收者竞争同一事件时只产生一个 canonical event；重试能够恢复，非法数据不会被当成普通 duplicate。
- 服务身份限制 environment / collector / source_type / permission；伪造来源、资源或 validation_run_id 拒绝；批量尺寸和请求体上限生效；错误正文不返回 SQL、输入载荷或凭据。
- Audit 哈希链、顺序与不可变记录；不存在的审计流返回 false。数据库管理员仍能改 schema 或禁用触发器，不宣称具备外部锚定防篡改能力。
- Outbox SKIP LOCKED、限次重试、过期重领、generation 更新以及旧 Worker ACK 拒绝；这是消息基础设施测试，尚无 Action 执行器。
- Action 幂等、授权摘要绑定、跨环境 FK 与不可变参数的数据库约束；三维 Verification 的非法 PASS 被拒绝。未执行真实 Action、Policy Gate 或 Probe。
- DB 停机时应用进程可启动且 /health=200、/ready=503、写入=503；恢复后同一 API 进程 /ready=200、重发仍是 duplicate。

## 重现

使用 README 的锁定环境安装方式，并为专用开发数据库设置 ZHIYU_DATABASE_URL 和 ZHIYU_TEST_DATABASE_URL。不要对已有业务数据的数据库执行 downgrade。

```bash
python -m compileall -q src tests migrations tools
mypy
ruff check src tests migrations tools
ruff format --check src tests migrations tools
python tools/schema_snapshot.py --check
# 环境变量 ZHIYU_REQUIRE_POSTGRES=1，确保数据库测试必须执行
pytest -q --junitxml=docs/test-results.xml
alembic upgrade head
alembic check
zhiyu bootstrap --file config/bootstrap.lab.json --actor local-admin
zhiyu verify-audit --environment lab-zhiyu-01
```

pytest 中的 migration roundtrip 使用独立随机 schema 自动执行 downgrade / upgrade。命令行 roundtrip 也已在本轮临时数据库上完成。原始输出记录中的宿主名称、路径和时区是本机执行元数据，数据库连接凭据不进入交付包。

有 Linux Docker Engine 后执行：

```bash
python tools/compose_smoke.py
docker compose --profile test run --build --rm tests
```

第一条现已扩展为完整 Docker Runtime 验收，结果按随机项目名留档，结束时保留自己的命名卷；第二条运行 Linux 容器内的完整非 Compose 测试。缺少 Docker CLI 时返回 NOT_RUN / exit 2，Engine 或运行检查失败时返回非零；只有完整运行成功才记录 PASS。

## 尚未证明的事项

未测吞吐量；M1 接收以 environment 行锁串行化以保持明确的 Bootstrap/审计事务顺序，不能据此宣称高吞吐。部分 JSONB 内部 ID 列表与多态引用仍须未来服务校验，30 张表不等于完整状态机运行时。

双源真实 Adapter、窗口关联、EventGroup/CorrelationDecision 服务、Task/Worker 执行侧 fencing、Scope/Policy 运行时 Gate、未知执行状态 reconcile、独立探针、真实 SCN-LAB-AUTH-01 与 A01–A15 均待后续单元完成。Golden Chain 缺少 lab-gateway StateEntity 的 fixture 问题见 [审计报告](REPOSITORY_AUDIT.md)，不需要升级 Contract。
