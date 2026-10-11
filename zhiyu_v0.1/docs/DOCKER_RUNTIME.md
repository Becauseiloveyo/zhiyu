# M1.1 Docker Runtime — PASS

验收日期：2026-09-13。工程保持 v0.1.1，Architecture Baseline 保持 ai.5 Engineering Freeze。AI、主动安全执行、真实 Sensor 和 A01–A15 未启用/未执行。

本次实际运行了 Docker Engine、Linux images、PostgreSQL、migration、bootstrap、API 和 tests。最终 [37 项机器记录](docker-runtime/zhiyu-smoke-a35906dee8ed/result.json) 全部 PASS；[宿主 Compose 测试](docker-compose-test.txt) 通过。首次无缓存构建的完整证据见 [build-proxy.log](docker-runtime/environment/build-proxy.log)。最终验收重新构建了修复后的脚本，使用已有层缓存。

## Environment

| 项目 | 实测结果 |
|---|---|
| Docker Desktop | 4.90.0 (238679)，安装于 D:\Docker\Desktop |
| Docker CLI / Engine | 29.7.2 / 29.7.2，API 1.55 |
| Compose | 5.5.1 |
| Context / daemon | desktop-linux，Docker Desktop Linux Engine 正常响应 |
| OSType / architecture | linux / amd64 |
| WSL2 kernel | 6.6.87.2-microsoft-standard-WSL2 |
| Image Python | 3.12.14，39 个业务模块实际导入 |
| PostgreSQL | 17.11，Debian 17.11-1.pgdg13+2 |
| DB connection timezone | UTC |
| API UID | 10001，非 root |

[docker version](docker-runtime/environment/version.log)、[docker info](docker-runtime/environment/info.log)、[context ls](docker-runtime/environment/contexts.log)、[hello-world](docker-runtime/environment/hello.log) 均为实际命令记录。配置、inspect 和日志中的临时数据库密码已脱敏。

## Implemented

- `tools/runtime_acceptance.py`：可重复运行的 Linux Docker 验收，按随机项目名隔离，生成结果、命令退出码、耗时、脱敏日志和 JUnit；只使用 Python 标准库，没有新增依赖。
- `tools/compose_smoke.py`：保留既有入口，调用完整验收。
- 修复 API restart 后随机宿主端口缓存错误；每次重启/重建后重新读取实际发布端口，保存端点变化记录。
- 同步 README、CHANGELOG、PROJECT_STATE、状态/验证/审计文档；保留首次本地验证与本轮中断/失败证据。

业务源代码、数据库 migration、已有 pytest 用例、依赖和 ai.5 Contract 与上一交付版本相比没有修改。没有通过移除测试、降级依赖或放宽断言消除失败。

## Docker Runtime

最终项目为 `zhiyu-smoke-a35906dee8ed`。验收时 `postgres` 和 `api` 均 healthy、RestartCount=0；`migrate` 和 `bootstrap` 均 exited(0)；tests exited(0)。API 仅绑定 loopback 随机端口；PostgreSQL 没有发布宿主端口。

数据存储使用 Docker managed volume `zhiyu-smoke-a35906dee8ed_zhiyu_pg`，容器目标为 `/var/lib/postgresql/data`。未把 PostgreSQL 数据 bind mount 到 Windows 目录。测试实际执行 API restart，以及不带 `-v` 的 Compose down/up；卷的 CreatedAt 和持久数据摘要保持一致。

完成后已执行正常 `down`，测试容器和网络已移除，命名卷保留。报告中的 `http://127.0.0.1:32772` 是本次验收端点，当前不提供常驻服务。中断和失败项目的两个卷也保留，供复核；未执行全局 prune 或删除卷。

## Tests

| 类型 | 数量 | 实际运行位置 | Passed / Failed / Skipped |
|---|---:|---|---|
| Unit / Contract / 静态配置 | 7 | Linux tests image | 7 / 0 / 0 |
| API in-process integration | 6 | Linux tests image | 6 / 0 / 0 |
| PostgreSQL integration | 33 | Linux tests image → Docker PostgreSQL；ZHIYU_REQUIRE_POSTGRES=1 | 33 / 0 / 0 |
| Compose end-to-end | 1 | Windows Docker host → Linux containers / 真实 HTTP | 1 / 0 / 0 |
| 合计 | **47** | 两次互补 pytest 调用 | **47 / 0 / 0** |

Linux pytest：`46 passed, 1 deselected, 2 warnings in 14.32s`，见 [原始输出](docker-runtime/zhiyu-smoke-a35906dee8ed/096.log)、[JUnit](docker-runtime/zhiyu-smoke-a35906dee8ed/test-results.xml)。其中唯一 deselected 是需宿主 Docker CLI 的 Compose 测试。

