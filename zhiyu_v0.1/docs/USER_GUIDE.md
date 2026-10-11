# 智御 v1.0 工作台用户手册

当前稳定原型候选和最终签署状态见 [机器状态](../V1.0_STATUS.json)，仅 CONTROLLED LAB。管理员按 [安装](INSTALLATION_GUIDE.md) 和 [部署](DEPLOYMENT_GUIDE.md) 启动 API/独立 Worker。打开默认 `http://127.0.0.1:18010`，从本机私密配置取得操作员用户名及工作台访问密钥，密钥不会保存在 localStorage。

左侧工作环境与 Scope 决定全部读取范围；全局时间窗为6/24/72/168小时。读取授权在服务端强制执行，演示子环境与其登记控制环境当前授权相连；复制录制文件不授予权限。401需重新登录，403需选择获准范围，410需重建快照。

- 概览：当前授权数据库事实、环比和7日分布；未定义指标不展示虚构风险分数，覆盖未知显示UNKNOWN。
- 事件：状态/优先级/文本筛选与分页；详情五个视图为摘要、决策、验证、证据、记录。
- 时间线：保留 source_timestamp/observed_at/ingested_at 等原字段与来源，时间相邻不意味着因果。
- 证据图谱：真实对象引用关系，缺失引用与截断显式提示，不画未经证实的攻击因果。
- 决策与验证：分析/提案/授权/风险/执行收据分开；REFERENCE_GROUNDED仅是引用校验，模型confidence不是准确率；执行成功与独立验证结论分开。
- 报告：八节安全事件响应与独立验证报告，文档状态UNREVIEWED_DRAFT，JSON/Markdown下载核对SHA256；没有人工签名、审批发布或自动关闭Incident的含义。

详情、时间线、图谱与报告共享固定快照。快照缓存过期会提示刷新；历史回放刷新继续读登记档案。LIVE表示当前数据库读取，不保证历史证据当前有效；SYNTHETIC仍按合成来源标记。RECORDED_REPLAY保存原as_of/事实，明确历史封存标签，不调用模型、不产生Action或验证结果。

顶部搜索支持 Ctrl/⌘K。侧栏与右侧显示偏好可以记忆，数据权限和密钥不会记忆到浏览器存储。UI错误时读取失败提示优先于旧健康数字；不要从截图旧状态宣称恢复。

演示必须回登记控制环境，选择controlled-lab，启动固定A–E。每个profile同一时刻最多一个未清理运行。网页不能填命令、外部目标、能力或风险覆盖。观察PREFLIGHT/TRIGGER/VERIFY/ARCHIVE、实际/预期结果和模型来源；流程COMPLETED并不一定安全PASS。终态申请清理到CLEAN，再重置新建运行，旧失败/报告保留。停止后续步骤不能撤销已发出的Action；不确定步骤转NEEDS_RECONCILIATION，不自动重发。

完整讲解及各场景来源见 [比赛演示](COMPETITION_DEMO_GUIDE.md)。AI默认OFF/启用SHADOW；正式主张与 [已知限制](KNOWN_LIMITATIONS.md) 是报告和演示的共同边界。
