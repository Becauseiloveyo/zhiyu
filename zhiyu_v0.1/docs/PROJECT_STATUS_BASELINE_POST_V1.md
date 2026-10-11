# 智御：v1.0 封版后的项目状态基线

编制日期：2026-10-07。用途：下一次计划书状态同步的事实源。文档状态：待负责人审阅；本轮只读检查与规划，不是新增验收或新版本批准。

## 1. 当前正式结论

| 项目 | 当前事实 | 来源与适用范围 |
|---|---|---|
| CURRENT_RELEASE | v1.0.0 PASS / STABLE PROTOTYPE | [最终验收报告](VALIDATION_REPORT_v1.0.0.md)、[正式状态](../V1.0_STATUS.json) |
| Architecture / Engineering Contract | ai.5 Engineering Freeze | [工程冻结](../../zhiyu_ai5/docs/10_ai5工程冻结与实现入口.md)；原件不改 |
| 验证边界 | CONTROLLED LAB | 自有、教学、隔离、明确授权的固定场景 |
| 开发状态 | 已停止、已封版 | 本轮未开始 v1.0.1、v1.1 或 v2.0 |
| Backend / Linux | 491 PASS / 490 PASS | 两个独立测试口径，不相加为总成绩 |
| Runtime / Frontend | 189 PASS / 15 PASS | 引用最终版本结果，本轮未重跑 |
| Gate A–E | PASS | 安装、历史升级/恢复、供应链与文档、最终发布验收 |
| Demo / Replay / Fault Recovery / Package | PASS | 仅限报告记录的场景、故障与发布环境 |
| Production | NOT VALIDATED | 无生产上线、生产 SLA 或企业全场景支持声明 |
| 高风险自主执行 | 0 | 不把未来高风险审批产品化当当前已实现 |
| 正式 UI / Logo | 现有 Web Console / 原项目 Logo | 维持负责人已确定版本 |

PASS 仍成立于原封版范围；它不等于“每个用户交互均无缺陷”。封版后的走查单独保留失败与未测试结论，不改写原验收，也不能用原 PASS 抹掉新发现。

正式包：[智御_Project_v1.0.0_Stable_Prototype.zip](../artifacts/智御_Project_v1.0.0_Stable_Prototype.zip)，47,842,718 字节，SHA256 `90e85661a0a90e46b789565f52cccaabb497b96d720e39b3c4bac4034bb55868`。RC12 391 个控制文件；后端 source `3525c9d70f7c5b8b38ae9d368671ab7ebba78b1c9b1ba9037904b42e210aa73e`；前端 build `da3bfd776289f94cb2360f3ec6fd837e56d008100836d3515b6c6a24b849219b`；schema head `0016_lab_remediation`。本轮不替换这些身份。

## 2. 事实源与冲突处理

当前实现以 router/navigation/backend 为准，运行结论以所属版本的实测证据为准；正式发行结论读取 v1.0 状态与报告，封版后用户体验读取走查报告。ai.5 描述冻结语义与当时未实现状态，不是今天的进度；旧计划书与历史实施计划的 PLANNED 不覆盖当前 PASS。本文只整理事实，不成为新的架构合同。

本轮已检查以下材料：

- [完整走查](FULL_PRODUCT_WALKTHROUGH_v1.0.0.md)、[63 项清单](FINAL_FUNCTION_INVENTORY_v1.0.0.md)、[用户手册](ZHIYU_USER_MANUAL_v1.0.0.md)、[快速上手](ZHIYU_QUICK_START_v1.0.0.md)、[比赛操作卡](ZHIYU_COMPETITION_OPERATION_CARD_v1.0.0.md)。
- [验收报告](VALIDATION_REPORT_v1.0.0.md)、[证据索引](FINAL_EVIDENCE_INDEX_v1.0.0.md)、[Release Notes](../RELEASE_NOTES_v1.0.0.md)、[安全基线](SECURITY_BASELINE_v1.0.md)、[限制](KNOWN_LIMITATIONS.md)、[AI 最终主张](AI_VALUE_FINAL_POSITION_v1.0.md)。
- [API 合同](API_CONTRACT_v1.0.md)、[演示指南](COMPETITION_DEMO_GUIDE.md)、[安装](INSTALLATION_GUIDE.md)、[部署](DEPLOYMENT_GUIDE.md)、[升级](UPGRADE_GUIDE.md)、[备份恢复](BACKUP_RESTORE_GUIDE.md)。
- [AI 主上下文](../../zhiyu_ai5/智御_AI_CONTEXT_v2026.09.12_ai.5.md)、[冻结入口](../../zhiyu_ai5/docs/10_ai5工程冻结与实现入口.md)、[原始定位](../../zhiyu_ai5/docs/01_项目定位与总体架构.md)、[部署设计](../../zhiyu_ai5/docs/05_部署与能力适配.md)、[验收路线](../../zhiyu_ai5/docs/07_实验验收与路线.md)、[v0.9 历史实施计划](V0.9_IMPLEMENTATION_PLAN.md)及[最终结果](VALIDATION_REPORT_v0.9.0.md)。
- 最初项目计划书、原参赛稿和 2026-09-28 工程状态更新版：见[更新提案](PROJECT_PLAN_UPDATE_PROPOSAL_POST_V1.md)的完整来源路径。通过 DOCX XML 只读提取正文及表格；未改文件、未做版式更新。
- [启动工具](../tools/release_profile.py)全文件、[恢复工具](../tools/release_recovery.py)、[开发 Compose](../docker-compose.yml)、[Reference 配置](../config/reference-profile.json)、[实际页面](../frontend/src/App.jsx)、[图谱](../frontend/src/AnalysisPages.jsx)、[路由](../frontend/src/routing.js)、[后端查询](../src/zhiyu/product/queries.py)、[产品 API](../src/zhiyu/api/routes/product.py)。

