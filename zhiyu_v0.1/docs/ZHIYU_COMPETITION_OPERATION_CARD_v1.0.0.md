# 智御 v1.0.0 比赛操作卡

**仅 CONTROLLED LAB；报告 UNREVIEWED_DRAFT；AI建议不授权执行；历史PASS不证明现在健康。** 冷安装不用于台上计时。管理员赛前准备本机API、登录身份、干净可运行Lab及登记A–E档案。START-001尚未修复，Docker重启后先核验底层服务。

| 顺序 | 现场操作与一句讲解 |
|---|---|
| Start / Health | 执行正式start；health=ok、version1.0.0；ready=ready/schema0016。LIVE须另开worker终端 |
| Overview | 选A子环境/Scope，重置残留筛选；四项实际KPI，N/A/UNKNOWN如实保留 |
| Incident | 事件→完整页→摘要；“事件状态、执行结果、验证结论分开读取” |
| AI Decision | 决策→ModelRun、Analysis、Proposal；“REAL_LOCAL_MODEL，REFERENCE_GROUNDED非保证正确，SHADOW无授权” |
| Authorization | 按action_id查Authorization/Risk；“固定R2策略允许，提案不直接执行；没有网页人工审批” |
| Action | 看Result的EXECUTION_SUCCESS、executor与LAB_PATH；“只作用于一次性实验路径” |
| Verification | 三维与valid_until；“A通过、C无法确认、D业务失败；执行成功不能覆盖失败” |
| Graph | 证据→图谱；选节点/关系来源、两层展开；“真实引用非攻击因果，推断/UNKNOWN保留”。用鼠标平移，方向键平移存在UI-001 |
| Report | 八节固定快照草稿→JSON/Markdown；“hash区分事实、整体报告、文件字节；无PDF/签名” |
| Replay fallback | 回控制环境→已完成运行“历史回放”，确认RECORDED_REPLAY；“原事实、原结果、无新增模型/Action” |

**需要现场LIVE时：** 控制环境→controlled-lab→开始A→刷新PREFLIGHT/TRIGGER/VERIFY/ARCHIVE→读实际/预期→看本次事件→终态清理至CLEAN。B REJECTED、C INCONCLUSIVE、D FAIL、E FALLBACK是固定反例的预期；B/D明确SCRIPTED_NOT_AI。新一轮用“重置并新建运行”，保留旧记录。

**异常处理：** 401重新登录；403选获准范围；410刷新快照；429稍后刷新；API/Model/Sensor不在线不讲实时成功，切明确标记的历史回放。报告校验失败停止下载，正常读取后重试；清理失败/NEEDS_RECONCILIATION交管理员，不重发不确定步骤，不提高权限。数据库故障、任意损坏档案不承诺台上修复。

**收场：** 每个新运行CLEAN→Worker终端Ctrl+C→正式stop（只停API，保留DB/证据）。不得down -v或操作其他项目。

[详细手册](ZHIYU_USER_MANUAL_v1.0.0.md) · [本轮实际结果与问题](FULL_PRODUCT_WALKTHROUGH_v1.0.0.md)
