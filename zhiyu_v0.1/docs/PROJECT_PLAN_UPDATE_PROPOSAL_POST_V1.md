# 计划书封版后状态同步提案

日期：2026-10-07。状态：PROPOSED / NOT APPROVED。本轮不编辑 DOCX/PDF、不重写原稿、不改历史证据。下一次获得“计划书更新”授权后，以[状态基线](PROJECT_STATUS_BASELINE_POST_V1.md)逐章同步。

## 1. 原稿与更新对象

| 来源 | 完整路径 | 用途 |
|---|---|---|
| 最初项目计划书 | `C:\Users\wc\Downloads\Compressed\智御_网络安全自主决策与持续验证平台_项目计划书.docx` | 原始构想、用户价值、初期时间路线与真实性约束；不能把原假设写成已取得成果 |
| 原正式参赛稿 | `C:\Users\wc\Downloads\智御-网络安全自主决策与持续验证平台-参赛项目计划书（排版优化版） (1).docx` | v2026.09 章节结构、v0.2–v1.0 路线、概念完整版候选 |
| 最近工程状态更新版 | `C:\Users\wc\Documents\ChatGPT\创新创业大赛\artifacts\plan-update-20260928\智御-网络安全自主决策与持续验证平台-参赛项目计划书_v2026.09_工程状态更新版.docx` | 推荐的下一次编辑起点；保留排版与结构，仅增量更新状态 |
| 上次修改说明 | [PLAN_UPDATE_CHANGELOG](../../artifacts/plan-update-20260928/PLAN_UPDATE_CHANGELOG.md)、[PLAN_UPDATE_VALIDATION](../../artifacts/plan-update-20260928/PLAN_UPDATE_VALIDATION.md) | 区分上次同步与本次新增事实 |

此次通过 OOXML 读取文字与表格。下表段落号是当前更新版 `word/document.xml` 中所有 `w:p` 的顺序号，包含表格单元格，不是 Word 页码；下次应按标题定位，不能靠旧目录页码硬替换。

最初稿第 10.1/10.2 节还是创意/原型搭建与按月份的假设路线；2026-09-28 更新版已前进到 v0.6 PASS，但仍把 v0.9 写为 PLANNED、v1.0 写为待完成。应补新状态，不能把 9 月 28 日当时的叙述伪造为当时就已 v1.0 PASS。

## 2. 更新后的主叙述（建议稿，不是已写回）

截至 2026-10-05，智御保持 ai.5 Engineering Freeze，v0.9 Competition-ready Product 和 v1.0.0 Stable Prototype 已完成受控工程验收；当前正式版本为 v1.0.0 PASS / STABLE PROTOTYPE，开发停止并封版。Backend 491、Linux 490、Runtime 189、Frontend 15 分属各自测试口径，Gate A–E、Demo/Replay/Fault Recovery 与包校验 PASS，边界为 CONTROLLED LAB，Production NOT VALIDATED。

封版后工具辅助浏览器走查覆盖 63 个可见功能：53 项通过（含只读/回放）、8 项 Lab-only 通过、1 项失败、1 项未能测试；另有 START-001 操作缺口及 DF-001–003 文档错位。正式发行 PASS 与走查缺陷同时披露，负责人审阅仍待完成。下一步先决定有界维护及比赛交付，未来产品强化和完整版研究须另行立项。

## 3. 逐章更新清单

