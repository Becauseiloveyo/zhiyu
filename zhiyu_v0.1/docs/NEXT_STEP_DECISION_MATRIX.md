# 下一步决策矩阵

日期：2026-10-07。状态：待负责人决定；矩阵不构成实施、DOCX 编辑或比赛交付授权。事实源：[状态基线](PROJECT_STATUS_BASELINE_POST_V1.md)，细节见[维护范围](V1.0.1_MAINTENANCE_SCOPE.md)、[四层路线](POST_V1_PRODUCT_ROADMAP.md)、[比赛计划](COMPETITION_READINESS_PLAN.md)。

## 1. 决策口径

“Must For Stable Prototype?”针对当前受控稳定原型的合格主张，不等于生产要求；“维护须修/验”指若发行 v1.0.1 必须履行新候选出口。比赛前须处置可以是材料披露/操作预演，不一律是代码修改。未来提案的 Target Version 是条件建议，不表示版本已创建。

| Item | Problem | Current Evidence | Must Before Competition? | Must For Stable Prototype? | Can Defer? | Target Version | Risk | Decision |
|---|---|---|---|---|---|---|---|---|
| v1.0.0 PASS | 发行与后走查结论可能混淆 | 491/490/189/15、Gate A–E PASS；走查1失败1未测另列 | YES：正确声明 | YES：保留适用范围 | 不延后真实性说明 | v1.0.0 | 抹掉缺陷或误撤整个发行结论 | 保持 PASS / STABLE PROTOTYPE / CONTROLLED LAB，非全功能无缺陷 |
| v1.0.1 | 有六项有界维护收益 | START/UI/DF1–3/F22 | NO：不是强制换版 | NO：原 PASS 不因候选自动失效 | YES，窗口不足就延期 | v1.0.1 仅推荐 | 修改/构建/复验引回归 | 推荐 YES，先批准范围/窗口，再实施，禁止新功能 |
| START-001 / OPS-START | stopped infra 无法由 start 拉起 | refresh先检查PG/ingress；先恢复infra后正常 | YES：操作合同/安全恢复必须清楚；代码可延期 | YES：须披露先决条件；自动拉起不是既有明确要求 | 诊断代码可延期；操作准备不可忽略 | v1.0.1 方案C | 错启foreign/泄密/现场冷启动失败 | 主类 B；SHOULD FIX预检；MUST DOCUMENT；不自动A/B扩命令 |
| UI-001 / F42 | 四箭头平移失效 | 画布获焦ArrowRight无位移；鼠标160%生效 | NO：可用鼠标，披露限制 | 不撤原PASS；维护候选 MUST FIX | YES，比赛用鼠标 | v1.0.1 | 键盘/焦点/鼠标回归 | 只修四箭头，不重写图/语义/样式 |
| DF-001 | Demo Guide旧Gate E状态 | 现文称未完成；正式已PASS | YES：材料须同步 | YES：如实描述发行 | 不应推迟提交口径；正式文档编辑仍待授权 | 文档维护 | 旧状态导致不可信 | DOCUMENT：Final PASS与走查限制并列 |
| DF-002 | API旧开发阶段 | 开头Gate A实现中、结尾旧阶段 | YES：对外状态同步 | YES：合同不能长期误称开发中 | 文档编辑待授权，材料纠正优先 | 文档维护 | 更新时误改API承诺 | DOCUMENT：状态/链接修正，不改endpoint/schema |
| DF-003 | start/bootstrap/infra混写 | Docker重启后start说明与实现矛盾 | YES：恢复流程/前提 | YES：准确运行契约 | 不能省略现场前提；代码可延期 | 文档维护 | 重装/删卷/旧端口/误启别项目 | DOCUMENT：owned恢复先于API start，分别演练 |
| F22 | 事件真实跨页未验 | 每子环境1条；现UI50条next/首页、后端keyset | NO：不展示已全验；可单事件演示 | 不撤原PASS；维护候选 MUST VERIFY | YES：缺口保持 | v1.0.1 补验 | 污染正式库/跨Scope/cursor失效 | 隔离121条补验next/历史回退/首页/过滤/环境/Scope；不重写分页 |
| 最终计划书状态更新 | 9/28稿仍v0.9PLANNED/v1待完成 | OOXML现状与Final报告对照 | YES：提交材料一致 | NO：材料工作不是新增引擎 | 比赛交付批准前待办 | Track B，无新版本 | 历史事实改写/生产夸大 | 按章节提案派生新版，保留原稿；本轮未编辑 |
| PPT/成果简介/创新/架构 | 工程结果需转成评审可读材料 | 现手册/证据、原五创新 | YES | NO | 依赛事交付日，不能用代码代替材料 | Track B | PPT引入无证据功能 | 基于选定发行，说明自研/第三方、现实/愿景 |
| 5–7/2–3min演示/Q&A | 单一路径/时长/反例解释需收敛 | 现操作卡、A–E、60.2s已安装读路径 | YES | NO | 不延期排练到现场 | Track B | 首次冷安装/新LIVE耗时超预算 | 两套脚本、两轮排练；不把60s当冷安装保证 |
| 现场恢复/LIVE-REPLAY/数据/提交 | 模式/依赖中断会误导现场 | START、API重启、登记回放 | YES | 恢复合同准确；非要求新恢复功能 | 不能忽略；真实破坏注入可后移 | Track B | Replay也依赖API；数据与版本混乱 | owned预检/备用档案/外部预录分支；提交前核对身份与敏感信息 |
| fresh install repeat | 仅已有一次干净安装及影响复验 | RC6 PASS，后续复用非新全装 | NO | NO：已验Reference事实保留 | YES | Track C；v1.1条件 | 网络/源变化/时间投入 | 先预定重复条件/预算，报告失败与方差，不补算历史次数 |
| new-host install | 第二台Linux实体主机未验 | Final明确NOT_RUN | NO | NO：不宣称此支持 | YES | Track C；v1.1条件 | 新权限/平台假兼容 | 取得新宿主后实测，再决定支持范围 |
| real DB service recovery | 当前Reference完整故障链未验 | 已有事务/API故障不覆盖全部DB进程故障 | NO | NO：披露该缺口 | YES | Track C | 数据/审计/未知动作重复 | 仅隔离副本故障，定义恢复目标，不动正式库 |
| corrupted archive recovery | 拒绝测试不是全灾难恢复 | verify_backup负例存在；走查未损坏正式包 | NO | NO：拒绝边界已存在 | YES | Track C | 错误“修复”证据/hash | 副本篡改矩阵与备用有效包恢复，不承诺任意损坏可修 |
| pagination large dataset | 基本跨页不证明容量 | 有界SQL/cursor，无大网页数据实证 | NO | NO | YES | Track C | 资源饱和/弱一致夸大 | F22后按容量目标测，瓶颈证明后再改 |
| Model/Worker probes | 只有UNKNOWN、无实时探针 | queries.health与清单明确未实现 | NO | NO：真实UNKNOWN是正确表现 | YES | Track C；v1.1条件 | 假健康/副作用/泄密 | DEFERRED_TO_FUTURE，先定义运维收益/新鲜度 |
| better bootstrap | 一键冷恢复尚非公开合同 | install/restoration负责infra，start负责API | NO：已有操作路线 | NO：无默认新命令要求 | YES | Track C；v1.1条件 | 更大启动副作用/锁/身份 | 需求成立再评审A或独立infra命令，不用内部DB bootstrap冒充 |
| deployment hardening | Lab暴露与供应链残余风险 | loopback；520CH出现项/241许可证UNKNOWN | 比赛须披露/遵守Lab边界；不必加生产功能 | 受控边界YES；生产强化NO | YES，试点前重新评审 | Track C或更后 | 把Lab风险批准套生产 | 先威胁模型/补丁/许可/身份/TLS需求，不空喊生产可用 |
| 网页审批/风险编辑 | UI只有状态，无管理入口 | 后端绑定/风险控制与browser低权限 | NO | NO | YES | Track D有新治理需求 | 身份/撤权/职责扩张 | SECURITY_BOUNDARY_BY_DESIGN，不纳入维护 |
| 任意目标/命令/payload | UI不提供通用执行 | 固定Scope/Capability/Scenario | NO | NO | 不建设此任意入口 | 无 | 越权/任意副作用 | SECURITY_BOUNDARY_BY_DESIGN；通用任意执行NOT_NEEDED |
| HTML/PDF报告 | 仅网页、JSON/MD草稿 | Reports/下载与清单 | NO | NO | YES | 可选后续需求提案 | 新导出面/审核与数据暴露 | OPTIONAL_PRODUCT_ENHANCEMENT，比赛材料可独立编制，不改核心 |
| 网页DB备份恢复 | 已有管理员CLI，非网页 | release_profile/recovery与指南 | NO | NO：已有受控运维能力 | YES | 无默认版本 | 浏览器扩权/秘密数据 | SECURITY_BOUNDARY_BY_DESIGN，不重复造入口 |
| Assets独立页 | 最小资源事实存在，缺完整台账表面 | Snapshot/Detail/Graph有Resource/State | NO | NO | YES | Track D条件需求 | 资产身份/授权范围扩大 | OPTIONAL_PRODUCT_ENHANCEMENT，先访谈，不补菜单 |
| Threats独立页 | 无情报运营生命周期 | Incident风险/假设已有，OpenCTI未集成 | NO | NO | YES | Track D | 情报投毒/出域/过期 | DEFERRED_TO_FUTURE，有来源/用户任务再评估 |
| Detection独立页 | 无检测配置控制台 | Wazuh/Suricata +记录/健康已存在 | NO | NO | YES | 无默认版本 | 复制第三方功能/扩权 | NOT_NEEDED，规则运营需求另提 |
| Investigation独立页 | 无独立菜单，不代表无研判 | Detail/Decision/Evidence/Timeline/Graph | NO | NO | YES | 无默认版本 | 重复产品表面/范围扩大 | NOT_NEEDED，未来工作区需任务证据 |
| Zeek/OpenCTI/Tetragon-eBPF | 更多证据/情报仍候选 | ai.5/原10.2愿景，无当前必要性证据 | NO | NO | YES | 有界v2条件 | 新采集特权/来源/隐私 | 每源以覆盖缺口与可测收益进入，不算当前缺陷 |
| CALDERA/Atomic/WindowsPool | 场景/平台未扩展 | ai.5设计，当前首场景稳定 | NO | NO | YES | 有界v2条件 | 新执行/凭据/清理边界 | 选一个授权场景，适配/三维验证/重置出口先定义 |
| OT Offline Lab/full twin | 离线专项/环境复制为愿景 | ai.5默认OT被动、V1 twin非目标 | NO | NO | YES | 后续研究 | 生产业务/孪生漂移 | P4研究，真实授权和误差指标先行，不宣传生产控制 |
| Policy-as-Code/WorkloadIdentity | 治理规模需求未证明 | 当前RiskGate/可信operator存在 | NO | NO | YES | v2或后条件 | 新策略/信任根/撤权语义 | 先证明治理收益；不为先进性换架构 |
| DurableWorkflow/EventBus | 当前没有必须更换的瓶颈 | PG耐久任务/Outbox已满足V1 | NO | NO | YES | v2或后条件 | 双队列/重复副作用/secret历史 | 长任务或吞吐瓶颈实证后选择，非全引入 |
| HA/multi-site/multi-tenancy | 无生产合同/多客户证据 | 原冻结V3目标，当前未实现/未验证 | NO | NO | YES | 更后规模阶段 | 故障域/租户隔离/权限/运维 | 不默认合入下一V2；真实需求与RPO/RTO/隔离测试先行 |
| 资产状态/SOC完整表面 | 当前最小状态与研判非全SOC | 原愿景 + 实际页面归位 | NO | NO | YES | v2条件需求 | 更大权限/复杂流程 | 优先真实用户任务和稳定身份，不堆功能 |