`PROJECT_STATE.yaml` 等历史聚合说明含旧阶段计数/待办时，按所属版本理解。此次仅记录漂移，不扩展维护范围去重写全部旧资料。

## 3. 封版后走查的真实结论

| 验收项 | 数量 / 结果 | 解释 |
|---|---|---|
| TOTAL_USER_VISIBLE_FEATURES | 63 | 网页可见功能分母；OPS-START 单列 |
| WORKING | 53 | 包含通过的只读与回放项，并非 53 项都实时执行 |
| WORKING_LAB_ONLY | 8 | 固定 A–E、取消后续步骤、清理、重置 |
| FAILED | 1 | F42 / UI-001 图谱方向键平移 |
| NOT_TESTABLE | 1 | F22 事件列表真实跨页，获准子环境只有一条记录 |
| ALL_USER_VISIBLE_FEATURES_WALKED_THROUGH | NO | 检查入口不等于每项成功执行 |
| ALL_CORE_WORKFLOWS_OPERABLE | NO | 保留启动缺口、键盘失败与分页补验 |
| MANUAL_MATCHES_ACTUAL_PRODUCT | YES | 手册对应现有 UI |
| 负责人签署 | 待审阅 | 这是工具执行的浏览器走查，不能替代人的验收签名 |

功能类型另为 WORKING 22、READ_ONLY 28、UNAVAILABLE 2、WORKING_LAB_ONLY 8、REPLAY_ONLY 3；类型不是另一个验收计数，不能重复累计。63 = 53 + 8 + 1 + 1。

### 正确受控反例

| Scenario | 预期结果 | 可以说明什么 / 不能说明什么 |
|---|---|---|
| A | 受控低风险动作、独立验证 PASS | 真实本地模型分析/规划为 SHADOW；动作仍走确定性授权路径；临时遏制不是根因修复或自动关闭 |
| B | REJECTED | 脚本化非法能力提案在 Proposal 层被拒绝、无 Action；不能写成真实模型幻觉或 Authorization DENY |
| C | INCONCLUSIVE | 真实 Sensor 故障使观测资格不足；不能把 UNKNOWN 当成功 |
| D | FAIL + bounded Re-plan | 脚本声称成功但真实业务检查失败，有限重规划；不是产品失败 |
| E | FALLBACK | 实际模型不可用后确定性基线继续，不能称模型一直健康 |

## 4. 实际产品范围与能力归位

源码 `App.jsx:19–22,65–71`：五个主导航 + 演示、显示偏好；事件详情为独立路由，健康为概览/抽屉面板。

| 用户表面 | 当前实际功能 | 明确限制 |
|---|---|---|
| Overview | 同授权环境/Scope 的事实统计、待关注项、Sensor 摘要 | 不把“待关注=0”解释为环境没有任何事件 |
| Incidents / Incident Detail | 搜索、状态/优先级筛选、50 条列表、详情五标签、关联记录 | 真实跨页未走查；不是任意数据库查询 |
| Timeline | 多来源真实时间、分页、来源检查、缩放 | 时间邻近不证明因果；历史可 PARTIAL |
| Evidence Graph | 有来源字段的节点/边、两层展开、搜索、鼠标拖动/缩放 | 无确认攻击因果；MODEL_INFERENCE 仍是推断；键盘平移失败 |
| Reports | 固定快照、八段报告、JSON/Markdown 下载、hash/provenance | UNREVIEWED DRAFT；没有 HTML/PDF 导出或签名发布 |
| Demo | 固定 A–E 运行意图、状态、取消/清理/重置 | 要求登记 Lab Profile、独立可信 Worker；无任意执行 |
| Display Preferences | 本浏览器侧栏/面板/说明等布局记忆 | 路由名 settings 不等于系统管理、风险或权限编辑 |
| Environment Health Panel | DB 可读状态、Sensor 观测资格、AI 配置模式 | Model / Worker 无实时探针，UNKNOWN 有事实依据 |

