# v1.0 部署指南

仅支持已验证的 Windows / WSL2 / Docker Desktop Linux Containers Reference；跨机访问、TLS/公网部署未验证。[安装指南](INSTALLATION_GUIDE.md) 是首次安装入口。以下命令在发布工程根目录执行，部署私密目录在工程外。

```powershell
$env:PYTHONUTF8 = '1'
$deployment = 'C:\ZHIYU-private\reference-1'
$runtime = Join-Path $deployment 'venv\Scripts\python.exe'
& $runtime tools/release_profile.py start --deployment $deployment
& $runtime tools/release_profile.py status --deployment $deployment
Invoke-RestMethod 'http://127.0.0.1:18010/health'
Invoke-RestMethod 'http://127.0.0.1:18010/ready'
```

实际 API port 以安装时 `--port` 为准；默认18010。容器 API 的8000和 PostgreSQL 的5432仅供内部固定转发，数据库主机随机端口每次重新发布后可能变化，`start` 会刷新 URL。禁止手工复用旧数据库 URL。ingress 健康只表示转发监听，不能替代 `/ready`。

另开终端运行固定 Worker：

```powershell
& $runtime tools/release_profile.py worker --deployment $deployment
```

这个终端必须持续运行，网页只提交受限场景意图。停止 Worker 可在其终端 Ctrl+C；若有在途执行，先查看运行/租约和 CLEAN 状态，不能认为 Ctrl+C 撤销了动作。不要同时运行 Worker 和 CLI `run`。API 不持有 Docker socket，Docker 权限仅在可信操作员主机工具。

停止前清理每个终态演示，按运行 ID 执行 `cleanup`，等待 CLEAN；然后 `stop` 只停 API，保留数据库与证据。Docker 重启后执行 `start`，重新登录及取得内存快照；持久录制仍从原始 SHA256 档案读取。不要使用 `down -v` 清理控制数据。

恢复环境复用已验证的操作员 Python 和固定镜像，没有自身 venv；使用创建恢复环境时记录的 `operator_python`，参见 [备份恢复指南](BACKUP_RESTORE_GUIDE.md)。恢复不能被称为 Clean Install。

端口、TLS和权限见 [安全基线](SECURITY_BASELINE_v1.0.md)。不把 internal 网络当作不可配置的宿主机安全边界；Docker 管理员可以修改网络，必须按可信操作员权限保护。
