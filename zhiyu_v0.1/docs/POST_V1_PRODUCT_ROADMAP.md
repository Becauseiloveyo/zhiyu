# 智御封版后产品路线：Now / Next / Later / Future

日期：2026-10-07。状态：建议路线，所有新增工作 NOT APPROVED；没有创建 v1.1/v2.0 或实现 v1.0.1。事实源：[当前基线](PROJECT_STATUS_BASELINE_POST_V1.md)，近期缺陷详见[维护范围](V1.0.1_MAINTENANCE_SCOPE.md)。

## 1. 路线原则与版本判断

先整理事实并冻结现有发行，再决定小维护与比赛材料。比赛后先用部署/运维/用户证据选择强化内容，最后才选择少数扩展能力研究。功能名字不构成需求，第三方有功能不等于智御已经集成。

| Track / 时间层 | 工作目的 | 版本建议 | 进入条件 |
|---|---|---|---|
| A / Now | 缺陷、文档错位、缺失验证 | v1.0.1 Maintenance 推荐，尚未批准 | 六项有界范围；可完成复验和回退；比赛窗口允许 |
| B / Next | 已冻结代码上的 Competition Readiness | 材料交付，不默认新产品版本 | 负责人选择发行基线、批准交付；确认赛事时间/格式 |
| C / Later | 比赛后 Product Hardening | v1.1 仅条件建议，也可先独立验证 | 已收集部署/用户问题、确认预算与明确需求集合 |
| D / Future | 扩展产品与研究 | v2.0 仅有界扩展提案；规模治理可继续后移至原 V3 阶段 | 真实试点/授权、价值证据、团队能力、安全与可测试边界 |

顺序建议：**Maintenance 决策 → Competition Delivery → Product Hardening → V2 Research**。如果比赛窗口不足，Maintenance 代码延期，Competition 使用 v1.0.0；不能为了顺序强行换版本。

优先级统一：P0=Release/usability blocker，P1=Competition/important reliability，P2=Product hardening，P3=Future enhancement，P4=Research/optional。当前没有证据判定原受控发行必须撤销 PASS 的 P0；若将 stopped 全栈冷启动定为强制现场路径而无法恢复，它可成为该场比赛的 P0 操作阻断，不由此改写所有历史验收。

Engineering cost 使用相对估计：L=局部且边界清楚，M=跨运行/数据/环境验证，H=新增适配或治理，XL=系统级长期建设。不是工期承诺；负责人资源、现场日期和新需求未知，不能伪造排期。

Evidence 简写：S=[状态基线](PROJECT_STATUS_BASELINE_POST_V1.md)，W=[走查](FULL_PRODUCT_WALKTHROUGH_v1.0.0.md)，R=[正式报告](VALIDATION_REPORT_v1.0.0.md)，F=[冻结部署/能力设计](../../zhiyu_ai5/docs/05_部署与能力适配.md)，V=[原愿景/计划章节对照](PROJECT_PLAN_UPDATE_PROPOSAL_POST_V1.md)，M=[维护专项](V1.0.1_MAINTENANCE_SCOPE.md)。未来行的证据通常只是设计依据/缺口观察，并非已经证明产品需求。

## 2. Now — Track A，有界维护候选

下表每行均给出 Problem、Why it matters、User value、Engineering cost、Security impact、Evidence、Dependency、Priority、Recommended release、Exit criteria。Exit 是未来验收条件，不是本轮已经完成。

