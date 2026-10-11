# 智御 ZHIYU v1.0.0 · Full Product Walkthrough

2026-10-05，已封版 Stable Prototype 的操作验收与文档附加成果。**READ / RUN / OPERATE / VERIFY / DOCUMENT；无修复。** 不改变原 v1.0.0 PASS / STABLE PROTOTYPE，不生成v1.0.1，不重打ZIP。

## 验收结论

准备就绪的Reference上，实际事件读取、模型证据链、确定性授权、受控执行、独立三维验证、报告和五场景回放均可操作。全部固定A–E各执行两轮并清理，另验证一次未执行意图取消。所有可见入口已检查，但事件列表跨页因只有一条记录未实际翻页；图谱方向键平移失败。因此不签署“所有功能成功”。严格正式冷服务启动还存在START-001，因此整体核心流程的无条件结论为NO，**已恢复底层服务后的核心流程可操作**。

本轮是工具操作的真实浏览器走查，不是负责人、人类首次用户的签字。MANUAL_MATCHES_ACTUAL_PRODUCT=YES只表示手册与本轮事实/实际路由一致；所有附加文档仍待负责人审查。

| 计数 | 数值 | 口径 |
|---|---:|---|
| TOTAL_USER_VISIBLE_FEATURES | 63 | 独立功能单元，复用控件归组，非DOM按钮总数 |
| WORKING | 53 | 非Lab通过项，含READ_ONLY与REPLAY_ONLY |
| WORKING_LAB_ONLY | 8 | 固定A–E、取消、清理、重置 |
| FAILED | 1 | F42，网页可见功能失败 |
| NOT_TESTABLE | 1 | F22，当前获准数据不足以翻页 |

63 = 53 + 8 + 1 + 1。OPS-START另外记录，不重复加入网页分母。Scenario C的INCONCLUSIVE、D的FAIL、E的FALLBACK和B的REJECTED是正确固定反例结果，不能算产品功能失败。功能类型枚举见 [最终功能清单](FINAL_FUNCTION_INVENTORY_v1.0.0.md)。

## 依据、正式产品与环境

已读取最终VALIDATION_REPORT、FINAL_EVIDENCE_INDEX、USER_GUIDE、ADMIN_GUIDE、INSTALLATION_GUIDE、DEPLOYMENT_GUIDE、COMPETITION_DEMO_GUIDE、SECURITY_BASELINE、KNOWN_LIMITATIONS、API_CONTRACT，以及工程根RELEASE_NOTES_v1.0.0.md；并核对frontend router/nav/实际组件、后端product/demo routes、registry/queries、固定scenario/Compose/Reference CLI/health。

实际工程应用v1.0.0，投影/报告协议0.9.0，数据库head=0016_lab_remediation。正式包RC12，391受控文件。AI OPTION B，仅分析/规划建议；默认OFF/启用SHADOW。G0 NOT_INCLUDED；closed-loop superiority NOT_CLAIMED；生产NOT_VALIDATED。

本轮复用 `.work/v1-reference-rc6` 已安装部署，project/owner `zhiyu-v1-efac7e3aa5c8`。Windows操作员、Docker Desktop Linux Engine、同源Web ingress、API、PostgreSQL；独立Worker处理固定Lab意图。URL为 `http://127.0.0.1:18010`，仅loopback暴露。身份v09-demo-operator，product:read + 实际ReadGrant + demo:run；控制环境v1-reference-control、scope-lab-web。不公开凭据、不取得任意Action权限。

使用缓存Playwright CLI的真实headed Chromium，主会话1920×1080；另七个导航页分别1366×768，额外960宽度查看详情抽屉。14个页面外层scrollWidth均等于viewport；表格/图谱内部滚动允许。登录、焦点、图谱Enter、目录焦点、空状态、错误/加载均有实际操作。无应用白屏/缺失静态资源/应用未捕获崩溃。日志含预期401、实际429，以及宿主Kaspersky注入脚本被CSP阻止；后者不归为应用脚本故障，不把“有console error日志”写成零错误。

## 正式启动与干净起点

起点Docker Desktop未运行。启动Docker Linux Engine后，本部署已有API、PostgreSQL、ingress全部停止。**没有执行第二次全新install、重建镜像/数据库或修改配置来美化结果。** 按正式启动入口执行：

```powershell
$env:PYTHONUTF8 = '1'
$deployment = 'C:\Users\wc\Documents\ChatGPT\创新创业大赛\.work\v1-reference-rc6'
$runtime = Join-Path $deployment 'venv\Scripts\python.exe'
& $runtime tools/release_profile.py start --deployment $deployment
```

首次实际失败为 `reference_database_not_running`。START-001：start只拉API，要求PostgreSQL/ingress已运行。随后核验两个**既有本部署容器**归属后恢复底层服务；记录的实际操作为 `docker start 0634af582e8d 4f46d0b06d63`。这些ID只解释此次操作，不能供其他安装盲目复制。未删除/移动/重建容器、数据或其他项目。

恢复后，正式工具实现的stop/start与健康重测耗时7.31秒。本轮末另直接执行文档列出的CLI start/status→health→ready，4.88秒通过后CLI stop：health HTTP200/ok/version1.0.0/ai_enabled=false/active_security_actions_enabled=false；ready HTTP200/ready/database=ok/schema0016。这些全局字段不妨碍登记Lab的独立显式SHADOW演示，不能误读为网页可任意执行。

