# v1.0 排障与恢复

先记录当前候选、部署project、运行ID、实际错误和最后完成步骤；机器状态不因重试自动PASS。私密日志、配置与备份保留在工程外；分享前确认没有凭据或原始客户内容。操作命令见 [部署](DEPLOYMENT_GUIDE.md)。

| 现象 | 检查与受限恢复 |
|---|---|
| Docker正常但镜像下载失败 | `docker version`仅证明Engine可用；检查Docker自己的代理监听/registry连接。不存在的127.0.0.1代理不能用旧镜像掩盖。只修改获得授权的Docker设置，不自动重写Windows全局代理。 |
| pip哈希/缺wheel/下载失败 | 保留失败目录，检查固定direct-URL与官方HTTPS、完整下载；不关闭require-hashes，不自动升级。修复后另一个空目录完整重装。 |
| Sensor apt DNS/连接失败 | Reference Dockerfile使用签名验证的Debian USTC HTTPS软件源与有限重试，任一更新错误拒绝构建；不使用trusted或allow-unauthenticated。 |
| PostgreSQL healthy但主机连不上 | 核对ingress归属及实际127.0.0.1随机端口；仅internal网络不会提供主机端口。执行start刷新URL；禁止改为0.0.0.0。 |
| API不ready/启动失败 | 查已脱敏私密日志及容器退出状态，保留原DB；恢复已验证compose/config/image后start，必要时从验证备份恢复新空环境。 |
| 页面401/403/410 | 分别重新登录、选受权环境/Scope、显式刷新快照；不要扩大Grant或把ID当凭证。 |
| Model/Sensor offline | 保留FAIL/UNKNOWN/INCONCLUSIVE；缺Sensor不能判PASS，模型失败保留确定性基线。切历史回放要明确RECORDED_REPLAY。 |
| 列表无旧Incident | 列表按created_at时间窗，详情/登记回放可读旧根；先选正确环境/Scope与168小时，不修改原时戳。 |
| 备份路径/哈希/CRC错误 | 只接受本部署backups的新.zip文件；校验失败在写库前拒绝，保留原实例，从可信备份另建空恢复目录。 |
| 未清理/锁文件存在 | 查询运行/步骤、PID与本项目资源；不确定执行不能重发。仅确认进程已退出且无操作时手工移除对应旧锁，再cleanup。 |
| 0016无法降级 | 有真实LAB_PATH收据，恢复旧约束必失败并事务回滚；保留head或恢复兼容备份，不删证据/约束。 |

安全移除陈旧锁的操作顺序：读本部署operator.lock或worker.lock的PID；在Windows用 `Get-Process -Id <PID>` 核对进程/启动时间；确认无在途操作和运行状态后，仅对该部署路径执行 `Remove-Item -LiteralPath '<部署目录>\operator.lock'`（worker.lock同理）。PID重用不能自动视为原进程；存在疑问保留锁并人工核对。工具不执行全局解锁或自动杀进程。

真实故障与最小修复保留在 [Release Blocking Findings](RELEASE_BLOCKING_FINDINGS_v1.0.md)。已测试migration DDL/写入后失败、服务exit73、非法所有权配置、pip哈希不匹配与0016降级阻断；不能把这些受控恢复外推为任意灾难/SLA保证。