| Item / Problem | Why it matters | User value | Engineering cost | Security impact | Evidence | Dependency | Priority | Recommended release | Exit criteria |
|---|---|---|---|---|---|---|---|---|---|
| START-001：stopped infra 使 start 失败 | 现场误判 API 无法恢复 | 明确诊断、可安全恢复 | L–M：方案 C 与副本演练 | 不启 foreign 服务、不泄密、不增自动副作用 | W + release_profile 顺序，M §2 | 负责人接受 API-start 契约；owned metadata | P1 | v1.0.1 候选；无授权不改 | stopped/missing/foreign 分开；合法路径 ready；恢复说明实测，无历史变化 |
| UI-001/F42：方向键无平移 | 已承诺键盘路径失效 | 键盘可浏览图谱 | L：局部事件处理+真浏览器 | 不改事实/图语义/节点操作 | W ArrowRight；M M-02 | 已有可滚动图和焦点 | P1 | v1.0.1 候选 | 四方向、焦点/边界、鼠标/缩放/窄屏全通过 |
| DF-001：演示指南旧 Gate E 状态 | 材料与封版冲突 | 可信演示说明 | L：状态段/链接 | 保留受控反例与未验证边界 | 正式指南首段；R | 已冻结 v1.0 状态 | P1 | 维护文档 / 独立材料同步 | Final PASS 与走查 NO 并存，链接/来源正确 |
| DF-002：API 合同旧开发阶段 | 用户难判断接口稳定状态 | 准确接口说明 | L：状态文字比对 | 不改 endpoint/权限/错误语义 | 合同首尾；R | 实际 router/DTO | P1 | 维护文档 | Final 状态正确，接口定义无新增能力 |
| DF-003：启动先决条件缺失 | Docker 重启后按文档失败 | 安全、可执行操作步骤 | L–M：跨指南/演练 | 禁止任意容器启动、重装/删卷捷径 | DEPLOYMENT §25；W；M | START-001 C 契约、可信 operator | P1 | 维护文档 / 比赛操作附注 | install/DB bootstrap/API start/infra/restore 分清；owned 恢复可复现 |
| F22：真实列表跨页未验 | 单条数据掩盖交互/隔离错误 | 相信现有分页 | M：隔离数据与网页补验 | 不污染正式 DB/evidence；cursor 隔离 | W；App limit50；queries keyset | 新副本/121 条可见与不可见对照 | P1 | v1.0.1 验证候选 | next/历史回退/首页/过期/过滤/环境/Scope 通过，不新增 previous 按钮 |

## 3. Next — Track B，代码冻结后的比赛交付

| Item / Problem | Why it matters | User value | Engineering cost | Security impact | Evidence | Dependency | Priority | Recommended release | Exit criteria |
|---|---|---|---|---|---|---|---|---|---|
| Competition Delivery：当前材料滞后、现场路径未最终签署 | 工程成绩不能自动转成可答辩材料 | 清楚理解价值、证据和边界 | M：计划书/PPT/脚本/Q&A/演练/校验 | 脱敏、不把 Replay 冒充 LIVE、不改核心追求效果 | S、V；现有操作卡/手册 | 发行版本确认；赛事要求；负责人授权与签署 | P1 | 无新增产品版本 | 完成计划书、PPT、5–7/2–3 分钟演示、Q&A、恢复与模式切换、数据、简介/创新/架构、提交检查；两轮计时演练、内容可溯源 |

具体交付项、角色、顺序、冻结和模式切换见[Competition Readiness Plan](COMPETITION_READINESS_PLAN.md)。本轮只规划，不自动生成 PPT/新视频/新计划书。

## 4. Later — Track C，比赛后先证明收益