```powershell
& $runtime tools/release_profile.py stop --deployment $deployment
& $runtime tools/release_profile.py start --deployment $deployment
& $runtime tools/release_profile.py status --deployment $deployment
Invoke-RestMethod 'http://127.0.0.1:18010/health'
Invoke-RestMethod 'http://127.0.0.1:18010/ready'
# LIVE Lab使用另一终端，保留前台可退出的Worker：
& $runtime tools/release_profile.py worker --deployment $deployment
```

证据：[启动前置发现](../output/playwright/walkthrough/startup-prerequisites.json)、[工具启动/健康/服务](../output/playwright/walkthrough/startup.json)、[直接正式CLI start/status/health/ready/stop](../output/playwright/walkthrough/official-cli-cycle.json)。START-001按首次使用阻断项交负责人判断，**没有因人工恢复成功而删掉首个失败**。

## 逐功能操作结果

下表是实际动作/结果。PASSED/FAILED/NOT_TESTABLE为操作验收标签，区别于功能清单规定的Status枚举。截图反映入口或选定时点；完整结果以JSON/实际下载证据为准，尤其演示目录截图不证明各次运行结果。

| Feature | Action Performed | Result | Evidence | Screenshot | Finding | Status |
|---|---|---|---|---|---|---|
| F01 登录 | 输入用户名/访问密钥并登录 | 进入授权工作台，无白屏 | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | [截图](manual-assets/overview.png) | — | PASSED |
| F02 退出/重新登录 | 退出后重新登录；实际会话到期再登录 | 登录表单恢复；重启丢失会话后可重新登录 | [api-recovery.json](../output/playwright/walkthrough/api-recovery.json) | — | — | PASSED |
| F03 工作环境 | 选择两种获准环境 | 授权范围与读API参数改变 | [overview.json](../output/playwright/walkthrough/overview.json) | [截图](manual-assets/overview.png) | — | PASSED |
| F04 读取Scope | 选择范围；试读未授权范围 | 获准数据可读；越权403而非扩大权限 | [read-states.json](../output/playwright/walkthrough/read-states.json) | [截图](manual-assets/system-status.png) | — | PASSED |
| F05 全局时间窗 | 逐个选择再恢复24小时 | URL/请求窗口变化；回放禁用时间窗 | [overview.json](../output/playwright/walkthrough/overview.json) | [截图](manual-assets/overview.png) | — | PASSED |
| F06 全局刷新 | 点击刷新当前数据 | 重新读取；LIVE新快照，REPLAY保留档案 | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | [截图](manual-assets/overview.png) | — | PASSED |
| F07 命令查找 | Ctrl+K输入；清空/方向键/Enter/Escape | 当前事件可查；无结果空态；可键盘关闭 | [command-incident.json](../output/playwright/walkthrough/command-incident.json) | — | — | PASSED |
| F08 命令跳转 | 选页面按Enter | 进入对应实际路由 | [preferences.json](../output/playwright/walkthrough/preferences.json) | — | — | PASSED |
| F09 命令刷新 | Ctrl+K搜索刷新并Enter | 面板关闭且读数据更新 | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | — | — | PASSED |
| F10 侧栏折叠 | 折叠/展开；窄屏导航 | 图标标签可达；布局可恢复 | [preferences.json](../output/playwright/walkthrough/preferences.json) | [截图](manual-assets/overview.png) | — | PASSED |
| F11 显示偏好 | 逐项切换、重载验证、恢复 | sidebar/panel/context/banner记忆；无密钥localStorage | [preferences.json](../output/playwright/walkthrough/preferences.json) | — | — | PASSED |
| F12 环境健康面板 | 点击Sensor覆盖打开/关闭 | 真实心跳/覆盖、DB AVAILABLE、模型/Worker UNKNOWN | [new-core.json](../output/playwright/walkthrough/new-core.json) | [截图](manual-assets/system-status.png) | — | PASSED |
| F13 概览四项KPI | 读数并与API/SQL比对 | 8/1/0/1完全一致；N/A/Not calculated保留 | [kpi-source-validation.json](../output/playwright/walkthrough/kpi-source-validation.json) | [截图](manual-assets/overview.png) | — | PASSED |
| F14 KPI跳转 | 分别点击再返回 | 四项均跳事件列表，不声称自动应用专用筛选 | [overview.json](../output/playwright/walkthrough/overview.json) | [截图](manual-assets/overview.png) | — | PASSED |
| F15 趋势悬浮 | 悬浮实际数据点 | 日期与数量tooltip显示；非随机曲线 | [overview.json](../output/playwright/walkthrough/overview.json) | [截图](manual-assets/overview.png) | — | PASSED |
| F16 趋势图例 | 隐藏后显示序列 | 隐藏空态与恢复均正常 | [overview.json](../output/playwright/walkthrough/overview.json) | [截图](manual-assets/overview.png) | — | PASSED |
| F17 关注队列/全部事件 | 查看空态；点击查看事件/全部事件 | 均可到列表；队列最多当前页5条 | [overview.json](../output/playwright/walkthrough/overview.json) | [截图](manual-assets/overview.png) | UX-005 | PASSED |
| F18 事件搜索 | 输入/清空 | 命中一条；未知词空态可重置 | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | [截图](manual-assets/incident-list.png) | — | PASSED |
| F19 事件状态筛选 | 选择再恢复 | 按当前状态查询，状态有文字 | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | [截图](manual-assets/incident-list.png) | — | PASSED |
| F20 事件优先级筛选 | 选择P0再恢复 | 无命中显示空态，不造记录 | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | [截图](manual-assets/incident-list.png) | — | PASSED |
| F21 重置筛选 | 点击重置 | 清除查询条件；旧筛选跨环境须手动清除 | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | [截图](manual-assets/incident-list.png) | UX-002 | PASSED |
| F22 事件列表分页 | 检查下一页/返回首页 | 只有1条，按钮禁用；跨页未实测 | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | [截图](manual-assets/incident-list.png) | — | NOT_TESTABLE |
| F23 事件面板/完整页 | 选行、完整页、主要事件入口 | 右面板与完整页显示同一事件；窄屏抽屉可关 | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | [截图](manual-assets/incident-detail.png) | — | PASSED |
| F24 详情面板折叠 | 收起/显示；窄屏关闭 | 不丢当前事件，导航恢复可操作 | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | [截图](manual-assets/incident-detail.png) | — | PASSED |
| F25 事件摘要 | 打开摘要 | VERIFYING、授权、执行、验证分别展示 | [new-core.json](../output/playwright/walkthrough/new-core.json) | [截图](manual-assets/incident-detail.png) | — | PASSED |
| F26 AI决策/ModelRun | 查model/provider/延迟/分析/提案 | 本地真实调用；SHADOW/自报置信度/拒绝/降级明确 | [new-core.json](../output/playwright/walkthrough/new-core.json) | [截图](manual-assets/ai-modelrun.png) | — | PASSED |
| F27 Authorization/Risk | 按action_id查看独立授权和风险 | A R2 ALLOW；B在Proposal层拒绝无Action，未伪造DENY | [fault-observations.json](../output/playwright/walkthrough/fault-observations.json) | [截图](manual-assets/ai-decision.png) | — | PASSED |
| F28 Action回执 | 查Attempt/Result/executor/output_hash | EXECUTION_SUCCESS独立于Verification | [new-core.json](../output/playwright/walkthrough/new-core.json) | [截图](manual-assets/ai-decision.png) | — | PASSED |
| F29 三维Verification | 读取安全/业务/观测与TTL | PASS/FAIL/INCONCLUSIVE实测；过期不当当前PASS | [fault-observations.json](../output/playwright/walkthrough/fault-observations.json) | [截图](manual-assets/verification.png) | — | PASSED |
| F30 Evidence/复制ID | 查看来源/hash/时间；复制ID | ID复制成功Toast；敏感Raw定位不自动公开 | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | [截图](manual-assets/incident-detail.png) | — | PASSED |
| F31 记录沿袭 | 逐卡读取 | Raw/Normalization/Event/Group/Correlation/Incident/Audit可见 | [new-core.json](../output/playwright/walkthrough/new-core.json) | [截图](manual-assets/incident-detail.png) | — | PASSED |
| F32 详情跨页链接 | 记录→时间线；证据→图谱；摘要→验证 | 对象/快照一致，返回可继续阅读 | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | [截图](manual-assets/timeline.png) | — | PASSED |
| F33 聚焦事件选择器 | 选空后恢复原ID | 先选择一条事件空态→正常记录 | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | [截图](manual-assets/timeline.png) | — | PASSED |
| F34 时间线分页 | 下一页两次再返回首页 | 三页共112点；API时间排序成立 | [timeline-controls-final.json](../output/playwright/walkthrough/timeline-controls-final.json) | [截图](manual-assets/timeline.png) | — | PASSED |
| F35 时间点/来源检查 | 鼠标与Enter选点/来源记录 | 检查器展示source_ref/字段/时间语义 | [timeline-controls-final.json](../output/playwright/walkthrough/timeline-controls-final.json) | [截图](manual-assets/timeline.png) | — | PASSED |
| F36 时间线缩放/浏览 | 放大缩小；拖动浏览时间轴 | 125–150%与浏览位置65%实际生效 | [timeline-controls-final.json](../output/playwright/walkthrough/timeline-controls-final.json) | [截图](manual-assets/timeline.png) | — | PASSED |
| F37 图谱节点/关系来源 | 逐类选节点读关系 | source_ref/source_field/非因果明确，推断不冒充事实 | [graph-controls.json](../output/playwright/walkthrough/graph-controls.json) | [截图](manual-assets/graph.png) | — | PASSED |
| F38 图谱搜索 | 搜空结果、清空、收起实体列表 | 实体搜索/无匹配/恢复正常 | [graph-controls.json](../output/playwright/walkthrough/graph-controls.json) | [截图](manual-assets/graph.png) | — | PASSED |
| F39 图谱聚焦/两层/重置 | 以此节点展开两层后重置 | 新root查询，上限200节点400边，重置恢复 | [graph-controls.json](../output/playwright/walkthrough/graph-controls.json) | [截图](manual-assets/graph.png) | — | PASSED |
| F40 图谱缩放 | 放大缩小 | 160%可操作，节点内容仍可检查 | [graph-pan.json](../output/playwright/walkthrough/graph-pan.json) | [截图](manual-assets/graph.png) | — | PASSED |
| F41 图谱鼠标平移 | 拖动空白处 | scrollLeft实际增加160 | [graph-pan.json](../output/playwright/walkthrough/graph-pan.json) | [截图](manual-assets/graph.png) | — | PASSED |
| F42 图谱方向键平移 | 按/持续按右方向键两次 | scrollLeft仍0，与可方向键滚动标签不符 | [read-states.json](../output/playwright/walkthrough/read-states.json) | [截图](manual-assets/graph.png) | UI-001 | FAILED |
| F43 固定快照报告 | 打开报告逐节读取 | 八节草稿，与同一snapshot Facts对应 | [live-report-integrity.json](../output/playwright/walkthrough/live-report-integrity.json) | [截图](manual-assets/report.png) | — | PASSED |
| F44 报告目录 | 逐个点击目录 | 对应H3滚动并获得焦点 | [report-export-final.json](../output/playwright/walkthrough/report-export-final.json) | [截图](manual-assets/report.png) | — | PASSED |
| F45 下载JSON | 实际下载并解析/校验 | UI Facts/报告/精确文件hash一致 | [live-report-integrity.json](../output/playwright/walkthrough/live-report-integrity.json) | [截图](manual-assets/report.png) | — | PASSED |
| F46 下载Markdown | 实际下载阅读/校验 | 八节、来源、限制和hash保留 | [live-report-integrity.json](../output/playwright/walkthrough/live-report-integrity.json) | [截图](manual-assets/report.png) | — | PASSED |
| F47 场景目录/profile | 读取目录并选择登记profile | 只有固定A–E；脚本与真实模型标签明确 | [demo-events.json](../output/playwright/walkthrough/demo-events.json) | [截图](manual-assets/demo.png) | — | PASSED |
| F48 Scenario A | 开始→刷新→完成→查看结果 | 两轮REAL_LOCAL_MODEL，PASS且CLEAN | [current-scenarios.json](../output/playwright/walkthrough/current-scenarios.json) | [截图](manual-assets/demo.png) | — | PASSED |
| F49 Scenario B | 开始→刷新→完成→查看结果 | 两轮SCRIPTED_NOT_AI，REJECTED，Action为0 | [current-scenarios.json](../output/playwright/walkthrough/current-scenarios.json) | [截图](manual-assets/demo.png) | — | PASSED |
| F50 Scenario C | 开始→刷新→完成→查看结果 | 两轮真实Sensor故障，三维INCONCLUSIVE | [fault-observations.json](../output/playwright/walkthrough/fault-observations.json) | [截图](manual-assets/verification.png) | — | PASSED |
| F51 Scenario D | 开始→刷新→完成→查看结果 | 两轮SCRIPTED_NOT_AI，业务FAIL，有限重规划 | [fault-observations.json](../output/playwright/walkthrough/fault-observations.json) | [截图](manual-assets/verification.png) | — | PASSED |
| F52 Scenario E | 开始→刷新→完成→查看结果 | 两轮实际模型不可用，FALLBACK保留确定性链 | [fault-observations.json](../output/playwright/walkthrough/fault-observations.json) | [截图](manual-assets/ai-decision.png) | — | PASSED |
| F53 运行进度刷新 | 刷新运行状态观察四阶段 | 步骤完成与actual_outcome分开显示 | [demo-events.json](../output/playwright/walkthrough/demo-events.json) | [截图](manual-assets/demo.png) | — | PASSED |
| F54 停止后续步骤 | Worker暂停时QUEUED点击停止 | CANCELLED、0步、0资源；不宣称回滚 | [shutdown.json](../output/playwright/walkthrough/shutdown.json) | [截图](manual-assets/demo.png) | — | PASSED |
| F55 清理本次资源 | 点击清理并等CLEAN | 归属容器/网络/卷均0，旧证据保留 | [shutdown.json](../output/playwright/walkthrough/shutdown.json) | [截图](manual-assets/demo.png) | — | PASSED |
| F56 重置并新建运行 | 点击重置，等待第二轮完成清理 | 五个新run_id，predecessor正确，旧档案保留 | [current-scenarios.json](../output/playwright/walkthrough/current-scenarios.json) | [截图](manual-assets/demo.png) | — | PASSED |
| F57 运行历史回放 | 分别点历史回放、图谱、报告/导出 | RECORDED_REPLAY；全74表与10档案不变 | [replay-integrity.json](../output/playwright/walkthrough/replay-integrity.json) | [截图](manual-assets/timeline.png) | — | PASSED |
| F58 封存记录目录回放 | 打开历史回放 | 回放标识和原记录一致 | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | [截图](manual-assets/timeline.png) | — | PASSED |
| F59 回放刷新 | 刷新后重新读图谱/报告 | 仍同源Facts/hash；无ModelRun/Action写入 | [replay-integrity.json](../output/playwright/walkthrough/replay-integrity.json) | [截图](manual-assets/report.png) | — | PASSED |
| F60 加载骨架屏 | 刷新观察loading | 2处骨架屏，非居中spinner | [read-states.json](../output/playwright/walkthrough/read-states.json) | — | — | PASSED |
| F61 读取错误/重试 | 读失败后恢复/重试 | 旧KPI撤下；范围错误明确；API恢复需重登录 | [api-recovery.json](../output/playwright/walkthrough/api-recovery.json) | [截图](../output/playwright/walkthrough/api-unavailable.png) | UX-003 | PASSED |
| F62 响应式/键盘焦点 | 逐页导航；键盘选实体/关闭抽屉 | 14页面无外层横向溢出；focus轮廓可见 | [responsive-final.json](../output/playwright/walkthrough/responsive-final.json) | [截图](manual-assets/overview.png) | — | PASSED |
| F63 相对时间/完整时间 | 阅读相对时间并查看title/键盘标签 | 显示完整+08:00时间；时间轴UTC注明 | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | [截图](manual-assets/timeline.png) | — | PASSED |

