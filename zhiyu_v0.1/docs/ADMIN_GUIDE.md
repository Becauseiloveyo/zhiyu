# v1.0 管理员手册

管理员负责本机可信Docker权限、私密配置/密钥、单实例Worker、受限场景归属和恢复，不通过网页发布任意命令。Reference用户初始化由install生成一个operator；当前产品不提供企业账号管理、MSSP多租户或HA。

公开配置 `config/reference-profile.json` 说明默认端口/控制环境/Scope/AI边界。真正运行配置在工程外部署目录：deployment.private.json、api.private.json、compose.private.json、model-key.private、lab-key.private。安装用不同随机密钥，恢复保留旧操作员和模型/Lab身份，DB密码新建。不要把样例字段当成已有执行授权。

浏览器身份仅product:read/demo:run；不能用cookie调用核心Action接口。环境/Scope/Grant由服务端校验，演示子环境继承当前受权读取范围；撤权同时影响LIVE与回放。更改身份配置后重启API、重新登录，旧会话为内存态，非跨进程账号服务。

日常操作见 [部署](DEPLOYMENT_GUIDE.md)。维护前全部运行CLEAN并停止Worker，先备份；新空恢复后对照计数/摘要/审计链，再开放本机浏览器。[备份恢复](BACKUP_RESTORE_GUIDE.md) 不提供破坏性降级或强行覆盖已有数据库。

共享operator.lock防止并发run/cleanup/worker/backup/restore/upgrade。锁写PID；若进程异常退出，先确认本机PID是否仍是原Python操作员、查询canonical运行/步骤和资源归属。只对确认陈旧且无操作进行的本部署锁作人工移除；存在不确定执行时保留NEEDS_RECONCILIATION，不能直接继续重发。

诊断日志先脱敏再写，不把pg_dump二进制写进日志；完整dump只在私密备份。即使日志已脱敏也可能含环境、事件ID和内部路径，仍不作为公开材料。浏览器会话、备份和截图必须与源码发布分离。公开证据使用各步骤结果和哈希，禁止复制私密配置、原始命令日志或实际密钥。

固定镜像、锁、权重、Prompt/策略/场景/报告身份见 [RC冻结](../artifacts/RC_STATE_v1.0.0.json)。更新这些身份必须重新冻结并复验受影响Gate；不会自动升级依赖以掩盖扫描问题。公开SBOM及许可证/漏洞处置索引由Gate D生成。禁止把CONTROLLED LAB放宽成生产部署授权。