| Item / Problem | Why it matters | User value | Engineering cost | Security impact | Evidence | Dependency | Priority | Recommended release | Exit criteria |
|---|---|---|---|---|---|---|---|---|---|
| 重复 fresh install：已有一次干净安装及影响承接，缺重复统计 | 网络/软件源/构建可重复性仍有波动 | 少依赖维护者经验 | M：多次空环境与锁定制品 | 固定 hash/来源，不自动升级/降 TLS | R RC6 1224.25s；后续非重复干净安装 | 安装资源/预算、独立部署 | P2 | 先验证；有维护价值才并入 v1.1 提案 | 批准次数预先固定，成功/失败/时长逐次报告；各层无缓存复用界定清楚 |
| new-host install：第二台 Linux 实体主机 NOT_RUN | 容器回归不能证明新宿主交付 | 明确支持矩阵 | H：宿主差异/操作员环境 | 新平台权限/端口/隔离再评估 | R；INSTALLATION_GUIDE | 第二台授权主机与平台范围 | P2 | v1.1 条件候选或独立验证，不纳入 v1.0.1 | 新空目录/卷与固定身份跑通安装、场景、清理；失败保留；支持声明只到实测平台 |
| 真实 DB service failure recovery：当前 Reference 未走查此链 | 事务失败/API故障不等于 DB 进程失效恢复 | 数据不丢、动作不重复 | M–H：隔离副本故障矩阵 | 禁正式库注入；durable intent/审计/UNKNOWN 不破坏 | R 故障类别；W 未测表 | 可丢弃副本、备份与有界注入批准 | P2 | v1.1 条件验证 | 明确 stop/kill/连接中断条件；health/ready、Worker核对、74表/审计/副作用完整性、恢复时长实测 |
| corrupted archive recovery：已有拒绝测试，未广泛运行演练 | 防止操作员把损坏包当可恢复 | 明确拒绝/备用档案路线 | M：篡改矩阵/副本恢复 | 验证先于服务/DB变更；不“修补”事实 hash | tests/test_release_profile；W | 备份副本、隔离恢复环境 | P2 | v1.1 条件验证 | 截断/CRC/hash/重复路径/版本缺失均安全拒绝；有效备份独立恢复；不得声称任意损坏可修复 |
| pagination large dataset：F22 仅基本交互补验 | 产品增长后延迟/资源预算可能变差 | 大列表仍有界且隔离 | M：规模/并发/query plan | 读预算与 scope不可绕过；不污染证据 | queries limit+keyset；S | F22完成、预定规模/并发与容量目标 | P2 | v1.1 条件候选 | 报数据量、索引计划、延迟分布/429/预算；正确性与弱一致性分开；瓶颈才改实现 |
| Model/Worker health probe：面板 UNKNOWN | 配置 OFF/历史调用不是实时在线状态 | 定位故障，减少误操作 | M：探针/新鲜度/访问控制 | 探针无动作/模型副作用，不泄密；不能把无观测改绿 | S；queries.health无此探针 | 明确运维任务、状态定义/超时/权限 | P2 | v1.1 有需求才提案 | OFF/STARTING/UNKNOWN/STALE/DOWN 等口径审定；真实停止/恢复、误报/撤权测试通过 |
| better operator bootstrap：当前 start 需 infra运行 | 若用户确需冷启动，文档方案不足 | 减少部署/恢复步骤 | M–H：A或独立infra命令评审 | 严格 owned project/service/image/network/volume；协调锁；不自动扩权 | START-001 B+C结论；F | 六项维护结束；一键恢复需求与安全评审 | P2 | v1.1 条件行为需求 | 启动契约明确；全 stopped/partial/foreign/port/锁失败矩阵通过；无新卷、无隐式Worker/Lab启动 |
| deployment hardening：当前 loopback/Lab，仍有漏洞/许可未知 | 进入试点会改变威胁与暴露面 | 可评估的交付风险 | H：按需求TLS/身份/秘密/补丁/备份 | 先威胁模型/可达性与责任人；不能沿用Lab风险批准 | 安全基线、520 CH出现项/241 License UNKNOWN | 具体试点/暴露方式、补丁兼容性、许可复核 | P2 | v1.1 或更后，范围批准后再定 | 支持矩阵/残余风险签署、秘密/权限/补丁回归与恢复目标实测；不空喊Production ready |

Track C 收益判断：重复安装/新宿主提高交付可重复性，DB/档案演练补恢复证据，分页补容量证据，探针/启动改善操作，部署强化支持受控试点。需要有用户/部署需求才变成产品版本；纯验证可以单独产证据。不得为凑 v1.1 一次性承诺八项全部实施。

## 5. Future — Track D，原愿景的有界扩展候选

下列均不是当前 v1.0 缺陷；当前只有设计/愿景依据，需求收益待证明。保留 ai.5 安全不变量，新增组件须解决明确缺口，优先替换重复职责，避免叠加。