## 数据来源与真实页面

实际七页：概览、事件、时间线、证据图谱、报告、演示、显示偏好；事件详情有摘要/决策/验证/证据/记录五页签，环境健康是面板。没有计划中的独立Assets/Threats/Detection页，未在手册虚构。

概览API为`GET /v1/product/overview`，同源授权范围下查询PostgreSQL；四项指标不是前端常量/随机/fixture。A本轮UI/API/只读SQL为关联Event去重8、Incident1、待处理0、VERIFYING1。需要处理由NEW/WAITING_APPROVAL/HUMAN_REVIEW/REOPENED求和，列表与Incident创建窗口/筛选一致。环比前一等长窗口为零时N/A；三项标“环比未计算”。近七日daily_incidents按UTC日桶和ReadGrant计算，独立于列表search/status/priority。综合分数Not calculated、防护/通过率N/A是明确未定义，不用假分数填充。

来源见 [KPI SQL/UI对照](../output/playwright/walkthrough/kpi-source-validation.json)、[浏览器DTO](../output/playwright/walkthrough/kpi-review.json)、`src/zhiyu/product/queries.py`。固定Lab真实Sensor产生的记录与系统明确标SYNTHETIC的测试记录分别保留；“LIVE”只描述读取方式，不证明所有内容生产来源。关键来源Raw正文/定位不自动公开。

