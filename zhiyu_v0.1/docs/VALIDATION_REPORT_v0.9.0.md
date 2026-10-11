# 智御 v0.9.0 Competition-ready Product / Web Console

验收日期：2026-10-04，Asia/Shanghai。

**Milestone: v0.9.0 PASS**

Gate A–E 全部通过，范围为 CONTROLLED LAB。CRC、Manifest、逐文件 SHA256、秘密排除与源码/镜像/构建/包字节对应均通过：[包验证](../artifacts/PACKAGE_VALIDATION_v0.9.0.json)。最终 ZIP SHA256 由包外同名验证文件绑定，避免递归 hash。

## Environment / Version / Frontend Stack

Windows 主机、Docker Linux Engine 29.8.0、Python 3.12.14、PostgreSQL 17.11，工程版本0.9.0。实际安全执行目标仅为本机隔离 Linux Lab；Windows 主机不表示 Windows Sensor 已验证。

沿用已批准 React 19.3.0 / Vite 8.3.1 / Recharts 3.10.1 / cmdk 1.1.1 / Sonner 2.0.8 / Lucide 1.48.0、自有路由、React状态、原项目 Logo、暖米白配色和既定信息架构。没有第二套前端或桌面壳。

## Product Architecture / Gates

canonical state 仍为原 PostgreSQL；产品查询以短只读事务投影，严格 Environment/Scope/字段白名单、HMAC游标、授权快照、大小与并发预算。独立 `zhiyu_product` schema 仅存演示意图、租约、步骤和引用，不复制安全事实。默认无执行 profile；固定 Worker 复用原 Sensor 摄取、TaskGraph、Authorization、Risk、ActionGateway、Verification 与 Re-plan。

| Gate | 结果 | 证据 |
|---|---|---|
| A 数据基础 | PASS | [Gate A](V0.9_GATE_A.md)、[数据审计](V0.9_UI_DATA_AUDIT.md) |
| B 真实工作台 | PASS | [Gate B/C](V0.9_GATE_B_C.md)、最终 Browser E2E |
| C 时间线与图谱 | PASS | 同一快照、时间语义、来源边、有界展开及隔离测试 |
| D 报告与演示 | PASS | [Gate D](V0.9_GATE_D_PROGRESS.md)、A–E实际运行、逐场景重置/清理/回放 |
| E 最终验收 | PASS | 下述测试、Browser E2E、字节对应、最终包报告 |

详见 [架构](DASHBOARD_ARCHITECTURE.md)、[产品 API](API_CONTRACT_v0.9.0.md)。ai.5 Engineering Freeze保持，原72张核心表与 Alembic head `0016_lab_remediation` 未变。

## UI Data Audit / Dashboard / Incident Detail

[当前逐域数据来源与初始 mock 审计](V0.9_UI_DATA_AUDIT.md)并列保存。主要业务数据均从正式 Product API 读取，没有随机数字、合成业务 fallback 或 frontend-only 状态。测试 fixture 和传输故障注入与 LIVE 数据明确分开。

Dashboard 按当前授权范围计算关联事件、Incident、待处理、VERIFYING、UTC日桶和前窗 delta；未定义的综合分数及跨事件通过率显示 Not calculated / N/A。没有活性探测的 Model Runtime/Worker 显示 UNKNOWN。SensorHealth超过有效窗口不继续显示健康，API失败撤下旧数据。

Incident Detail 的摘要、决策、验证、证据、记录覆盖真实 Raw/Normalization/Event/Group/Correlation/Incident、Context/ModelRun、Proposal/Plan、Authorization/Risk、Action/Result、Verification、State/Re-plan。缺失对象、UNKNOWN、过期与未确定最新顺序均保留。

## Timeline / Graph / AI Decision / Authorization / Verification

Timeline 使用来源、接收、入库、观测、创建、执行、验证等实际时间，不补造顺序；按页读取并保留 provenance。图由真实引用构建，OBSERVED/DERIVED/MODEL_INFERENCE/UNKNOWN 分开；所有边不宣称攻击因果。每次最多2层、200节点、400边，无图数据库。

模型 provider/model/revision/模式、ModelRun、Context、证据、latency/token、fallback与提案校验可追溯。自报 confidence 未校准；REFERENCE_GROUNDED不等于语义正确。AI Proposal不等于授权，SHADOW不授予执行权限。

真正改变状态的 Lab Action 仍经原授权、风险与 Gateway；浏览器无任意shell/target/capability/risk override。验证独立区分 SECURITY / BUSINESS / OBSERVATION 及 PASS / FAIL / INCONCLUSIVE，执行成功或模型声称成功不能改写结论。

## Report / Demo Scenarios / LIVE and REPLAY

正式报告含执行摘要、范围方法、证据、时间与原始来源、决策处置、三维验证、状态重规划、限制等八章，来源于同一 Snapshot。JSON与安全转义Markdown可下载；事实hash、报告hash、字节hash分别验证。报告为 UNREVIEWED_DRAFT，不自动发布、签名或关闭事件。

真实A–E均通过，逐场景浏览器 reset/重复运行/cleanup 通过，回放前后业务对象数量不变：[场景证据](../artifacts/v0.9/demo-live-evidence.json)、[重复性](../artifacts/v0.9/demo-browser-repeatability.json)、[页面结果与报告hash](../artifacts/v0.9/demo-browser-content.json)。A真实本地模型分析与SHADOW提案；B脚本无效提案拒绝且Action=0；C停止Sensor得INCONCLUSIVE；D脚本声称成功但独立FAIL并重规划1次；E停止模型后确定性基线继续。B/D不是AI语义质量评估。

