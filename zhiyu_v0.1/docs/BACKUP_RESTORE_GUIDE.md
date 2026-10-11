# v1.0 备份、恢复与故障处理

逻辑备份覆盖 PostgreSQL custom dump、逐表计数/摘要/审计状态、操作员配置/必要密钥、登记录制、对应报告与现场 artifacts、场景与冻结版本身份、公开配置。排除模型权重（外部固定 SHA256）、镜像、venv/npm缓存、可丢弃会话/快照缓存、私密诊断日志和已清理 Lab volume。它是包含真实凭据的私密未加密 ZIP；Windows ACL仅当前用户/SYSTEM，必须使用加密存储或加密传输，不得当作公开交付包。

在工程根目录执行；先停止 Worker、所有演示 CLEAN。backup 使用共享操作员锁、停止 API、确认 idle、导出并对照全部74表，完成后重启 API。运行锁不会阻止有 Docker 权限的外部管理员绕过流程写库，因此备份窗口必须由操作员协调。

```powershell
$env:PYTHONUTF8 = '1'
$deployment = 'C:\ZHIYU-private\reference-1'
$runtime = Join-Path $deployment 'venv\Scripts\python.exe'
$backup = Join-Path $deployment 'backups\before-maintenance.zip'
& $runtime tools/release_profile.py backup --deployment $deployment --backup $backup
```

路径必须位于该部署的 backups 目录，后缀.zip，文件不存在；已有备份永不覆盖。每次生成独立文件名。BACKUP_MANIFEST.json 保存时点、产品版本、head、每个成员SHA256/大小、包括/排除组件。`backup-result.json` 的 PASS 只证明本次备份完成，整体发布仍须全部 Gate。

在新空环境恢复，复用已验证的镜像与操作员 runtime：

```powershell
$newDeployment = 'C:\ZHIYU-private\recovery-1'
& $runtime tools/release_recovery.py restore-environment --deployment $newDeployment --reference $deployment --backup $backup --port 18012
& $runtime tools/release_profile.py snapshot --deployment $newDeployment
Invoke-RestMethod 'http://127.0.0.1:18012/health'
Invoke-RestMethod 'http://127.0.0.1:18012/ready'
```

恢复环境没有单独 venv，继续使用上述已验证 `$runtime`（记录到 operator_python）。恢复到新空 volume，拒绝已有public/product表的数据库；所有 pg_restore 操作在一个事务中，CRC/重复路径/目录穿越/成员摘要校验在写库之前。恢复 artifacts/scenario/public配置在 newDeployment/restored-evidence 下，recordings 在其 recordings 下；再次备份会登记恢复的证据，不能遗漏它们。公开配置副本供审计，不自动覆盖当前冻结代码/能力策略；操作员账号/密钥/控制环境按备份恢复，新DB密码和部署网络保留新值。

恢复后先逐表对照 database-state.json，再检查 health/ready、登录、历史 Incident/Timeline/Graph/AI/Verification/报告及回放。旧会话不会恢复，重新登录；旧内存snapshot不作为恢复来源。从完成运行打开历史回放，核对原 as_of、内容/文件hash与 RECORDED_REPLAY。不要因 LIVE 事实过期而写入虚构心跳。

故障边界：迁移使用 engine.begin 单事务；注入DDL/写入后异常已实际完整回滚。服务启动失败则保持原DB/备份，恢复已验证compose/config/image再start；配置错误在运行前拒绝；依赖校验失败不继续启动。必要时创建另一个新空目录从备份恢复，原失败实例留作隔离诊断，不删除原库。真实0016 LAB_PATH证据无法降级，必须保留原head或恢复其兼容备份。

工具不自动恢复 crashed Worker 的在途动作。若锁文件遗留，先按PID确认原操作进程已退出、无在途执行、canonical运行状态已核对；只删除本部署中确认陈旧的锁，再执行清理/恢复。不得按固定时间自动删锁或把 NEEDS_RECONCILIATION 改成完成。详细例子见 [排障](TROUBLESHOOTING_GUIDE.md)。

实测 [旧库导入/两次恢复](../artifacts/v1.0/gate-c-final.json)、[五类故障](../artifacts/v1.0/gate-c-recovery-faults.json)。备份不包含可离线重建镜像/下载权重的全部字节，Reference恢复需要本地已验证镜像和模型文件；灾难后完全断网重建整机未验证。
