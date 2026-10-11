# M1.1 Status — 2026-09-13

当前工程状态以 [PROJECT_STATE.yaml](../PROJECT_STATE.yaml) 为准；保留的 ai.5 YAML 只描述设计冻结时的状态。

已完成：30 契约表 + 4 基础设施表、固定首版迁移、被动 Bootstrap 与 Repository、原子事件接收/去重/收据/Audit/Outbox、最小 API 来源身份、Health/Readiness、PostgreSQL 集成测试与真实 HTTP 数据库故障恢复。

M1.1 PASS：Linux Docker 实际镜像 build、Compose 启动及 37 项容器运行检查已通过；46 项容器内测试和 1 项宿主 Compose 测试全部通过。实际失败、修复、重启/卷持久化证据见 [DOCKER_RUNTIME.md](DOCKER_RUNTIME.md)。

M2 Runtime 未实现：双源 Adapter、窗口关联、Incident 状态机、Task Worker/Fencing、Gate/Gateway、独立 Probe、真实 SCN-LAB-AUTH-01。M3 AI 禁用，A01–A15 仍全部 NOT_RUN。

详细证据见 [VALIDATION.md](VALIDATION.md)。
