# Files changed — v0.1 Skeleton → v0.1.1 / M1.1 首次本地交付

这是首次本地交付的历史清单。随后 Docker Runtime 阶段新增的验收脚本、运行证据和文档变更见 [DOCKER_RUNTIME.md](DOCKER_RUNTIME.md)；该阶段未修改业务源代码、迁移、依赖或已有测试。

以收到的原始 Skeleton zip 为比较基线；不计缓存、虚拟环境或构建产物。本清单自身不计入统计。

新增 53，修改 26，删除 0，原样保留 13。

## 关键文件与用途

- `src/zhiyu/db/`：30 种 Contract 的显式 PostgreSQL 映射、4 张内部表、转换及连接配置。
- `migrations/versions/0001_m1_1_m1_1_ai_5_initial_postgresql_schema.py`：固定初始迁移、循环引用、不可变触发器及 downgrade。
- `src/zhiyu/repositories/`：Bootstrap 读取/写入、Resource CAS、来源去重、审计链和 Outbox 租约。
- `src/zhiyu/services/`、`src/zhiyu/api/`、`src/zhiyu/cli.py`：明确事务边界、最小身份限制、被动 Bootstrap、health/readiness。
- `tests/`、`baseline/ai5/`：冻结基线、53 个合成对象及 47 项可收集测试，其中 33 项使用真实 PostgreSQL。
- `Dockerfile`、`docker-compose.yml`、锁文件：可复现依赖、迁移/Bootstrap job、非 root API 容器及集成测试 stage。
- `docs/REPOSITORY_AUDIT.md`、`docs/VALIDATION.md`、`PROJECT_STATE.yaml`：审查证据、实际验证结果和未完成边界。

## 相对原包的明细

| 状态 | 文件 |
|---|---|
| 修改 | `.env.example` |
| 修改 | `.gitignore` |
| 修改 | `Dockerfile` |
| 修改 | `README.md` |
| 修改 | `alembic.ini` |
| 修改 | `docker-compose.yml` |
| 修改 | `docs/M1_STATUS.md` |
| 修改 | `migrations/env.py` |
| 修改 | `pyproject.toml` |
| 修改 | `schema/0001_initial_postgresql.sql` |
| 修改 | `src/zhiyu/__init__.py` |
| 修改 | `src/zhiyu/api/routes/events.py` |
| 修改 | `src/zhiyu/api/routes/health.py` |
| 修改 | `src/zhiyu/api/routes/incidents.py` |
| 修改 | `src/zhiyu/core/config.py` |
| 修改 | `src/zhiyu/db/base.py` |
| 修改 | `src/zhiyu/db/models.py` |
| 修改 | `src/zhiyu/db/session.py` |
| 修改 | `src/zhiyu/main.py` |
| 修改 | `src/zhiyu/repositories/events.py` |
| 修改 | `src/zhiyu/repositories/incidents.py` |
| 修改 | `src/zhiyu/services/event_intelligence.py` |
| 修改 | `src/zhiyu/services/verification.py` |
| 修改 | `tests/test_api.py` |
| 修改 | `tests/test_contracts.py` |
| 修改 | `tests/test_event_repository.py` |
| 新增 | `.dockerignore` |
| 新增 | `CHANGELOG.md` |
| 新增 | `PROJECT_STATE.yaml` |
| 新增 | `baseline/ai5/models.py` |
| 新增 | `baseline/ai5/state_machines.json` |
| 新增 | `baseline/ai5/zhiyu.schema.json` |
| 新增 | `config/bootstrap.lab.json` |
| 新增 | `docs/DEPENDENCIES.md` |
| 新增 | `docs/REPOSITORY_AUDIT.md` |
| 新增 | `docs/RUNTIME_SMOKE_RESULT.json` |
| 新增 | `docs/SCHEMA.md` |
| 新增 | `docs/VALIDATION.md` |
| 新增 | `docs/test-results.xml` |
| 新增 | `docs/test-run.txt` |
| 新增 | `migrations/versions/0001_m1_1_m1_1_ai_5_initial_postgresql_schema.py` |
| 新增 | `requirements-dev.lock` |
| 新增 | `requirements-runtime.lock` |
| 新增 | `src/zhiyu/api/body_limit.py` |
| 新增 | `src/zhiyu/api/security.py` |
| 新增 | `src/zhiyu/cli.py` |
| 新增 | `src/zhiyu/core/canonical.py` |
| 新增 | `src/zhiyu/core/errors.py` |
| 新增 | `src/zhiyu/core/identity.py` |
| 新增 | `src/zhiyu/db/contract_rows.py` |
| 新增 | `src/zhiyu/db/infrastructure.py` |
| 新增 | `src/zhiyu/db/mapping.py` |
| 新增 | `src/zhiyu/repositories/audit.py` |
| 新增 | `src/zhiyu/repositories/base.py` |
| 新增 | `src/zhiyu/repositories/environments.py` |
| 新增 | `src/zhiyu/repositories/outbox.py` |
| 新增 | `src/zhiyu/repositories/resources.py` |
| 新增 | `src/zhiyu/repositories/scopes.py` |
| 新增 | `src/zhiyu/services/bootstrap.py` |
| 新增 | `src/zhiyu/services/event_ingest.py` |
| 新增 | `src/zhiyu/services/health.py` |
| 新增 | `src/zhiyu/services/incidents.py` |
| 新增 | `tests/conftest.py` |
| 新增 | `tests/fixtures/ai5/approval.json` |
| 新增 | `tests/fixtures/ai5/capabilities.json` |
| 新增 | `tests/fixtures/ai5/environment.json` |
| 新增 | `tests/fixtures/ai5/evidence_payloads.json` |
| 新增 | `tests/fixtures/ai5/golden_chain.json` |
| 新增 | `tests/fixtures/ai5/scenario.json` |
| 新增 | `tests/fixtures/ai5/verification_cases.json` |
| 新增 | `tests/test_action_storage.py` |
| 新增 | `tests/test_api_boundaries.py` |
| 新增 | `tests/test_bootstrap.py` |
| 新增 | `tests/test_compose.py` |
| 新增 | `tests/test_outbox.py` |
| 新增 | `tests/test_schema_and_baseline.py` |
| 新增 | `tools/compose_smoke.py` |
| 新增 | `tools/schema_snapshot.py` |
| 新增 | `uv.lock` |
| 原样保留 | `Makefile` |
| 原样保留 | `docs/AI_CONTEXT_ai.5.md` |
| 原样保留 | `docs/PROJECT_STATE_ai.5.yaml` |
| 原样保留 | `lab/README.md` |
| 原样保留 | `migrations/script.py.mako` |
| 原样保留 | `src/zhiyu/api/__init__.py` |
| 原样保留 | `src/zhiyu/api/routes/__init__.py` |
| 原样保留 | `src/zhiyu/core/__init__.py` |
| 原样保留 | `src/zhiyu/db/__init__.py` |
| 原样保留 | `src/zhiyu/domain/__init__.py` |
| 原样保留 | `src/zhiyu/domain/contracts.py` |
| 原样保留 | `src/zhiyu/repositories/__init__.py` |
| 原样保留 | `src/zhiyu/services/__init__.py` |