已实现核心：双源真实 Suricata/Wazuh 与 provenance；事件压缩/关联/Incident；最小版本化环境状态和 Context；可替换 Model Gateway、分析/提案校验与回退；持久 Task/Outbox/lease/fencing；确定性授权、Action digest/过期/执行重检；幂等、UNKNOWN 核对、仅 owned 资源 TTL/补偿；Security/Business/Observation 三维独立验证；状态回写与 bounded Re-plan；证据、审计、可追溯产品投影。

Lab-only：当前状态变更与固定故障场景不是生产自动响应能力。Replay-only：F57–F59 读取登记封存档案；RECORDED_REPLAY 保留原时间/hash，零新模型调用、零动作。回放可展示部分核心历史，不证明当前服务或 Sensor 在线。

### 未实现能力分类

类别定义：REQUIRED_FOR_V1=冻结验收必需；OPTIONAL_PRODUCT_ENHANCEMENT=可选产品体验；SECURITY_BOUNDARY_BY_DESIGN=当前设计有意不暴露；DEFERRED_TO_FUTURE=需新需求/治理后评估；NOT_NEEDED=无需作为独立功能建设。下面没有证据支持把某个“缺独立页面”升级为 REQUIRED_FOR_V1。

| 未实现项 | 分类 | 已有替代/真实缺口 | 后续决定 |
|---|---|---|---|
| 网页人工审批 / 风险权限编辑 | SECURITY_BOUNDARY_BY_DESIGN | 后端审批绑定/风险拒绝存在；浏览器是低权限读者 + 受限 Demo 意图 | 完整审批治理 UI 需角色、撤权、审批人责任等独立设计，未来评估 |
| 任意目标/命令/payload 执行 | SECURITY_BOUNDARY_BY_DESIGN | 只有登记 Scope/Capability、固定动作 | 通用任意执行入口 NOT_NEEDED；扩大能力也不能绕过授权 |
| HTML/PDF 报告 | OPTIONAL_PRODUCT_ENHANCEMENT | 已有网页报告和 JSON/Markdown；网页可见不等于 HTML 下载 | 确有交付格式需求再定；不纳入 v1.0.1 |
| 网页数据库备份恢复 | SECURITY_BOUNDARY_BY_DESIGN | 可信管理员 CLI、带私密材料的逻辑备份/新空库恢复存在 | 无比赛需求；浏览器管理员扩权需新威胁模型 |
| 独立 Assets 页面 | OPTIONAL_PRODUCT_ENHANCEMENT | Resource/State 在快照、详情、图谱可读；没有独立资产台账/管理页 | 先访谈资产运营需求，不补菜单凑完整 |
| 独立 Threats 页面 | DEFERRED_TO_FUTURE | Incident 风险/来源与模型假设存在；无独立威胁情报生命周期 | OpenCTI/情报来源有需求再评估 |
| 独立 Detection 页面 | NOT_NEEDED | 底层 Wazuh/Suricata 检测、Sensor 健康及记录来源已有 | 不替代检测设备控制台；规则运营若有明确需求再提案 |
| 独立 Investigation 页面 | NOT_NEEDED | 事件详情、决策/证据/记录、时间线/图谱已构成研判工作流 | 无需重复建设同类页面；后续调查工作区属可选增强 |
| Model / Worker 实时健康探针 | DEFERRED_TO_FUTURE | 只有配置/历史 ModelRun、Sensor/能力状态；不是实时 UP/DOWN | Track C 判断运维收益；不得把 UNKNOWN 改成假健康 |

## 5. 已知发现与未测试场景

| Finding | 当前证据 | 处置性质 |
|---|---|---|
| START-001 / OPS-START | PG/ingress 停止时正式 start 报 reference_database_not_running；恢复底层既有服务后 start/status/health/ready 正常 | 主分类 B：documentation/bootstrap contract defect；仍是实际操作缺口，详见[专项设计](V1.0.1_MAINTENANCE_SCOPE.md) |
| UI-001 / F42 | 画布获焦，方向键未平移；160% 下鼠标拖动生效 | 最小 UI 缺陷；不影响图谱事实语义 |
| F22 | 每获准子环境一条事件，下一页不可用 | 验证缺口，不是 pagination 未实现 |
| DF-001 | 演示指南仍称 Gate E 未完成 | 待同步最终 PASS |
| DF-002 | API 合同仍称 Gate A 实现中/旧阶段 | 待同步 v1.0 Final；不改 API |
| DF-003 | 未说明底层 stopped 时的先决条件，且声称 Docker 重启后执行 start | 文档承诺与实现不一致，不能归咎操作员 |