首次快速流程截图KPI为0，之后只读API/UI稳定读数为8/1/0/1。原因是采集在数据加载/数字count-up结束前；保留quick-start-attempt-1.json并修正**附加采集脚本**等待真实API值与可见数字相同，未改产品。第二次极快切环境出现真实429，记录quick-repeat-failure.yml；按文案等待/重读和正常操作节奏后完成。没有关闭速率限制或吞掉错误。

## 后端对象与用户可见面分开核对

以下均在本轮A当前snapshot的94 Facts中实际存在，不能由数据库存在推断详情页有专用卡片。快照history_completeness=PARTIAL，保持“不完整”提示。

| 对象 | BACKEND EXISTS | USER VISIBLE（实际入口） |
|---|---|---|
| Event / Normalized Event | YES，event/normalization/raw | 记录页签、Timeline、Graph、Report；没有独立检测控制台 |
| EventGroup / Correlation | YES，group/group_member/correlation | 记录页签中的group/correlation，Timeline/Graph/Report |
| Incident | YES | 列表、摘要、根Fact、跨页聚焦 |
| Affected Resource | YES，resource/event_resource | 列表资源名、Graph resource检查器、报告；无资产管理页 |
| Evidence | YES | 证据卡片/ID/hash/时间，Graph关联、报告附录；不开放所有敏感原文 |
| Environment Context | YES，context/ai_context | 决策上下文卡、Scope/Environment、来源字段；非环境编辑 |
| AI Analysis / Proposal | YES | 决策页ModelRun/analysis/proposal；SHADOW与validation.reasons |
| Authorization / Risk | YES | 决策与摘要；按action_id查看独立决定/评估，无人工审批按钮 |
| Plan / Task | YES | Plan在决策卡；Task在Timeline/Graph/Report，无通用Task管理页 |
| Action / Attempt / Result | YES | 决策/摘要、Timeline/Graph/Report；浏览器不能编写任意Action |
| Verification / Check / Observation | YES | 验证页三维、具体执行/断言/证据及valid_until |
| State Update / Re-plan | YES | 验证页state_update/state/replan、Timeline/Graph/Report；不编造额外重规划 |