宿主 pytest：`1 passed, 46 deselected, 2 warnings in 124.55s`，见 [输出](docker-compose-test.txt)、[JUnit](docker-compose-test.xml)。46 个 deselected 已在 Linux 容器内运行，未跳过任何应运行的 PostgreSQL 测试。两种上游弃用警告分别来自 Starlette/httpx 与 AnyIO alias，在两个 pytest 进程中各出现一次，共 4 次警告输出；未隐藏警告。

额外通过：Ruff、mypy（39 个源码文件）、Python compile/import，以及 Schema 快照校验。数据库实际检查到 35 张表（含 Alembic 版本表）、73 个 FK、28 个 Unique、281 个 CHECK、42 个 Index；固定迁移为 `0001_m1_1`。PG 集成测试还检查了 migration/ORM drift、全部 CHECK 名称及关键非法数据拒绝。

## Smoke Test

| 项目 | 结果 | 实际证据 |
|---|---|---|
| hello-world | PASS | 拉取并执行，exit 0 |
| compose config | PASS | 使用实际随机开发凭据解析，输出脱敏 |
| image build | PASS | runtime/tests 无缓存构建成功；最终脚本重建成功 |
| compose up | PASS | Linux PostgreSQL / API / migration / bootstrap 实际启动 |
| PostgreSQL healthy | PASS | Docker healthcheck healthy |
| Migration | PASS | 独立 service exit 0 |
| Bootstrap | PASS | 独立 service exit 0 |
| API 启动 | PASS | Uvicorn 运行，UID 10001 |
| health / ready 正常 | PASS | 真实宿主 HTTP 200 / 200 |
| DB down health | PASS | 200 |
| DB down ready / write | PASS | 503 / 503 |
| DB recovery ready | PASS | 200，API Id 和 StartedAt 未变 |
| migration upgrade / downgrade / upgrade | PASS | 新建隔离库实际执行；downgrade 后 ready=503 |
| migration 失败语义 | PASS | 故意指定不存在的 revision，非零退出且 ready=503 |
| bootstrap 失败可观察 | PASS | 未迁移库执行返回错误 JSON 和非零退出 |
| bootstrap 幂等 | PASS | 第二次新增量为 0/0/0，数据库摘要不变 |
| Case A 正常 ingest | PASS | 202；Event / Receipt / Audit / Outbox 的 xmin 相同 |
| Case B duplicate | PASS | 202、duplicates=1；Event/Outbox 不重复，Receipt 新增 |
| Case C 身份相同内容改变 | PASS | 409 identity_conflict，数据库摘要不变 |
| Case D 同 fingerprint 不同 Collector | PASS | 保留两条 Event 和两个 Collector，不冒充独立观测证据 |
| Case E 错误 Environment | PASS | 403 access_denied，数据库摘要不变 |
| Case E 错误 Collector | PASS | 403 access_denied，数据库摘要不变 |
| Case E 错误 Source Type | PASS | 403 access_denied，数据库摘要不变 |
| Audit / Outbox | PASS | Audit 链有效，持久 Outbox 数量正确 |
| PostgreSQL integration tests | PASS | 全部 33 项真实连接容器 PostgreSQL |
| API restart | PASS | 重新发现随机端口，数据摘要不变 |
| Compose down/up 保留卷 | PASS | 卷 CreatedAt 与数据摘要不变，migration/bootstrap 重跑不破坏数据 |
| crash loop | PASS | 正常观察及显式重建后均无循环崩溃，RestartCount=0 |
| ai.5 修改检查 | PASS | Frozen Contract 字节不变，SHA256 见下文 |
| REAL SENSOR RUNTIME | NOT_RUN | 本轮仅使用明确标记的合成 fixture |
| A01–A15 | NOT_RUN | 未进入平台闭环验收 |

JSON 中包含 37 个细分检查；上表按用户验收项汇总，未把静态检查当作运行检查。

## Bootstrap / 持久数据

| 对象 | 实际关键字段 |
|---|---|
| Environment | lab-zhiyu-01；LAB / IT / RESTRICTED；OBSERVE_ONLY；active_validation=DISABLED；max_auto_risk=R0；model_policy=LOCAL_ONLY；data_egress_policy=DENY |
| Resource target-a | NETWORK_ENDPOINT；10.77.20.10:8080 / TCP；binding_version=1 |
| Resource validation-a | HOST；10.77.30.10 / Linux；binding_version=1 |
| Resource business-probe | HOST；10.77.40.10 / Linux；binding_version=1 |
| Scope | scope-lab-web；source=[validation-a,business-probe]；target=[target-a]；TCP/8080；max_requests_per_second=1 |