| 章节 / 定位 | 当前不再适用的文字 | 建议同步内容 | 依据 / 保留规则 |
|---|---|---|---|
| 封面、提交说明与真实性声明（14、17、19） | 更新于 2026-09-28；v0.9 未 Implement/UI 待设计 | 新更新日期；当前版本/停止开发、真实 UI 与封版事实；明确本次材料更新不产生工程验收 | 状态基线 §1–3；原 9 月 28 日版另存，不覆盖历史 |
| 一、摘要“当前研发阶段”（55） | v0.6 当前，v0.9 PLANNED | v1.0.0 Stable Prototype，CONTROLLED LAB；Maintenance 仅提案 | V1.0_STATUS/最终报告；不是企业已商用 |
| 三、产品边界与用户环境 | 企业、SOC、Cloud、Windows/OT 完整版描述可能与当前混读 | 分开“已验证 Reference/Lab”和“未来适配/生产目标”；显示偏好不称后台 Settings | 实际 router/能力分类；不删除长期定位 |
| 四、总体架构与流程 | 架构设计正确，但容易将全部平面/未来组件当当前部署 | 保持八层/五平面、PG canonical、模块化单体；补现有 Web Console 与可信 operator/Worker 边界 | ai.5 不改；概念图标注设计层，另图注明实际实现 |
| 五、5.2/5.3 环境状态、AI | 完整状态模型愿景与实际最小状态混写 | 最小状态、来源/有效期/事实推断分离已实现；AI 辅助分析/规划、default OFF/enabled SHADOW | 不宣称 full digital twin 或普遍语义准确 |
| 五、5.4 编排 / 5.5 能力 | Durable Workflow/Event Bus、Strix/CALDERA 等候选容易被读成集成 | 现有 PG task/outbox/lease 与固定真实 Capability；第三方候选标“未来/未适配” | 不把组件 upstream 支持归为智御完成 |
| 五、5.6 风险与凭据 | Approval 设计容易暗示网页审批已可用 | 后端精确绑定/过期/重检成立；无浏览器审批或风险权限编辑；仅固定 Lab 状态动作 | 不让状态标签冒充审批管理产品 |
| 五、5.8 安全/SBOM（193）及十二、12.1（486） | SBOM generation + validation 尚未完成 | 正式 CycloneDX1.6 已生成/schema 验证、实际 license/漏洞处置已记录；同时披露剩余风险 | 1629 组件、241 License UNKNOWN、520 Critical/High 告警出现项；不是零漏洞/法律认证 |
| 七、7.1 里程碑/7.2 当前工程（281） | 当前 v0.6 RC7 | 增 v0.9 完成、v1.0 RC12 封版；具体安装、历史升级/新空库恢复、故障与发行证据 | 保留 v0.2–v0.6 原测试数字和环境，不倒填新成绩 |
| 七、7.3 历史性能表 | 合成吞吐/短 soak 可能被当今日 SLA | 保持原表、加版本/数据规模/合成或受控标签；当前验收计数单列 | 不把旧 soak 当多日生产可靠性，不相加跨版本测试 |
| 七、新增“封版后完整走查”小节 | 现版无该记录 | 63=53+8+1+1；OPS-START 单列，UI-001/F22/DF 明确，负责人未签署 | 走查附加事实，不修改 Final Validation Report |
| 八、8.1 演示（328、345–346） | Dashboard/Timeline/Graph/Report 尚未实现；“PASS 才允许关闭”易简化过度 | 现有七导航/详情/健康；A–E 真实路径及 LIVE/REPLAY；独立 PASS 仍受 objective/TTL/残余风险约束，遏制不自动修复/关闭 | 时间线/图谱非因果；报告仅 JSON/MD 未复核草稿；受控反例是成功的安全控制 |
| 八、8.2 AI 增量（349–350） | v1.0 前仍需在 OPTION A/B 间决定 | 最终已选择 OPTION B；80 例规划层 SHADOW，G2 未执行；G0 不纳入 v1.0 主张，闭环优势未证明 | [AI 最终定位](AI_VALUE_FINAL_POSITION_v1.0.md)；不把演示当严格对照实验 |
| 十、10.1 版本路线（427–450） | v0.9 PLANNED/v1.0 待完成 | v0.9 PASS、v1.0 PASS/冻结；v1.0.1 仅推荐维护候选；比赛交付不等于新版本 | A01–A15 v0.6 前移历史保留；v1.0 影响复验另列 |
| 十、10.2 Future Development | 将未来组件一次性列出 | 按 Track C/D、需求/证据/安全/成本进入条件组织；v1.1/v2 仅条件建议，原 V3 规模能力可继续后移 | 不默认全实现，不自动创建版本 |
| 十、新增 Competition Readiness | 尚无封版后材料交付顺序/停止点 | 计划书、PPT、长短演示、Q&A、恢复/模式切换、数据、提交；代码冻结点与时间不足保留 v1.0 方案 | [比赛交付计划](COMPETITION_READINESS_PLAN.md)；此轮只提案 |
| 十一、团队/知识产权；九/十三、市场财务 | 个别假设可能被当新成果 | 只更新负责人提供且有凭证的新事实；没有新调查/客户/专利信息就保留未取得/待确认 | 不推断已软著、已合作或营收；报名规则/截止时间另由负责人确认 |
| 附录 B（560–568）与结论 | v0.9 产品未实现、下一步进入 v0.9 | 当前正式版本、计数、证据索引、走查限制、停止开发与四层未来路线 | 保留历史原版本；目录/页码需下次排版后重新核验 |

## 4. 必须区分的三个状态

