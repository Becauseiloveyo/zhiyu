# 智御 v1.0.0 最终实际功能清单

2026-10-05，已封版 PASS / STABLE PROTOTYPE 的附加走查文档。基于实际 router、侧栏、后端读API及 Browser 操作，不从计划书补造页面。正式源码、UI、状态与ZIP不改动。

## 口径与权限

63项是可独立解释/操作的用户功能单元；复用按钮按功能归组，不按DOM节点计数。图谱鼠标与方向键分别计数，因为方向键标称可用但实测失败。禁用的事件列表分页仍纳入一个可见入口。不存在的页面不进入63项分母。

BASE＝已运行API/同源Web ingress/PostgreSQL与本机Browser；只读路径不需要Worker/模型。LAB＝BASE + 正式独立Worker + 登记controlled-lab + 该场景受控Sensor/固定本地模型或明确脚本反例。REPLAY＝BASE + 获准登记档案，不需要运行Lab/模型。角色名称只描述实际权限，不编造企业RBAC。

Status严格使用指定枚举：WORKING是UI操作可用，READ_ONLY是实际只读功能，REPLAY_ONLY是档案读取，WORKING_LAB_ONLY是固定Lab写入操作；UNAVAILABLE表示当前未能执行。F22仅在本次单记录数据集不可测试，**不等于证明分页代码未实现**；F42为实测失败。

API默认前缀 `/v1/product/`；projections包括snapshot、timeline、graph、report。时间线/图谱引用同一固定snapshot。只有demo登记意图为POST；它不授权任意核心Action。

## 功能矩阵