证据：[本轮A五页签/快照/投影](../output/playwright/walkthrough/new-core.json)。

## Timeline / Graph / AI / 授权 / 验证

时间线实际翻完三页112点，API顺序检验成立，节点可选/键盘Enter，source_ref与来源类型保留。展示Detection/Raw、Normalization、Correlation、Incident、AI analysis/proposal、Authorization、Action、Verification、State/Re-plan等实际记录；source/observed/ingested/created时间语义不同。页图UTC、完整卡片+08:00均注明，时间邻近不证明因果。

Graph逐类查看resource、incident、evidence、verification、analysis、raw；检查器显示relation/source_ref/source_field/semantic_class，所有边causal=false。MODEL_INFERENCE保持推断，UNKNOWN保持未知。两层查询、root/focus、搜索空态/恢复、缩放/实体面板工作；实际鼠标拖动scrollLeft增加160。两次聚焦画布方向键测试scrollLeft仍0，UI-001；初次零拖动是在100%横向空间不足，调整到160%后鼠标成功，未错误归类鼠标失败。

真实A ModelRun：provider字段实际`demo`（本地适配身份），model `zhiyu-qwen2.5-1.5b`，固定GGUF hash `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`，source REAL_LOCAL_MODEL。分析/提案latency_ms=45734/37396。Analysis REFERENCE_GROUNDED，假设model_confidence=0.95未经校准，semantic_correctness=NOT_VALIDATED；Proposal SHADOW/valid=true/plan_id=null。UI有明确限定，没有称保证正确。

A固定确定性动作lab_http_containment，经R2/LOW风险/独立ALLOW进入LAB_PATH；human_approval_required=false。不存在任意目标/人工审批编辑入口。B scripted proposal因`hallucinated_or_out_of_context_capability`被REJECTED，Action=0，未达到授权执行层，不能虚构Authorization DENY。Proposal != Authorization。