完整实际读取并通过 ai.5 Pydantic 验证的对象在最终 JSON 的 `bootstrap` 中。Scope 有效时间仍是原合成 fixture 的 2026-09-12 10:00–10:30 UTC；它不代表当前实地授权。本轮不连接这些目标。

Environment / Scope 保留 3 个设计能力名称引用，但实际 `capabilities=0`、`action_requests=0`，没有登记高权限执行器或执行 Action。最终持久状态：1 Environment、3 Resource、1 Scope、2 Event、4 Receipt、9 AuditEntry、2 Outbox；API restart 和 Compose 重建均保持数据摘要。

## Problems Found

1. **旧终端找不到 Docker，Engine 未启动。** 安装目录已进入系统 PATH，但当前进程仍持有安装前环境。使用实际安装路径给当前子进程补 PATH，执行 `docker desktop start`，确认 Linux context 与 daemon 后继续；未改全局 PATH。
2. **首轮 Buildx 获取匿名 registry token 超时。** [失败日志](docker-runtime/environment/build-first.log) 显示对 auth.docker.io 的直连超时；本机系统代理已启用在 127.0.0.1:10808。仅在构建子进程设置 HTTP_PROXY/HTTPS_PROXY 后，认证请求 200，随后无缓存构建成功。没有修改 Dockerfile、镜像 digest、依赖或全局代理。[Docker CLI proxy 说明](https://docs.docker.com/engine/cli/proxy/)及[上游 Buildx 同类问题](https://github.com/docker/buildx/issues/1979)可用于区分不同组件的代理配置。
3. **一次执行中断。** 续接时验收进程、Docker Desktop 进程和 Engine pipe 均不存在；原因未确定。[记录](docker-runtime/zhiyu-smoke-b2fb4ab0d9b1/result.json) 保持 INTERRUPTED，不计为整体验收通过。保留已有数据卷后重新运行。
4. **API restart 后脚本访问旧端口。** [失败记录](docker-runtime/zhiyu-smoke-5c1a28e8e7f0/result.json) 和 inspect 显示相同容器的宿主端口由 32768 变为 32769，内部 ready 持续 200；脚本没有重新读取端口。修复后最终记录中端点经历 32770 → 32771 → 32772，API 和 Compose 重启均通过。该问题属于 smoke harness，未降低 readiness 标准。

## Windows / WSL2 与安全边界

Compose 使用命名卷和 COPY build context，不把业务代码或 PostgreSQL 数据 bind mount 到 Windows 路径；首次 BuildKit 记录的 runtime context 为 346.49 kB、tests context 为 657.82 kB，根目录的临时数据库、压缩包和虚拟环境未传入。无自写 shell 脚本依赖 executable bit、CRLF 或 BOM；业务启动使用 exec-form Python 命令。Linux 大小写、包导入、权限和 UTC 时间字段已在真实容器中验证。未做吞吐量或磁盘性能基准测试，不宣称性能指标。

本轮随机数据库密码和调用令牌未传入 image build，镜像 config/history 不含它们，`/app/.env` 不存在；API 运行时以环境变量接收开发凭据。示例凭据明确为 development only，真实凭据没有写入 `.env` 或交付文件。API 只发布 loopback 端口，PostgreSQL 不发布宿主端口。现阶段仍是开发部署，未声称具备生产 TLS、角色分离或供应链合规验收。

## Architecture Findings / Remaining / Next

**No ai.5 architecture change required.** Contract SHA256：`663a7a597d2ef03fd2db25278858c25a5ce92fe30e55f0d3f21125503a9d85fb`。

当前里程碑：**M1.1 PASS**。下一单元：**M2.1 Suricata + Wazuh Adapter**。本轮停在 M1.1 验收关闭，没有开始 M2.2、Planner、Action 执行或 Verification Engine。原 Golden Chain 的 lab-gateway StateEntity 缺口仍待场景准备处理。

重现完整验收：在可用 Docker host 执行 `python tools/compose_smoke.py --no-cache`，或设置 `ZHIYU_RUN_COMPOSE=1` 后执行 `pytest -q -s -m compose`。后一方式会在 Linux tests 容器内运行全部非 Compose 测试，不需要挂载 Docker socket 到容器。无本地 Python 依赖需求时可直接使用前一标准库脚本入口；需要可用 Python 3.12+ 和 Docker CLI。