| Feature ID | Navigation / Entry | Page | Purpose | Required Role | Required Runtime | Input | User Action | Expected Result（实际验证） | Backend/API | Evidence | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F01 | 登录页 → 登录 | 登录页 | 登录 | product:read + 当前ReadGrant | BASE | 私密操作员身份 | 输入用户名/访问密钥并登录 | 进入授权工作台，无白屏 | POST session | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | WORKING |
| F02 | 全局 → 退出/重新登录 | 全局 | 退出/重新登录 | product:read + 当前ReadGrant | BASE | 当前会话 | 退出后重新登录；实际会话到期再登录 | 登录表单恢复；重启丢失会话后可重新登录 | DELETE/GET session | [api-recovery.json](../output/playwright/walkthrough/api-recovery.json) | WORKING |
| F03 | 全局 → 工作环境 | 全局 | 工作环境 | product:read + 当前ReadGrant | BASE | 登记父/子环境 | 选择两种获准环境 | 授权范围与读API参数改变 | GET access | [overview.json](../output/playwright/walkthrough/overview.json) | WORKING |
| F04 | 全局 → 读取Scope | 全局 | 读取Scope | product:read + 当前ReadGrant | BASE | scope-lab-web | 选择范围；试读未授权范围 | 获准数据可读；越权403而非扩大权限 | GET access/runtime-health | [read-states.json](../output/playwright/walkthrough/read-states.json) | WORKING |
| F05 | 全局 → 全局时间窗 | 全局 | 全局时间窗 | product:read + 当前ReadGrant | BASE | 6/24/72/168小时 | 逐个选择再恢复24小时 | URL/请求窗口变化；回放禁用时间窗 | GET overview/incidents | [overview.json](../output/playwright/walkthrough/overview.json) | WORKING |
| F06 | 全局 → 全局刷新 | 全局 | 全局刷新 | product:read + 当前ReadGrant | BASE | 当前范围/固定快照 | 点击刷新当前数据 | 重新读取；LIVE新快照，REPLAY保留档案 | GET projections | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | WORKING |
| F07 | 命令面板 → 命令查找 | 命令面板 | 命令查找 | 已登录本机用户 | BASE | 当前页事件ID/不存在的词 | Ctrl+K输入；清空/方向键/Enter/Escape | 当前事件可查；无结果空态；可键盘关闭 | 前端当前已读记录 | [command-incident.json](../output/playwright/walkthrough/command-incident.json) | WORKING |
| F08 | 命令面板 → 命令跳转 | 命令面板 | 命令跳转 | 已登录本机用户 | BASE | 页面名 | 选页面按Enter | 进入对应实际路由 | 前端路由 | [preferences.json](../output/playwright/walkthrough/preferences.json) | WORKING |
| F09 | 命令面板 → 命令刷新 | 命令面板 | 命令刷新 | product:read + 当前ReadGrant | BASE | 刷新当前数据 | Ctrl+K搜索刷新并Enter | 面板关闭且读数据更新 | GET projections | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | WORKING |
| F10 | 全局 → 侧栏折叠 | 全局 | 侧栏折叠 | 已登录本机用户 | BASE | 布局状态 | 折叠/展开；窄屏导航 | 图标标签可达；布局可恢复 | 本机layout存储 | [preferences.json](../output/playwright/walkthrough/preferences.json) | WORKING |
| F11 | 显示偏好 → 显示偏好 | 显示偏好 | 显示偏好 | 已登录本机用户 | BASE | 四个复选框 | 逐项切换、重载验证、恢复 | sidebar/panel/context/banner记忆；无密钥localStorage | 本机layout存储 | [preferences.json](../output/playwright/walkthrough/preferences.json) | WORKING |
| F12 | 侧栏状态 → 环境健康面板 | 侧栏状态 | 环境健康面板 | product:read + 当前ReadGrant | BASE | 当前环境 | 点击Sensor覆盖打开/关闭 | 真实心跳/覆盖、DB AVAILABLE、模型/Worker UNKNOWN | GET runtime-health | [new-core.json](../output/playwright/walkthrough/new-core.json) | READ_ONLY |
| F13 | 概览 → 概览四项KPI | 概览 | 概览四项KPI | product:read + 当前ReadGrant | BASE | A子环境/24小时 | 读数并与API/SQL比对 | 8/1/0/1完全一致；N/A/Not calculated保留 | GET overview | [kpi-source-validation.json](../output/playwright/walkthrough/kpi-source-validation.json) | READ_ONLY |
| F14 | 概览 → KPI跳转 | 概览 | KPI跳转 | 已登录本机用户 | BASE | 四个指标 | 分别点击再返回 | 四项均跳事件列表，不声称自动应用专用筛选 | 前端路由 | [overview.json](../output/playwright/walkthrough/overview.json) | WORKING |
| F15 | 概览 → 趋势悬浮 | 概览 | 趋势悬浮 | product:read + 当前ReadGrant | BASE | UTC日桶 | 悬浮实际数据点 | 日期与数量tooltip显示；非随机曲线 | GET overview.daily_incidents | [overview.json](../output/playwright/walkthrough/overview.json) | READ_ONLY |
| F16 | 概览 → 趋势图例 | 概览 | 趋势图例 | 已登录本机用户 | BASE | 安全事件序列 | 隐藏后显示序列 | 隐藏空态与恢复均正常 | 前端图表状态 | [overview.json](../output/playwright/walkthrough/overview.json) | WORKING |
| F17 | 概览 → 关注队列/全部事件 | 概览 | 关注队列/全部事件 | product:read + 当前ReadGrant | BASE | 待处理0 | 查看空态；点击查看事件/全部事件 | 均可到列表；队列最多当前页5条 | GET incidents/overview | [overview.json](../output/playwright/walkthrough/overview.json) | READ_ONLY |
| F18 | 事件 → 事件搜索 | 事件 | 事件搜索 | product:read + 当前ReadGrant | BASE | 实际ID/不存在的ID | 输入/清空 | 命中一条；未知词空态可重置 | GET incidents?search | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | READ_ONLY |
| F19 | 事件 → 事件状态筛选 | 事件 | 事件状态筛选 | product:read + 当前ReadGrant | BASE | VERIFYING/全部 | 选择再恢复 | 按当前状态查询，状态有文字 | GET incidents?status | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | READ_ONLY |
| F20 | 事件 → 事件优先级筛选 | 事件 | 事件优先级筛选 | product:read + 当前ReadGrant | BASE | P0/全部 | 选择P0再恢复 | 无命中显示空态，不造记录 | GET incidents?priority | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | READ_ONLY |
| F21 | 事件 → 重置筛选 | 事件 | 重置筛选 | product:read + 当前ReadGrant | BASE | 搜索/状态/优先级 | 点击重置 | 清除查询条件；旧筛选跨环境须手动清除 | GET incidents | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | WORKING |
| F22 | 事件 → 事件列表分页 | 事件 | 事件列表分页 | product:read + 当前ReadGrant | BASE | 单事件子环境 | 检查下一页/返回首页 | 只有1条，按钮禁用；跨页未实测 | GET incidents?cursor | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | UNAVAILABLE |
| F23 | 事件/详情 → 事件面板/完整页 | 事件/详情 | 事件面板/完整页 | product:read + 当前ReadGrant | BASE | 现有Incident | 选行、完整页、主要事件入口 | 右面板与完整页显示同一事件；窄屏抽屉可关 | GET incidents/{id}/snapshot | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | READ_ONLY |
| F24 | 事件 → 详情面板折叠 | 事件 | 详情面板折叠 | 已登录本机用户 | BASE | 布局状态 | 收起/显示；窄屏关闭 | 不丢当前事件，导航恢复可操作 | 前端layout | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | WORKING |
| F25 | 详情·摘要 → 事件摘要 | 详情·摘要 | 事件摘要 | product:read + 当前ReadGrant | BASE | A现有Incident | 打开摘要 | VERIFYING、授权、执行、验证分别展示 | GET snapshots/{id} | [new-core.json](../output/playwright/walkthrough/new-core.json) | READ_ONLY |
| F26 | 详情·决策 → AI决策/ModelRun | 详情·决策 | AI决策/ModelRun | product:read + 当前ReadGrant | BASE | A/B/E事实 | 查model/provider/延迟/分析/提案 | 本地真实调用；SHADOW/自报置信度/拒绝/降级明确 | GET snapshots/{id} | [new-core.json](../output/playwright/walkthrough/new-core.json) | READ_ONLY |
| F27 | 详情·决策 → Authorization/Risk | 详情·决策 | Authorization/Risk | product:read + 当前ReadGrant | BASE | Action关联记录 | 按action_id查看独立授权和风险 | A R2 ALLOW；B在Proposal层拒绝无Action，未伪造DENY | GET snapshots/{id} | [fault-observations.json](../output/playwright/walkthrough/fault-observations.json) | READ_ONLY |
| F28 | 详情·决策/摘要 → Action回执 | 详情·决策/摘要 | Action回执 | product:read + 当前ReadGrant | BASE | 固定Lab Action | 查Attempt/Result/executor/output_hash | EXECUTION_SUCCESS独立于Verification | GET snapshots/{id} | [new-core.json](../output/playwright/walkthrough/new-core.json) | READ_ONLY |
| F29 | 详情·验证 → 三维Verification | 详情·验证 | 三维Verification | product:read + 当前ReadGrant | BASE | A/C/D | 读取安全/业务/观测与TTL | PASS/FAIL/INCONCLUSIVE实测；过期不当当前PASS | GET snapshots/{id} | [fault-observations.json](../output/playwright/walkthrough/fault-observations.json) | READ_ONLY |
| F30 | 详情·证据 → Evidence/复制ID | 详情·证据 | Evidence/复制ID | product:read + 当前ReadGrant | BASE | 实际Fact | 查看来源/hash/时间；复制ID | ID复制成功Toast；敏感Raw定位不自动公开 | GET snapshots/{id}；clipboard | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | READ_ONLY |
| F31 | 详情·记录 → 记录沿袭 | 详情·记录 | 记录沿袭 | product:read + 当前ReadGrant | BASE | 实际Raw到Incident | 逐卡读取 | Raw/Normalization/Event/Group/Correlation/Incident/Audit可见 | GET snapshots/{id} | [new-core.json](../output/playwright/walkthrough/new-core.json) | READ_ONLY |
| F32 | 详情 → 详情跨页链接 | 详情 | 详情跨页链接 | product:read + 当前ReadGrant | BASE | 同一事件快照 | 记录→时间线；证据→图谱；摘要→验证 | 对象/快照一致，返回可继续阅读 | GET snapshot projections | [incident-controls.json](../output/playwright/walkthrough/incident-controls.json) | READ_ONLY |
| F33 | 时间线/图谱/报告 → 聚焦事件选择器 | 时间线/图谱/报告 | 聚焦事件选择器 | product:read + 当前ReadGrant | BASE | 现有ID/空 | 选空后恢复原ID | 先选择一条事件空态→正常记录 | GET incidents/snapshot | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | READ_ONLY |
| F34 | 时间线 → 时间线分页 | 时间线 | 时间线分页 | product:read + 当前ReadGrant | BASE | 112时间点 | 下一页两次再返回首页 | 三页共112点；API时间排序成立 | GET snapshots/{id}/timeline | [timeline-controls-final.json](../output/playwright/walkthrough/timeline-controls-final.json) | READ_ONLY |
| F35 | 时间线 → 时间点/来源检查 | 时间线 | 时间点/来源检查 | product:read + 当前ReadGrant | BASE | 实际记录 | 鼠标与Enter选点/来源记录 | 检查器展示source_ref/字段/时间语义 | GET snapshots/{id}/timeline | [timeline-controls-final.json](../output/playwright/walkthrough/timeline-controls-final.json) | READ_ONLY |
| F36 | 时间线 → 时间线缩放/浏览 | 时间线 | 时间线缩放/浏览 | 已登录本机用户 | BASE | 时间轴 | 放大缩小；拖动浏览时间轴 | 125–150%与浏览位置65%实际生效 | 前端时间轴状态 | [timeline-controls-final.json](../output/playwright/walkthrough/timeline-controls-final.json) | WORKING |
| F37 | 证据图谱 → 图谱节点/关系来源 | 证据图谱 | 图谱节点/关系来源 | product:read + 当前ReadGrant | BASE | resource/incident/evidence/verification/analysis/raw | 逐类选节点读关系 | source_ref/source_field/非因果明确，推断不冒充事实 | GET snapshots/{id}/graph | [graph-controls.json](../output/playwright/walkthrough/graph-controls.json) | READ_ONLY |
| F38 | 证据图谱 → 图谱搜索 | 证据图谱 | 图谱搜索 | 已登录本机用户 | BASE | 节点ID/不存在的词 | 搜空结果、清空、收起实体列表 | 实体搜索/无匹配/恢复正常 | 前端已有nodes | [graph-controls.json](../output/playwright/walkthrough/graph-controls.json) | READ_ONLY |
| F39 | 证据图谱 → 图谱聚焦/两层/重置 | 证据图谱 | 图谱聚焦/两层/重置 | product:read + 当前ReadGrant | BASE | 真实根节点 | 以此节点展开两层后重置 | 新root查询，上限200节点400边，重置恢复 | GET snapshots/{id}/graph?root_ref | [graph-controls.json](../output/playwright/walkthrough/graph-controls.json) | READ_ONLY |
| F40 | 证据图谱 → 图谱缩放 | 证据图谱 | 图谱缩放 | 已登录本机用户 | BASE | 当前画布 | 放大缩小 | 160%可操作，节点内容仍可检查 | 前端图谱状态 | [graph-pan.json](../output/playwright/walkthrough/graph-pan.json) | WORKING |
| F41 | 证据图谱 → 图谱鼠标平移 | 证据图谱 | 图谱鼠标平移 | 已登录本机用户 | BASE | 160%画布 | 拖动空白处 | scrollLeft实际增加160 | 前端滚动容器 | [graph-pan.json](../output/playwright/walkthrough/graph-pan.json) | WORKING |
| F42 | 证据图谱 → 图谱方向键平移 | 证据图谱 | 图谱方向键平移 | 已登录本机用户 | BASE | 聚焦画布 | 按/持续按右方向键两次 | scrollLeft仍0，与可方向键滚动标签不符 | 前端滚动容器 | [read-states.json](../output/playwright/walkthrough/read-states.json) | UNAVAILABLE |
| F43 | 报告 → 固定快照报告 | 报告 | 固定快照报告 | product:read + 当前ReadGrant | BASE | LIVE/REPLAY Incident | 打开报告逐节读取 | 八节草稿，与同一snapshot Facts对应 | GET snapshots/{id}/report | [live-report-integrity.json](../output/playwright/walkthrough/live-report-integrity.json) | READ_ONLY |
| F44 | 报告 → 报告目录 | 报告 | 报告目录 | 已登录本机用户 | BASE | 八个章节 | 逐个点击目录 | 对应H3滚动并获得焦点 | 前端报告目录 | [report-export-final.json](../output/playwright/walkthrough/report-export-final.json) | WORKING |
| F45 | 报告 → 下载JSON | 报告 | 下载JSON | product:read + 当前ReadGrant | BASE | 同一Report | 实际下载并解析/校验 | UI Facts/报告/精确文件hash一致 | GET snapshots/{id}/report-json | [live-report-integrity.json](../output/playwright/walkthrough/live-report-integrity.json) | READ_ONLY |
| F46 | 报告 → 下载Markdown | 报告 | 下载Markdown | product:read + 当前ReadGrant | BASE | 同一Report | 实际下载阅读/校验 | 八节、来源、限制和hash保留 | GET snapshots/{id}/report-markdown | [live-report-integrity.json](../output/playwright/walkthrough/live-report-integrity.json) | READ_ONLY |
| F47 | 演示 → 场景目录/profile | 演示 | 场景目录/profile | product:read + 当前ReadGrant | BASE | controlled-lab | 读取目录并选择登记profile | 只有固定A–E；脚本与真实模型标签明确 | GET demos/catalog | [demo-events.json](../output/playwright/walkthrough/demo-events.json) | READ_ONLY |
| F48 | 演示 → Scenario A | 演示 | Scenario A | demo:run + 登记profile；product:read读结果 | LAB | 固定A | 开始→刷新→完成→查看结果 | 两轮REAL_LOCAL_MODEL，PASS且CLEAN | POST demos/runs | [current-scenarios.json](../output/playwright/walkthrough/current-scenarios.json) | WORKING_LAB_ONLY |
| F49 | 演示 → Scenario B | 演示 | Scenario B | demo:run + 登记profile；product:read读结果 | LAB | 固定B | 开始→刷新→完成→查看结果 | 两轮SCRIPTED_NOT_AI，REJECTED，Action为0 | POST demos/runs | [current-scenarios.json](../output/playwright/walkthrough/current-scenarios.json) | WORKING_LAB_ONLY |
| F50 | 演示 → Scenario C | 演示 | Scenario C | demo:run + 登记profile；product:read读结果 | LAB | 固定C | 开始→刷新→完成→查看结果 | 两轮真实Sensor故障，三维INCONCLUSIVE | POST demos/runs | [fault-observations.json](../output/playwright/walkthrough/fault-observations.json) | WORKING_LAB_ONLY |
| F51 | 演示 → Scenario D | 演示 | Scenario D | demo:run + 登记profile；product:read读结果 | LAB | 固定D | 开始→刷新→完成→查看结果 | 两轮SCRIPTED_NOT_AI，业务FAIL，有限重规划 | POST demos/runs | [fault-observations.json](../output/playwright/walkthrough/fault-observations.json) | WORKING_LAB_ONLY |
| F52 | 演示 → Scenario E | 演示 | Scenario E | demo:run + 登记profile；product:read读结果 | LAB | 固定E | 开始→刷新→完成→查看结果 | 两轮实际模型不可用，FALLBACK保留确定性链 | POST demos/runs | [fault-observations.json](../output/playwright/walkthrough/fault-observations.json) | WORKING_LAB_ONLY |
| F53 | 演示 → 运行进度刷新 | 演示 | 运行进度刷新 | product:read + 当前ReadGrant | BASE | 实际run_id | 刷新运行状态观察四阶段 | 步骤完成与actual_outcome分开显示 | GET demos/runs/{id} | [demo-events.json](../output/playwright/walkthrough/demo-events.json) | READ_ONLY |
| F54 | 演示 → 停止后续步骤 | 演示 | 停止后续步骤 | demo:run + 登记profile；product:read读结果 | LAB | 未执行的固定B意图 | Worker暂停时QUEUED点击停止 | CANCELLED、0步、0资源；不宣称回滚 | POST demos/runs/{id}/cancel | [shutdown.json](../output/playwright/walkthrough/shutdown.json) | WORKING_LAB_ONLY |
| F55 | 演示 → 清理本次资源 | 演示 | 清理本次资源 | demo:run + 登记profile；product:read读结果 | LAB | 10完成+1取消运行 | 点击清理并等CLEAN | 归属容器/网络/卷均0，旧证据保留 | POST demos/runs/{id}/cleanup | [shutdown.json](../output/playwright/walkthrough/shutdown.json) | WORKING_LAB_ONLY |
| F56 | 演示 → 重置并新建运行 | 演示 | 重置并新建运行 | demo:run + 登记profile；product:read读结果 | LAB | 每个已清理A–E | 点击重置，等待第二轮完成清理 | 五个新run_id，predecessor正确，旧档案保留 | POST demos/runs/{id}/reset | [current-scenarios.json](../output/playwright/walkthrough/current-scenarios.json) | WORKING_LAB_ONLY |
| F57 | 演示·运行卡 → 运行历史回放 | 演示·运行卡 | 运行历史回放 | product:read + 当前ReadGrant | REPLAY | 五个登记档案 | 分别点历史回放、图谱、报告/导出 | RECORDED_REPLAY；全74表与10档案不变 | GET recordings/{id}/snapshot | [replay-integrity.json](../output/playwright/walkthrough/replay-integrity.json) | REPLAY_ONLY |
| F58 | 演示·子环境 → 封存记录目录回放 | 演示·子环境 | 封存记录目录回放 | product:read + 当前ReadGrant | REPLAY | 登记A档案 | 打开历史回放 | 回放标识和原记录一致 | GET recordings | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | REPLAY_ONLY |
| F59 | 全局·回放 → 回放刷新 | 全局·回放 | 回放刷新 | product:read + 当前ReadGrant | REPLAY | 固定档案 | 刷新后重新读图谱/报告 | 仍同源Facts/hash；无ModelRun/Action写入 | GET recordings/snapshot projections | [replay-integrity.json](../output/playwright/walkthrough/replay-integrity.json) | REPLAY_ONLY |
| F60 | 所有读取页 → 加载骨架屏 | 所有读取页 | 加载骨架屏 | product:read + 当前ReadGrant | BASE | 浏览器1200ms延迟注入 | 刷新观察loading | 2处骨架屏，非居中spinner | 浏览器只读响应延迟 | [read-states.json](../output/playwright/walkthrough/read-states.json) | WORKING |
| F61 | 所有读取页 → 读取错误/重试 | 所有读取页 | 读取错误/重试 | product:read + 当前ReadGrant | BASE | 503注入/真实API停止/403/404/429 | 读失败后恢复/重试 | 旧KPI撤下；范围错误明确；API恢复需重登录 | GET product APIs | [api-recovery.json](../output/playwright/walkthrough/api-recovery.json) | WORKING |
| F62 | 七导航页/详情 → 响应式/键盘焦点 | 七导航页/详情 | 响应式/键盘焦点 | 已登录本机用户 | BASE | 1920×1080、1366×768、960附加 | 逐页导航；键盘选实体/关闭抽屉 | 14页面无外层横向溢出；focus轮廓可见 | 前端布局/交互 | [responsive-final.json](../output/playwright/walkthrough/responsive-final.json) | WORKING |
| F63 | 记录/列表 → 相对时间/完整时间 | 记录/列表 | 相对时间/完整时间 | 已登录本机用户 | BASE | 实际timestamp | 阅读相对时间并查看title/键盘标签 | 显示完整+08:00时间；时间轴UTC注明 | 前端Time组件 | [quick-start.json](../output/playwright/walkthrough/quick-start.json) | READ_ONLY |