旧失败运行保持原错误与UNKNOWN，不重写成PASS。首轮A结构化输出截断导致FALLBACK，不计正常A通过；调整有限上下文/输出预算后重新运行及reset均通过。E执行类别接线和Windows路径转换问题均保留失败证据，并通过新运行验证修复。

Replay的后端/API/页面均标RECORDED_REPLAY，保留原as_of和事实；每次重新鉴权并校验登记文件及hash，不执行模型或安全动作。[5–7分钟与2–3分钟演示脚本](COMPETITION_DEMO_GUIDE.md)、[使用指南](USER_GUIDE_v0.9.0.md)已交付。

## Backend / Frontend / Browser / Security Tests

| 验收 | 结果 |
|---|---|
| 原测试逐项保留 | 381/381原nodeid均在最终JUnit，74个原测试/fixture文件字节不变 |
| 最终主机完整回归 | **464 passed / 0 failed / 0 skipped**，含真实Compose，2834.09秒 |
| 新增产品测试 | 83 passed；读模型/API/分页/Scope/环境/快照/报告/回放/控制器/安全 |
| Linux容器完整非Compose套件 | **463 passed / 0 failed / 0 skipped**，419.242秒；Compose由主机单独执行 |
| 完整Docker runtime | **189 checks PASS**，包含既有运行链与24个本地模型受控评估；容器清理完成 |
| 前端 | 锁文件离线npm ci、lint、全JS/JSX typecheck、15项测试、production build均PASS |
| 静态检查 | 受影响模块Ruff PASS；128个源文件mypy PASS |
| Browser E2E | 正式构建+真实API/PG；页面、A–E、reset/replay、报告、安全/错误/断连通过 |
| 原冻结文件 | 28/28 SHA256一致；无ai.5漂移 |

[测试保留明细](../artifacts/v0.9/final-test-retention.json)、[最终JUnit](../artifacts/v0.9/final-backend.xml)、[Docker结果](m5-runtime/zhiyu-smoke-e73aa9148443/result.json)、[前端结果](../artifacts/v0.9/frontend-checks.json)、[UI E2E报告](UI_E2E_REPORT_v0.9.0.md)。历史失败/中断日志保留但不计入本次通过数。v0.6的A01–A15与182项成绩属于历史版本，不混作这次189项runtime结果。

安全验证包含不可信Sensor/AI/Evidence/Incident文本、XSS/HTML/unsafe Markdown、秘密白名单、跨环境/Scope拒读、撤权、权限/CSRF、直接绕过隐藏按钮、未知副作用不重发、归属清理与回放无副作用。高风险自主执行为0；失败/缺失Sensor保持INCONCLUSIVE。401/403/503等拒绝行为按实际部署身份配置解释。

## Performance / Large Dataset / Accessibility

本机真实API每项10次采样：Overview中位38.151ms，Incident列表23.358ms，详情84.154ms，Timeline28.073ms，Graph25.138ms，Report26.267ms，Health19.816ms。最大响应分别有记录；这些是受控实验室、运行其他验收时的观测，不是SLA：[完整样本](../artifacts/v0.9/api-performance.json)。

真实PG压力数据为10,001个Incident及额外100,000个Event，列表查询只取51行后返回50条与游标：[EXPLAIN](../artifacts/v0.9/incident-query-plan.json)。Timeline 2000条预算、每页50；Graph候选与返回上限、Snapshot 1MiB/2000facts/每类200、Report字节上限和并发预算均有测试。不会把100k Event一次发到浏览器。

1920×1080及1366×768基本可用；键盘导航、2px可见焦点、Ctrl K/Escape、文本状态标签通过。不是完整WCAG或跨浏览器认证；移动端不是本次主要验收目标。

## Architecture Findings / Known Limitations

- 原核心schema测试固定72表；演示元数据显式安装到同一PG的独立schema，未改原迁移/安全真相。
- 无长期Model/Worker活性探针时标UNKNOWN；历史ModelReceipt不替代实时探测。
- Snapshot内存缓存有界、TTL300秒；API重启需重新登录/取快照。回放需保留登记文件与canonical授权/Incident。
- 大事件历史可能截断，报告标注不完整；不提供全量审计链已验证、攻击因果、语义正确或自动人工复核的虚假保证。
- 本地Qwen权重需单独提供，包内不含权重、数据库、凭据。B/D脚本用于确定性安全反例。
- CONTROLLED LAB；Production、客户部署、长期SLA、Cloud、Windows Sensor、OT/ICS均NOT VALIDATED；general AI semantic accuracy NOT PROVEN。

没有引入Kafka、Temporal、Neo4j、第二套事件/状态/审计/验证引擎、任意攻击入口或生产自动修复；不进入v1.0，不新增SBOM或Release Freeze。

## Source Correspondence / Package Validation

[字节对应清单](../artifacts/v0.9/source-correspondence.json)核对workspace Python、最终Lab镜像、实际测试API镜像、测试镜像内安装源码与工具/测试/锁文件；同时绑定frontend输入、package-lock和dist产物。source digest为 `edc309f58d76dad4b6d0ef3bb2982891b4f058bdbfdda9e96a5524d7b5a0f30b`，frontend build digest为 `da3bfd776289f94cb2360f3ec6fd837e56d008100836d3515b6c6a24b849219b`；完整image ID与各锁digest在清单内。

交付ZIP须通过CRC、Manifest、逐文件SHA256、重复/不安全路径、秘密排除、锁文件、frontend dist、源码/报告/截图/回放数据和workspace-image-build-package原始字节对应。最终SHA与验证报告置于ZIP外，避免递归hash。包内清单覆盖每个成员（自身除外）。

**Milestone: v0.9.0 PASS**
