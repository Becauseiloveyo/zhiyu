# v0.9 → v1.0 历史升级

正式路线为原库只读备份 → 新项目/空 volume 恢复 → v1.0 bootstrap → 对照验证 → 使用新实例。原 v0.9 保留，避免在原业务证据上试验升级。v0.9 和 v1.0 均为冻结 `0016_lab_remediation`，数据库迁移是0016→0016 no-op；应用版本升级仍须真实历史兼容性验证，不能用空库代替。

先按 [安装指南](INSTALLATION_GUIDE.md) 完成一个 v1 Reference。停止旧演示 Worker、清理全部旧运行；旧库可继续只读查询。准备原 `deployment.private.json` 以及 `m9-validation/local-secrets.json` 所有权记录，二者均不得上传。入口仅允许已登记 m9-validation 容器、专用历史数据库和回环端口，拒绝任意数据库/远端主机。

```powershell
$env:PYTHONUTF8 = '1'
$reference = 'C:\ZHIYU-private\reference-1'
$runtime = Join-Path $reference 'venv\Scripts\python.exe'
$backup = Join-Path $reference 'backups\v09-before-upgrade.zip'
& $runtime tools/release_recovery.py legacy-backup --deployment $reference --legacy-config 'C:\old-private\m9-demo\deployment.private.json' --owner-record 'C:\old-private\m9-validation\local-secrets.json' --backup $backup
$newDeployment = 'C:\ZHIYU-private\restored-v1'
& $runtime tools/release_recovery.py restore-environment --deployment $newDeployment --reference $reference --backup $backup --port 18011
& $runtime tools/release_profile.py snapshot --deployment $newDeployment
Invoke-RestMethod 'http://127.0.0.1:18011/ready'
```

新目录必须为空，18011必须空闲。restore-environment 实际验证归属、模型哈希和三个参考镜像身份，创建独立随机 DB 密码、独立 Compose project/volume，经单事务 pg_restore，再执行正式 upgrade。操作员身份/访问密钥、模型/Lab密钥和控制环境从备份恢复；数据库密码和新内部网络使用新值。跨机迁入的原历史 artifacts/recordings 必须完整位于随旧部署保存的原工程目录，不能只带数据库和配置。历史 m9 路径属于明确支持的本机迁入形态，任意第三方 PostgreSQL 部署未验证。

对照 backup 内 database-state.json 的全部表 count/SHA256、head、外键和审计链；检查 Incident/Evidence/ModelRun/Action/Verification/Audit、Demo状态及旧报告/录制。后续固定演示自然新增事实，必须先完成历史逐表对照再运行。LIVE 历史事实可能过期显示 UNKNOWN，RECORDED_REPLAY 保留原时点；不得将过期历史改为当前 HEALTHY。

已执行：原v0.9库74表、13 Incident、18 ModelRun、234 RawRecord/NormalizedEvent、14 DemoRun，包含12 COMPLETED与2 NEEDS_RECONCILIATION。旧表/状态/审计完全一致，完整报告、12份登记录制、1467证据文件恢复；两个真实新空 volume 恢复及浏览器/下载/场景 B/CLEAN通过。证据 [Gate C](../artifacts/v1.0/gate-c-final.json)。静态未登记 console-canonical.json 属于测试 fixture，不冒充运行录制。

迁移失败、服务启动失败、配置错误、依赖哈希不符的恢复步骤见 [备份恢复](BACKUP_RESTORE_GUIDE.md) 和 [排障](TROUBLESHOOTING_GUIDE.md)。真实 LAB_PATH 收据使0016降级被数据库 CHECK阻断，事务回滚；不要承诺安全降级到0015，更不能删除收据或约束。
