# 智御 v1.0.0 · Stable Prototype / Final Release Freeze

v1.0.0 PASS / STABLE PROTOTYPE

智御是网络安全自主决策与持续验证平台，采用Linux-native Control Plane + Browser Web Console，将已验证安全核心收敛成可安装、可升级、可备份恢复、可追溯和可演示的稳定原型。v1.0未新增核心产品能力或改变批准UI/原Logo。

## Version history

v0.2确定性事件智能；v0.3确定性响应控制；v0.4持续验证与有限重规划；v0.5 AI决策辅助；v0.6可靠性/安全/真实Sensor；v0.9比赛产品；v1.0稳定原型最终冻结。

## v1.0 additions

最小Reference配置/secret bootstrap/哈希依赖取得/受限loopback ingress；完整历史备份/新空环境恢复/安全升级与故障处理；操作员日志脱敏与无关Sensor解析器限制；27项新增发布工具测试、文档、安全库存、SBOM/License与逐漏洞处置。原464项测试全部保留。

## Deployment, install and upgrade

正式Profile：Windows + WSL2 + Docker Desktop Linux Containers + 浏览器。第二台Linux实体主机NOT_RUN。[安装](docs/INSTALLATION_GUIDE.md)、[部署](docs/DEPLOYMENT_GUIDE.md)、[升级](docs/UPGRADE_GUIDE.md)、[备份恢复](docs/BACKUP_RESTORE_GUIDE.md)。外部模型权重/真实密钥/备份/venv/node_modules/数据库不在发布包中。首次安装需取得固定依赖/镜像/经许可模型，不宣称全离线或一键。

## Validation

491 host /490 Linux /189 Docker checks /15 frontend全部通过，0失败/0跳过；A–E、reset/cleanup/replay、10份回放报告与真实API/Sensor故障恢复通过。ai.5/16迁移/83原测试fixture字节不变。完整记录见 [Validation](docs/VALIDATION_REPORT_v1.0.0.md) 与 [Evidence Index](docs/FINAL_EVIDENCE_INDEX_v1.0.0.md)。

## Security and AI behavior

CONTROLLED LAB，Production/customer/SLA NOT VALIDATED，HA/多租户未实现。520个第三方Critical/High告警出现项有明确处置与未补丁运行剩余风险，仅可信固定隔离Lab可沿用结论。[Security](docs/SECURITY_BASELINE_v1.0.md)、[limitations](docs/KNOWN_LIMITATIONS.md)。AI默认OFF/启用默认SHADOW，高风险自主执行0；Proposal不等于Authorization，独立验证不把执行成功当安全成功。OPTION B：辅助分析/规划/建议；closed-loop superiority NOT CLAIMED；G0 NOT INCLUDED。

## Demo and final freeze

A真实Sensor/本地模型闭环；B无效提案拒绝；C观测不足INCONCLUSIVE；D独立业务验证FAIL；E模型不可用FALLBACK。B/D明确SCRIPTED_NOT_AI。[演示指南](docs/COMPETITION_DEMO_GUIDE.md)。本版完成后停止，不自动推进v1.1/v2或新增Agent/Sensor；后续增强须重新批准。