| Item / Problem | Why it matters | User value | Engineering cost | Security impact | Evidence | Dependency | Priority | Recommended release | Exit criteria |
|---|---|---|---|---|---|---|---|---|---|
| Zeek deeper integration：缺某类网络证据时才引 | 更多来源不等于独立血缘 | 补具体观测盲区 | H：解析/身份/关联 | 抓包范围、隐私、provenance重复检查 | F、V；现仅Suricata/Wazuh | 具体协议/场景缺口、样本与标注 | P3 | 有界 v2 候选 | 新增证据确实改善覆盖；映射、误关联、范围与故障验证 |
| OpenCTI：当前无完整情报运营 | 情报需来源/时效治理 | 辅助研判并可追溯 | H：情报同步/映射 | 许可、出域、投毒与撤回；不得直接授权动作 | V §10.2；S Threats缺独立生命周期 | 情报用户任务/可靠来源/数据政策 | P3 | v2 候选或更后 | 事实/情报/推断分清；失效/冲突/撤回可测；同任务收益证明 |
| Tetragon / eBPF：端点/K8s观测缺口 | 网络证据不覆盖所有宿主行为 | 具体工作负载可见性 | H：内核/平台矩阵 | 特权采集与隐私、性能/失效影响 | F 跨平台设计 | 授权Linux/K8s、实际内核兼容测试 | P3 | v2 候选 | 一个明确平台/场景闭环，覆盖收益/丢失/开销/范围实测 |
| CALDERA / Atomic expansion：固定首场景覆盖有限 | 需要端点动作/可重复新场景时有用 | 授权复测模板 | H：allowlist与cleanup适配 | 固定 ability/测试版本、执行位置/Scope/TTL | F 能力角色；V | 每场景批准、目标/执行器与恢复责任 | P3 | v2 有界场景 | 已登记操作，拒绝越界/未知动作，无残留，可独立三维验证 |
| Strix深度集成：固定工具不满足复杂验证时才评估 | 复杂Executor也不能扩大自主边界 | 完成具体授权验证任务 | H：受控子任务/适配/核对 | 子任务Scope/权限/预算受控，独立验证/清理 | F可选Executor；V；当前无必要性实证 | 明确复杂任务缺口、可隔离执行环境 | P4 | 研究提案，非自动新Agent | 固定任务收益实证；越界/无限子任务拒绝，动作核对/清理与三维验证通过 |
| Windows Validation Pool：未验Windows专项 | Linux容器不代表Windows目标 | Windows场景的明确支持 | H：VM/身份/快照 | 凭据、AD业务影响、隔离/许可 | F Windows/AD设计；S未验 | 合法授权VM、权限/镜像/资源、单场景 | P3 | v2 候选 | 实际Windows目标从采集到清理复现；支持范围/版本明确 |
| OT Offline Lab：生产主动测试高风险 | 不能直接搬IT自治策略 | 保守的离线研究验证 | XL：协议/厂商/孪生 | 生产OBSERVE_ONLY；禁止越界主动执行 | F OT设计；S未验 | 厂商认可/授权离线环境、专家/资源 | P4 | 研究提案，更后专项 | 离线隔离/只读边界与目标有效性评审；不宣传生产OT控制 |
| Policy-as-Code：规则治理规模增长后评估 | 更换引擎不是创新 | 可审计策略演进 | H：语义兼容/回滚 | 所有入口仍强制授权；策略签署/撤销 | F；现有确定性RiskGate | 策略团队/变更数量/治理痛点 | P3 | v2条件；无需求保留现状 | 与原决策集差异解释/批准；fail closed、执行重检、旧授权失效通过 |
| Workload Identity：跨服务/站点身份治理 | 服务增多后静态秘密难管理 | 最小权限与可撤身份 | H：证书/引导/轮换 | 信任根、撤销、离线缓存/短凭据 | F SPIFFE类候选 | 明确服务边界、身份责任与可用性需求 | P3 | v2或后续治理 | 真实轮换/撤销/伪装拒绝；secret不入模型；失效安全 |
| Durable Workflow：跨天/审批恢复复杂 | 当前PG耐久任务已满足V1 | 长任务可恢复 | H：迁移/幂等/历史策略 | 不持久化secret；动作UNKNOWN先核对 | F；现Task/Outbox/lease | 已证明长任务复杂度/恢复瓶颈 | P3 | v2条件，不默认替换 | 同任务收益、崩溃/重试/升级/取消测试，无重复副作用 |
| Event Bus：吞吐/重放瓶颈出现后评估 | 不为先进性加第二套队列 | 更大遥测量有界处理 | H：顺序/耐久/背压 | 身份/租户隔离、丢失显式、审计intent保留 | F；目前未证明必须引入 | 实测瓶颈/容量目标、运维能力 | P3 | v2或后，测量后定 | 固定负载收益与故障/重复/排序/重放验证，不拿无持久PubSub当耐久流 |
| HA：单机不满足明确可用性目标时评估 | 节点多不自动HA | 可量化故障恢复 | XL：PG/故障域/运维 | split-brain/fencing、RPO/RTO、凭据恢复 | F原V3；S无生产SLA | 试点可用性合同、值守预算 | P3 | 后续规模阶段，原V3；非默认下一V2 | 真故障切换与RPO/RTO实测，无重复动作/数据丢失声明漂移 |
| multi-site：站点边界与离线需求 | 中心连通不能假设一直有效 | 分域授权与本地恢复 | XL：站点网关/同步 | 数据驻留、断连授权期限、站点ownership | F原V3设计 | 两个实际授权站点与需求 | P3 | 后续规模阶段 | 跨站点隔离/断连/策略撤销/证据同步复现，禁止越域补偿 |
| multi-tenancy：多客户隔离 | Environment读隔离不等于租户产品 | 可安全服务多个客户 | XL：身份/存储/密钥/配额 | 全链租户隔离与管理员边界 | F原V3；V SOC愿景 | 真实MSSP需求/独立威胁模型/运维团队 | P3 | 后续规模阶段，非v1.1 | 跨租户全链负例、密钥/证据/日志/备份隔离、撤权审查 |
| full digital twin：环境复制与漂移仍是愿景 | 模拟结果不能自证真实防御 | 有边界的离线复测 | XL：模型/同步/校准 | 禁孪生成功自动授权生产；敏感资产复制受控 | 最初计划§6.2；F non-goal | 小范围场景、可校准真实对照/漂移指标 | P4 | 研究，不承诺整套V2 | 误差/漂移/失败边界可测；明示模拟与真实验证差异 |
| stronger asset/state model：最小状态非完整台账 | 产品研判需稳定身份与时态关系 | 减少IP重用/过期关系误判 | H：版本/来源/查询 | FACT/INFERENCE分离；授权读主状态不读旧投影 | V EnvironmentState；现ResourceRef | 明确资产任务/真实样本和生命周期 | P3 | v2优先候选（有需求） | 地址更换/关系失效/冲突/freshness测试，支持实际任务并有收益 |
| 更完整 SOC product surface：缺角色化运营表面 | 独立菜单不等于用户价值 | 调查/资产/情报/审批等任务完成率 | H–XL：流程/角色/界面 | 审批/权限编辑属新安全表面；不能任意执行 | S能力分类；V愿景 | 用户访谈、任务原型、角色/审计/撤权合同 | P3 | v2或后，逐工作流批准 | 小范围用户任务验证；新权限全链测试；不重复Incidents/Timeline/Graph |