A三维均PASS，但仅短期临时遏制，历史过期显示“历史·已过期”，Incident仍VERIFYING；Re-plan为NO_REPLAN/count0，根因未声称修复或关闭。C三维INCONCLUSIVE，缺观测，产生一次收集额外观测的有限重规划。D独立结果Security PASS / Business FAIL / Observability PASS，总体FAIL，保留有限重规划；模型脚本声称成功不能覆盖真实业务失败。Execution Success != Security Success。

## 固定CONTROLLED LAB的十次完整运行

五场景实际按UI Start/Progress/Completion/Result/Cleanup/Reset操作。Start/Reset/清理HTTP202只登记意图，Worker真实执行；四阶段PREFLIGHT/TRIGGER/VERIFY/ARCHIVE完成不是安全PASS。每场景第一轮CLEAN后用“重置并新建运行”创建第二轮，predecessor与原ID匹配。第二轮再次CLEAN，保留原事实、失败和录制。

| Scenario | Run ID | Predecessor | Actual Outcome | Model Source | 最终状态 / Cleanup / 归属资源残留 |
|---|---|---|---|---|---|
| A | demo-4d0c80d3b356451d85cc90e64d52ea4f | 首次 | PASS | REAL_LOCAL_MODEL | COMPLETED / CLEAN / 0 |
| A | demo-2c257b079f3f410d8900a3e5fa21beb8 | demo-4d0c80d3b356451d85cc90e64d52ea4f | PASS | REAL_LOCAL_MODEL | COMPLETED / CLEAN / 0 |
| B | demo-78de4c70295944918373d502d2d5863d | 首次 | REJECTED | SCRIPTED_NOT_AI | COMPLETED / CLEAN / 0 |
| B | demo-d632826c6d7f470fb04b79a97dd71671 | demo-78de4c70295944918373d502d2d5863d | REJECTED | SCRIPTED_NOT_AI | COMPLETED / CLEAN / 0 |
| C | demo-29f5ac435776462c938337fede8195af | 首次 | INCONCLUSIVE | NONE | COMPLETED / CLEAN / 0 |
| C | demo-fbb50b5e353146dab445187c51b9b38c | demo-29f5ac435776462c938337fede8195af | INCONCLUSIVE | NONE | COMPLETED / CLEAN / 0 |
| D | demo-b563f17705d740a3a47f18116571bb43 | 首次 | FAIL | SCRIPTED_NOT_AI | COMPLETED / CLEAN / 0 |
| D | demo-ed838166428046ce8385e01535b7a088 | demo-b563f17705d740a3a47f18116571bb43 | FAIL | SCRIPTED_NOT_AI | COMPLETED / CLEAN / 0 |
| E | demo-14fa09f7b6c549f59fec6ff27c4461bb | 首次 | FALLBACK | REAL_LOCAL_MODEL | COMPLETED / CLEAN / 0 |
| E | demo-4e49d649c3a647219cc950b652985ef6 | demo-14fa09f7b6c549f59fec6ff27c4461bb | FALLBACK | REAL_LOCAL_MODEL | COMPLETED / CLEAN / 0 |

正常A真实Sensor→Event→Incident→Analysis→Proposal→独立Authorization→固定受控Action→独立Verification→State Update链完成，根因修复/安全关闭没有伪造。B/D明确SCRIPTED_NOT_AI只证明固定失败边界；C没有模型来源不补假ModelRun。

另固定B取消run_id `demo-f93051bf6b64434498f4c7c99c4ee1ec`：Worker暂停时QUEUED→实际按钮“停止后续步骤”→CANCELLED/step0→提交清理→Worker处理→CLEAN/0残留。它不计入十次COMPLETED演示，也不证明已执行动作可回滚。

证据：[UI意图与进度](../output/playwright/walkthrough/demo-events.json)、[最终DB/reset/归属资源核对](../output/playwright/walkthrough/current-scenarios.json)、[最终11次清理与关闭](../output/playwright/walkthrough/shutdown.json)。scenario-summary是在各轮清理前采集，**不把其中NOT_STARTED当作最终清理结果**。

## 故障：实际运行与浏览器注入分别标识

| 类型 | 操作/结果 | 恢复与验证边界 |
|---|---|---|
| 真实C Sensor unavailable | 正式固定场景停止一次性Lab Agent；此前Suricata/Wazuh HEALTHY/有效覆盖，之后无有效覆盖/UNKNOWN；三维INCONCLUSIVE | 清理C后新建已登记Lab，不改历史失败；没有停止宿主安全软件 |
| 真实E Model unavailable | 固定本地模型停止，request/receipt保留错误/FALLBACK；确定性链保留 | 不换假模型、不提权；可明确历史回放 |
| 真实API stopped | API stop后刷新出现读取失败、旧KPI为0个，不能继续显示旧成功数值 | 正式start，health/ready200，重新登录恢复；74表不变 |
| 真实LIVE快照TTL过期 | 自然超过300秒再打开本轮已观察链接，显示“这份快照已过期，请明确刷新后重新查看。” | 显式刷新得到新LIVE快照并可读，不延长TTL |
| 真实403 / 404 | 未获准Scope/不存在Incident，显示范围/缺失文案 | 返回授权范围，不绕过鉴权 |
| 真实429 | 极快环境/筛选产生reader容量限制 | 等待并重读可恢复；保持服务端限制 |
| 浏览器延迟1200ms注入 | 2处骨架屏 | 仅测试loading反馈，不代表Sensor延迟故障 |
| 浏览器HTTP503注入 | “数据服务不可用，无法确认当前状态。”且旧KPI撤下 | 解除路由注入后正常；未宣称真实数据库停机/灾难恢复 |
| 浏览器导出hash损坏注入 | 通用读取错误；下载次数0 | 解除注入后真实JSON/MD正常下载；未篡改数据库或封存文件 |

