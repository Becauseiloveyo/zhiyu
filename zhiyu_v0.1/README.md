# 智御 v1.0.0 · Stable Prototype / Final Release Freeze

智御是网络安全自主决策与持续验证平台，采用Linux-native Control Plane + Browser Web Console，PostgreSQL为canonical source。v1.0.0 PASS / STABLE PROTOTYPE；仅CONTROLLED LAB，原批准UI/项目Logo保持定稿。见 [最终验收](docs/VALIDATION_REPORT_v1.0.0.md)、[证据索引](docs/FINAL_EVIDENCE_INDEX_v1.0.0.md)、[机器状态](V1.0_STATUS.json)。

从 [安装指南](docs/INSTALLATION_GUIDE.md) 开始；后续使用 [部署](docs/DEPLOYMENT_GUIDE.md)、[升级](docs/UPGRADE_GUIDE.md)、[备份恢复](docs/BACKUP_RESTORE_GUIDE.md)、[用户手册](docs/USER_GUIDE.md)、[管理员手册](docs/ADMIN_GUIDE.md)、[演示](docs/COMPETITION_DEMO_GUIDE.md) 和 [排障](docs/TROUBLESHOOTING_GUIDE.md)。[架构](docs/ARCHITECTURE.md)、[API](docs/API_CONTRACT_v1.0.md)、[安全基线](docs/SECURITY_BASELINE_v1.0.md)、[已知限制](docs/KNOWN_LIMITATIONS.md) 说明正式边界。

正式参考安装为 Windows + WSL2 + Docker Desktop Linux Containers。实际从空目录创建独立 venv、npm cache、镜像、Compose project 与 PostgreSQL volume，经迁移、登录、真实 Sensor/本地模型场景 A 和 CLEAN，RC6 Clean Install PASS。RC12 的操作员工具变化单独复验，不把复用安装称为第二次干净安装。独立 Linux 实体主机 Clean Install = NOT_RUN。

AI 默认 OFF，启用默认 SHADOW；提案不等于授权，执行成功不等于安全成功。Action 必经 Authorization/Risk/Gateway，Verification 独立，Sensor 不足 => INCONCLUSIVE。高风险自主执行0。正式主张为 [AI-assisted analysis/planning/recommendation](docs/AI_VALUE_FINAL_POSITION_v1.0.md)，closed-loop superiority NOT CLAIMED，G0 NOT INCLUDED IN V1.0 CLAIM。

| 版本 | 已冻结能力 | 正式基线 |
|---|---|---|
| v0.2 | Deterministic Event Intelligence | PASS |
| v0.3 | Deterministic Response Control | PASS |
| v0.4 | Continuous Verification & Re-plan | PASS |
| v0.5 | AI Decision Brain | PASS |
| v0.6 | Reliability / Security / Real Sensor | PASS / CONTROLLED LAB |
| v0.9 | Competition-ready Product | PASS / CONTROLLED LAB |
| v1.0 | 可安装、可升级、可恢复、可审计的稳定原型 | PASS / STABLE PROTOTYPE |

历史 [v0.9验收](docs/VALIDATION_REPORT_v0.9.0.md) 和 [v0.6验收](docs/VALIDATION_REPORT_v0.6.0.md) 保留为各自版本证据，不自动证明当前版本通过。ai.5 冻结不变，原464后端与15前端测试保留；v1.0 不引入新安全引擎、HA、多租户或桌面客户端。v1.0 全部 Gate PASS 后停止本路线开发。