| 状态层 | 可以写 | 不能写 |
|---|---|---|
| Engineering Release | v1.0.0 PASS / STABLE PROTOTYPE / CONTROLLED LAB | Production ready、全部能力无缺陷 |
| Post-freeze Walkthrough | 覆盖清单已形成，53+8 通过；1 失败、1 未测；操作与文档缺口保留 | 63 全部成功、人工负责人已签署 |
| Future Plan | v1.0.1 推荐；Competition 交付待批准；v1.1/v2 需条件 | 已进入新版本、代码/审批/PDF/健康探针已实现 |

建议 Known Limitations 摘要至少包含 START/UI/F22、Lab-only、Replay-only、无审批管理/任意执行/网页备份、JSON/MD 草稿、Model/Worker UNKNOWN、未验生产/新宿主/Windows/OT、AI 主张与供应链剩余风险。可以引用附录，无需把原计划变成故障清单。

## 5. 原始愿景符合性对照

“完成”均指 v1 受控边界，不是企业完整版。以下十二项未找到负责人正式取消核心目标的决定，不能因未实现独立页面就写“已取消”。

| 原始核心构想 | 当前归类 | 当前实现 / 安全收敛 | 后移与仍值得做的部分 |
|---|---|---|---|
| 事件压缩 | 已完成 | 规范化、去重、EventGroup/CorrelationDecision/Incident，保留来源/成员/异常证据 | 真实用户数据下误合并/漏关联与关键异常保留评测，不泛化历史压缩比 |
| Environment State | 已完成最小形态 + 未来扩展 | PG 主状态、Resource/Context/事实类型/时效；不是大型通用知识库 | 更完整资产/状态、关系与 drift，full twin 需可校准范围 |
| AI Decision | 经安全收敛完成 | Model Gateway、证据约束分析/提案、SHADOW/fallback，OPTION B | 标注场景语义评估/闭环增益另研究，不预承诺多模型/新 Agent |
| Task Orchestration | 已完成 v1 | PG task/outbox、DAG、优先级/预算、lease/fencing | 跨天/审批/跨站点需求出现才引 durable workflow/event bus |
| Risk Gate | 经安全收敛完成 | 确定性 Scope/风险/业务约束、精确授权绑定、失效与执行重检 | 完整审批治理与策略运营需责任/身份/撤权设计 |
| Controlled Response | 经安全收敛完成 | 仅固定登记 Lab Capability，owned TTL/幂等/核对/补偿 | 普通终端隔离、会话终止等原愿景未成为当前通用产品；逐 Adapter 评审 |
| Continuous Verification | 已完成 v1 | 独立 Security/Business/Observation，PASS/FAIL/INCONCLUSIVE | 更广重复/长期验证与真实目标范围，不以 ACK 替代安全有效 |
| Evidence | 已完成 | provenance/hash、Context/Action/Verification/audit、版本与投影 | 企业证据存储/留存治理需真实需求；完整性不是内容真相 |
| Re-plan | 经安全收敛完成 | 有限次数、证据/风险/预算约束，无证据/预算到达停止 | 跨长任务恢复可研究；无限自主循环明确排除 |
| Dashboard | 已完成产品层 | Overview + Incidents/Detail + Health + 显示偏好 | 资产/情报/运营工作区按用户任务评估，不补菜单凑齐 |
| Graph | 已完成投影，交互有缺陷 | 有来源的记录关联/推断与非因果；UI-001 待修 | 因果攻击路径、多跳/图数据库需真实关系与查询收益 |
| Reports | 已完成 v1 范围 | 八段固定快照报告、JSON/Markdown/hash，未复核草稿 | PDF/HTML/签名产品需交付需求与审核机制，不算 v1 缺陷 |

明确排除而非待补的旧设想：LLM 直接高权限执行、互联网反攻、不受 Scope 的任意执行、无限自主循环、把模型置信度当校准概率。ai.5 已有 non-goals，属于安全/范围收敛；没有证据证明上述十二项核心愿景被正式取消。原始稿的路径“概率预测”、full twin 等描述应改成证据排序/未来研究，不能包装成当前能力。

## 6. 下一次真正更新的验收与停止

获得授权后，从最近工程状态更新版派生新文件，保留章序、历史图和原稿身份；只按本提案同步有证据变化。先核对全部“当前/已完成/未来/未验证”语句，再更新目录和页码，最后渲染 DOCX/PDF 看版式、断行、图表和截图归属。材料须与选定发行版本/维护结果一致，不能以计划文字证明功能存在。

本轮未执行上述编辑与渲染。批准“计划书更新”不自动批准 Maintenance 或 Competition Delivery；批准其中任一也不代表全路线进入实施。