证据：[34次运行/健康/失败详情观察](../output/playwright/walkthrough/fault-observations.json)、[真实API恢复](../output/playwright/walkthrough/api-recovery.json)、[真实TTL过期](../output/playwright/walkthrough/snapshot-expiry.json)、[浏览器注入及范围错误](../output/playwright/walkthrough/read-states.json)。

System Status当前有Sensor心跳/配置/有效覆盖、DB AVAILABLE、全局AI模式OFF；模型服务/Worker字段即使运行时也UNKNOWN，是未实现实时探针的诚实限制。健康汇总UNKNOWN允许；不要把未观测探针写成已证实HEALTHY。Lab清理后Sensor OFFLINE/覆盖未验证、心跳过期，UNKNOWN符合事实。API/frontend没有单独面板探针行；真实Web访问及health/ready另行验证。

## LIVE / RECORDED_REPLAY与报告导出

真实LIVE读取和五个登记A–E档案实际分别使用，UI顶部/范围条/快照均标模式，回放时间窗禁用。五次回放包含时间线→刷新→图谱→报告→JSON与Markdown共10份下载，记录original as_of、recording SHA、content SHA、report SHA。所有74张canonical表在操作前后逐表计数/摘要完全相等；10个本轮档案原字节SHA完全不变；未新增ModelRun/Action/Observation等写入。这证明所走的**只读回放路径**无副作用，不代表演示页其他LIVE Start按钮永远不能写入。

正式Report的JSON/Markdown八节实际名称：执行摘要、范围与方法、证据目录、事件时间线、AI 分析、决策与处置、独立验证、状态更新与重规划、限制与文档控制。其中“AI 分析、决策与处置”为一个章节；UI目录简写为“决策与处置”等。LIVE JSON解析与UI snapshot完全相等；事实hash、整体report hash、精确JSON/MD下载字节hash均通过。五份REPLAY报告同样通过源档案/事实/报告/字节hash核对，Markdown实际读取八节。

Report状态UNREVIEWED_DRAFT，不自动批准、签名或关闭Incident。当前没有HTML/PDF导出；0.9.0是冻结的投影/模板协议，应用health仍1.0.0。参考 [实际LIVE JSON](../output/playwright/walkthrough/report-live.json)、[实际Markdown](../output/playwright/walkthrough/report-live.md)、[LIVE一致性](../output/playwright/walkthrough/live-report-integrity.json)、[回放/10下载/74表证明](../output/playwright/walkthrough/replay-integrity.json)。

## 逐页用户体验检查（只记意见，不修改）

| 页面 | 用途/空态/加载 | 错误与状态文字 | 链接/返回/刷新 | 发现 |
|---|---|---|---|---|
| 概览 | 四项指标/趋势/关注区清晰；无待处理记录有按钮；加载骨架 | N/A、Not calculated、UNKNOWN如实；API失败撤旧指标 | KPI/全部事件可进入事件，图例可恢复，刷新有效 | UX-005：关注区0时写“当前窗口没有安全事件”，但KPI安全事件1；文案易误解 |
| 事件 | 列表/面板/完整页；搜空/优先级空有重置；窄屏抽屉可关 | 状态有文字，403/404/429可理解 | 搜索/筛选/重置/详情操作通过；跨页禁用未证明分页 | UX-002：旧筛选跨环境保留，需重置；单记录不可翻页 |
| 事件详情 | 五页签对应证据链；缺引用保留，不填假数据 | 执行与三维验证区分；过期明确；长ID/raw字段较密 | 复制Toast、跨时间线/图谱/验证、返回导航通过 | UX-004：英文原始字段和长ID对首次评委阅读成本高 |
| 时间线 | 真实时间与来源泳道/分页；未聚焦空态清楚 | source时间与UTC/本地时间保留；不完整提示 | 三页、Inspect、缩放/浏览、聚焦空后恢复通过 | 需手册说明多种时间语义，非因果 |
| 证据图谱 | 记录引用与检查器清晰，未知搜索有空态 | MODEL_INFERENCE/UNKNOWN/非因果文字明确 | 节点/关系来源/两层/root/search/zoom/鼠标pan通过 | UI-001方向键pan无效；不把图当攻击路径 |
| 报告 | 八节目录、草稿/来源/限制清晰 | 导出校验失败无下载，但通用“无法读取有效数据”诊断不够具体 | 八目录focus、JSON/MD、固定快照阅读通过 | UX-004原始附录很长；无PDF/签名属于边界 |
| 演示 | 实际五固定场景与LIVE/REPLAY分开 | actual/expected/model_source明确；C/D预期失败保留 | Start/刷新/清理/Reset/取消/历史回放通过 | 快速切环境可能429；需管理员Worker，不是浏览器自运行 |
| 显示偏好 | 四项说明清楚，布局记忆并恢复 | 状态均有文字，focus可见 | 4toggle/重载/恢复通过 | 只本机偏好，非系统运维Settings |
| 环境健康面板 | 心跳/配置/范围清楚，未覆盖有UNKNOWN说明 | 无独立Worker/Model实时探针，UNKNOWN保留 | 点击打开/关闭、刷新实际读取 | 不应向评委口述完整全组件在线监控 |