## 2. 负责人可选择的后续分支

| 分支 | 需要批准的具体范围 | 批准后先做什么 | 仍不自动开始 |
|---|---|---|---|
| 计划书更新 | 使用最近工程更新版、按章节同步、保留原稿/历史 | 核对状态事实与发行版本，派生DOCX/PDF并渲染验收 | 代码维护、PPT/演示交付 |
| v1.0.1 Maintenance | 仅六项，接受START方案C、隔离补验及复验/回退 | 维护候选与安全边界核对，再最小实现/文档/补验 | 新功能、v1.1/v2、生产部署 |
| Competition Delivery | 选定v1.0或已合格维护版、赛事要求、材料与演练 | 计划书/PPT/脚本与证据口径，再排练/提交检查 | 核心系统变更、主动破坏注入、自动对外提交 |

时间不足优先第三分支使用 v1.0.0；不能没有负责人选择就继续其中任何一个。

## 3. 最终决策摘要

```text
CURRENT_RELEASE = v1.0.0 PASS / STABLE PROTOTYPE
V1_0_1_RECOMMENDED = YES
COMPETITION_CODE_FREEZE = YES
NEXT_MAJOR_DIRECTION = Maintenance decision -> Competition Delivery -> Product Hardening -> V2 Research
```

TOP_5_NEXT_ACTIONS（均为待批准后行动）：

1. 负责人审阅本六份规划，选择下一分支，确认比赛日期/提交要求与最终发行基线。
2. 决定是否允许有界 v1.0.1；若允许，按 START方案C、UI-001、DF-001–003、F22 执行并验收；窗口不足则延期代码维护。
3. 按真实 v1 状态派生计划书更新版，保留历史数据/愿景/未验证范围。
4. 完成比赛 PPT、长短演示、Q&A、数据/恢复/LIVE-REPLAY方案及两轮计时排练，冻结后不加功能。
5. 比赛结束收集用户/部署需求，再批准少数 Track C 验证；满足路线前置条件后才考虑 v1.1/v2。

当前 v1.0.0 保持 PASS：YES。建议 v1.0.1：YES（仅推荐）。比赛前增加新功能：NO。V2 前置条件见[路线 §6](POST_V1_PRODUCT_ROADMAP.md)。完成规划后停止。