走查 UX-002–005 等过滤残留、读预算 429、术语/长 ID、待关注文案观察保留在原报告；未升级为本次六项维护范围。其重要性由真实用户反馈再判断。

| 场景 | 已有事实 | 尚不能声称 |
|---|---|---|
| Clean Install | RC6 Windows/WSL2/Docker Reference 实测 PASS，1224.25 秒；后续候选影响复验 | 第二台 Linux 实体主机已安装、每个 RC 都重新干净安装、完全离线重建 |
| 数据升级/恢复 | 真实 v0.9 历史导出；74 表摘要保持；三次新空卷恢复；0016→0016 应用升级 | 新 schema 迁移、任意灾难都能恢复 |
| 故障 | 已测事务失败回滚、降级拒绝、API exit73/坏配置恢复、错误 wheel hash 拒绝；已有其他版本 DB/Sensor/Worker 故障证据 | 当前 Reference 的真实 DB service stop/kill 与全链恢复已完成走查 |
| 损坏档案 | 恢复工具有 hash/path/member/schema 拒绝测试；登记回放完整性已验 | 任意损坏档案可修复；物理损坏数据服务恢复已验 |
| F22 / 大数据 | 有 keyset cursor 和绑定过滤/授权的实现与既有测试 | 当前网页真实多页、很大数据量和高并发容量已全验 |
| 独立 invalid EvidenceRef 提案 | 核心拒绝契约/测试存在，固定 UI 无独立输入入口 | 走查实际独立执行了该新场景 |

## 6. Stable Prototype、Production 与未来边界

当前是可安装、可恢复、可审计、可验证、可演示的受控稳定原型。AI 主张为辅助分析/规划（OPTION B）；80 例 G1/G2 是规划层 SHADOW，G2 未执行；G0 NOT INCLUDED IN V1.0 CLAIM；不证明闭环优越性、一般语义准确率或效率提升百分比。

生产、长期 SLA、真实客户部署、Cloud、Windows Sensor、OT/ICS、企业 HA/DR、多租户、多站点、完整数字孪生均未验证或未实现。Linux 容器测试不能代替新 Linux 宿主安装，也不能代替 Windows 目标验证。

供应链剩余风险不能藏在 PASS 后：正式安全报告保留 520 个 Critical/High 告警出现项和 241 个 License UNKNOWN；这是固定受控运行下的工程处置，既不是零漏洞，也不是生产风险批准。参考 [依赖安全复核](DEPENDENCY_SECURITY_REVIEW_v1.0.md)。

Future Scope：更深 Zeek/OpenCTI/eBPF、CALDERA/Atomic、Windows 验证池、OT 离线实验、策略代码化、工作负载身份、耐久工作流、事件总线、HA、多站点/租户、完整资产/状态与 SOC 产品表面。它们不是 v1.0 缺陷；逐项进入条件见[未来路线](POST_V1_PRODUCT_ROADMAP.md)。冻结设计中多站点/HA/多租户属于 V3 规模目标，此次 V2 是后续扩展路线评估桶，不意味着把 V3 全部塞进下一个版本。

## 7. 本轮保全与停止点

仅允许新增本轮六份规划 Markdown。预检查覆盖 14,402 个保护文件，聚合 SHA256 `286723b7fd106acb809560054fcf97f88c22bb5731f93460bd6fe56b1fa94b7b`；六份新文档不计入保护集合。最终须再次比较原集合及正式 ZIP，不用文档检查冒充产品测试。

2026-10-07 最终核对通过：14,402 个保护文件的聚合 SHA256 与预检查完全一致，正式 ZIP SHA256 不变；六份新规划文件、76 个本地链接、六个维护工作包各十个必需字段及表格结构检查通过。仅新增本轮六份文档；未运行产品验收、操作运行服务/数据库、编辑原计划书或改写历史材料。上述结果是文档与文件完整性检查，不是 v1.0.1 实现 PASS。

当前建议：v1.0.0 保持 PASS；v1.0.1 推荐但尚未批准；比赛代码冻结；不新增比赛功能。完成六份文档后停止，等待负责人选择“计划书更新”“Maintenance 实施”或“Competition Delivery”。