UX-003：连续快速操作会碰到并发容量限制，等待重试可恢复。这里提出的任何文案/交互优化都**没有实施**。

## 未修复问题与文档发现

| ID | 级别/性质 | 证据与影响 | 本轮处置 |
|---|---|---|---|
| START-001 / OPS-START | 首次冷服务启动阻断，需负责人复核是否Release Blocker | 正式start在底层停止时reference_database_not_running；需人工核验归属恢复PG/ingress | 记录原失败与有限恢复，未修改启动代码/配置；不宣称开箱即用 |
| UI-001 / F42 | 键盘交互失败 | 图谱标签承诺方向键滚动，实际两次0；鼠标平移160成功 | 手册明确鼠标操作与键盘限制，未修复 |
| DF-001 | 旧正式演示指南状态失配 | COMPETITION_DEMO_GUIDE.md:3仍称Gate E未完成，与当前正式PASS不同 | 原文保留，附加文档采用真实基线 |
| DF-002 | 旧API文档阶段失配 | API_CONTRACT_v1.0.md:3 Gate A实现中，结尾仍有旧阶段描述 | 原文保留，字段以源码/真实DTO核对 |
| DF-003 | 冷启动前置不足 | 正式部署流程未充分覆盖已有底层全部停止时的启动顺序 | 以START-001证据附加说明，未重写正式启动指南 |

## 安全关闭与冻结保全

所有10次完成运行及1次取消运行均实际CLEAN，按归属标签检查container/network/volume残留0。Worker终端Ctrl+C退出后worker.lock/operator.lock均不存在；执行正式stop只停止API，PostgreSQL/ingress保留，全部74表摘要不变。证据与录制不删除；未操作其他18011–18014部署，不关全Docker/WSL，不down -v。

关闭后本机Web不能继续读取API属于预期终态，不把保存的运行截图当“当前服务仍在线”。[11运行清理/关闭证明](../output/playwright/walkthrough/shutdown.json)。最后正式CLI入口核对完成也以stop结束，74表再次不变，[末次命令核对](../output/playwright/walkthrough/official-cli-cycle.json)。

原ZIP SHA256为`90e85661a0a90e46b789565f52cccaabb497b96d720e39b3c4bac4034bb55868`，47,842,718字节。本轮保护10,169个已有正式文件（含391受控项与所有既有docs）；附加文档/截图/证据另存，不加入原ZIP。最终 [冻结核对](../output/playwright/walkthrough/freeze-verification.json) 应显示 changed=[]、zip_unchanged=true；[附加文档校验](../output/playwright/walkthrough/documentation-qa.json) 对章节、链接、截图、敏感值与计数检查。

## 5分钟流程、手册与交付

实际服务stop/start→登录→概览→Incident→ModelRun/Verification→Timeline→固定档案Replay→Report下载路径耗时 **60.2秒**；只读浏览器流程本身48.96秒，全部74表不变。前提为已安装、本部署PostgreSQL/ingress已运行、已登记A档案、已获准身份。不包含冷install、镜像/模型下载、首次Docker恢复或新LIVE A全运行。这个时间是工具本机实测，不是保证任何首次用户都60秒完成。

手册24章及10个必需页面截图+ModelRun补图只来自本轮实际v1页面，截图涵盖较早已有Lab记录与本轮新A，按manual-assets/README注明身份/时点；没有使用历史设计mockup。未给不存在的HTML/PDF/审批/资产管理写教程。运维备份/新环境恢复引导到管理员正式指南，本轮不重新演练灾难恢复。

- [最终功能清单](FINAL_FUNCTION_INVENTORY_v1.0.0.md)
- [24章截图使用说明书](ZHIYU_USER_MANUAL_v1.0.0.md)
- [5分钟快速上手](ZHIYU_QUICK_START_v1.0.0.md)
- [比赛操作卡](ZHIYU_COMPETITION_OPERATION_CARD_v1.0.0.md)
- [实际截图及SHA来源](manual-assets/README.md)

## 最终指定判断

```json
{
  "ALL_USER_VISIBLE_FEATURES_WALKED_THROUGH": "NO",
  "ALL_CORE_WORKFLOWS_OPERABLE": "NO",
  "MANUAL_MATCHES_ACTUAL_PRODUCT": "YES",
  "UNTESTED_FEATURES": [
    "F22 事件列表跨页：各获准Lab子环境仅1条，分页禁用",
    "独立invalid EvidenceRef提案：正式固定UI场景无独立入口，未构造新场景",
    "本轮全新冷安装/新主机安装：复用已验证Reference",
    "真实数据库故障与任意损坏档案修复：未主动破坏；仅故障UI与登记档案读取验证"
  ],
  "FAILED_FEATURES": [
    "OPS-START / START-001 正式start无法启动已停止的底层PostgreSQL/ingress",
    "F42 / UI-001 图谱方向键平移无效"
  ],
  "DOCUMENTATION_FINDINGS": [
    "DF-001 COMPETITION_DEMO_GUIDE开头仍称Gate E未完成",
    "DF-002 API_CONTRACT开头Gate A实现中及旧阶段结尾未同步封版",
    "DF-003 start指南没有充分说明已停止底层服务时需额外恢复"
  ]
}
```

所有入口已检查不等于所有功能已执行成功；NO保留禁用分页、键盘失败、严格启动缺口。以上为本轮操作/文档判断，不修改原Release结论。负责人审查后再决定问题处置；本轮完成后停止，不修复、不开发新版本。