Strix 深度集成仍为可选受控 Executor 研究：当前无证据证明固定工具不能完成已批准目标。若将来选入，必须单列复杂验证任务、子任务/预算/Scope 限制和独立验证，按 P4 研究而非自动新增 Agent；不把参考项目当现有运行时。

## 6. v1.1 / v2.0 的正式进入条件

v1.1 值得提案的最低集合：比赛交付结束；至少有真实部署/用户反馈支撑的一组可靠性需求；每项有失效场景、收益、验收和负责人；资源可支撑兼容/安装/恢复回归。优先从操作启动、运行健康、安装重复性中选择有需求的少数项；不能因候选清单存在就建立 v1.1。

v2.0 只有以下前置条件全部满足才值得开始：

1. v1 基线与遗留缺陷处置已签署；比赛后维护/交付结束，有可回退发行与独立证据。
2. 至少一个明确用户/试点场景与合法授权，证明 v1 的真实能力缺口；没有客户不能虚构需求。
3. 收敛成少数可测需求，例如一个新证据源或一个 Windows 场景 + 必要状态增强，不把全部原 V2/V3 愿景一次合并。
4. 需求价值能用固定数据、任务成功/覆盖/恢复/成本指标验证；新 AI 收益有独立评价，不靠 Demo 或模型自评分。
5. 团队、硬件、预算、维护责任与时间明确，能够承担新增平台/组件的运维。
6. 新威胁模型、身份/Scope/数据出域/审批/秘密/补偿/供应链边界通过审查；ai.5 变化有实现或安全证据与明确决策。
7. 支持矩阵、兼容/迁移/恢复/故障负例和退出条件在开发前定义，保留原版本与证据。

原始愿景的完成/安全收敛/后移/取消证据见[计划提案 §5](PROJECT_PLAN_UPDATE_PROPOSAL_POST_V1.md)。没有取消决定的核心目标不写“已取消”；明确不受限执行等 non-goal 不重新排入功能路线。

## 7. 比赛前停止点与风险

**COMPETITION_CODE_FREEZE = YES。COMPETITION_CODE_FREEZE_POINT = 当前 v1.0.0；若经批准且验收通过的 v1.0.1 替换，则在维护签署后立即重新冻结。** 无比赛截止日信息，使用审批/验收事件设停止点，不推定可用开发窗口。

| 选择 / 风险 | 可能影响 | 控制与决策 |
|---|---|---|
| 修 v1.0.1 的 regression risk | start诊断影响安装/恢复调用，键盘事件影响焦点/鼠标，构建身份改变 | 六项白名单、隔离副本、实际浏览器/正式回归、独立候选与旧v1回退；失败不发布 |
| 不修 START-001 的操作风险 | Docker/infra停止后按旧指南失败，现场来不及恢复 | 文档附注+owned恢复预演；比赛前基础服务检查；明确Replay也需要API，API不能恢复时用外部预录材料 |
| 不修 UI-001 的比赛影响 | 纯键盘展示失败，可访问性承诺不完整 | 已验证鼠标拖动/缩放可替代；公开限制；不以鼠标成功改写键盘失败 |
| 比赛前继续加功能的 scope risk | 新权限/依赖/数据/演示流程破坏稳定基线，验证窗口不足 | 不加功能；材料用既有事实；新需求去Track C/D，逐项批准 |

本轮到文档止步。后续任何轨道均需负责人明确选择与授权，不能由本路线自动触发。