## 实际存在与未实现边界

实际侧栏只有概览、事件、时间线、证据图谱、报告、演示、显示偏好；另有事件详情和环境健康面板。Assets、Threats、Detection、独立Investigation、独立系统运维Settings不存在，不写成可用产品页面。

| 非计数项 | Status | 判定依据 |
|---|---|---|
| 网页人工审批/修改风险权限 | NOT_IMPLEMENTED | 只有状态标签，无审批或授权编辑入口 |
| 任意目标/命令/payload/防火墙执行 | NOT_IMPLEMENTED | 正式UI没有输入或任意执行器入口 |
| HTML/PDF报告导出/签名发布 | NOT_IMPLEMENTED | 只有JSON/Markdown及未复核草稿 |
| 网页DB备份恢复 | NOT_IMPLEMENTED | 管理员CLI与指南入口，非网页功能 |
| 独立资产/威胁/检测/攻击因果推断页 | NOT_IMPLEMENTED | router与实际导航未实现 |
| 模型/Worker实时健康探针 | NOT_IMPLEMENTED | 面板字段保留UNKNOWN，无UP/DOWN探针证据 |

## 功能类型与走查结果

- WORKING：22
- READ_ONLY：28
- UNAVAILABLE：2
- WORKING_LAB_ONLY：8
- REPLAY_ONLY：3

类型枚举与验收结论分开计算；验收WORKING包含通过的READ_ONLY/REPLAY_ONLY，且不重复计Lab。63 = 53通过非Lab + 8通过Lab + 1失败 + 1未能测试。启动问题作为OPS-START单列，不塞进网页功能分母。详见 [完整走查](FULL_PRODUCT_WALKTHROUGH_v1.0.0.md)。
