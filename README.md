# 智御 ZHIYU

网络安全自主决策与持续验证平台。项目将事件分析、AI 辅助研判、策略授权、受控执行和独立验证串成可追溯的工作流程。

当前工程为 **v1.0.0 Stable Prototype + Sentinel 前端（2026-10-11）**。已有验收结论仅适用于受控实验室；AI 提案不直接授权执行，执行成功也不等于安全验证通过。

![当前 Sentinel 界面](zhiyu_v0.1/docs/frontend-current/overview.png)

## 工程目录

| 路径 | 内容 |
|---|---|
| `zhiyu_v0.1/` | 当前 v1.0.0 工程，沿用历史目录名以保持工具和相对路径兼容 |
| `zhiyu_v0.1/frontend/` | React Web Console、测试、锁文件及参考安装所需的生产构建 |
| `zhiyu_v0.1/src/` | Python 控制面与业务模块 |
| `zhiyu_v0.1/tests/` | 后端测试和固定测试样本 |
| `zhiyu_v0.1/tools/` | 安装、运行、审计、备份与恢复工具 |
| `zhiyu_v0.1/docs/` | 架构、部署、使用手册、版本验收和后续计划 |
| `zhiyu_ai5/` | ai.5 架构与工程契约基线 |

## 开始使用

从 [安装指南](zhiyu_v0.1/docs/INSTALLATION_GUIDE.md) 开始。后续使用 [部署指南](zhiyu_v0.1/docs/DEPLOYMENT_GUIDE.md)、[用户手册](zhiyu_v0.1/docs/USER_GUIDE.md)、[备份恢复](zhiyu_v0.1/docs/BACKUP_RESTORE_GUIDE.md) 和 [已知限制](zhiyu_v0.1/docs/KNOWN_LIMITATIONS.md)。

```powershell
git clone https://github.com/Becauseiloveyo/zhiyu.git
Set-Location zhiyu/zhiyu_v0.1
```

参考安装需要 Python 3.12、Node.js 24 和 Docker Desktop 的 Linux Containers。模型权重需单独取得并校验安装指南中的 SHA256。账号、访问密钥和数据库由安装过程生成，没有通用默认密码。

前端检查与构建：

```powershell
Set-Location frontend
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

`frontend/dist` 有意纳入版本管理：安装工具会将全新构建与其逐文件比较。更新前端源码时应同时构建并提交该目录。普通源码校验不要求复跑真实实验室场景。

## 版本与证据

- [当前前端说明](zhiyu_v0.1/docs/FRONTEND_CURRENT.md)
- [v1.0.0 历史验收报告](zhiyu_v0.1/docs/VALIDATION_REPORT_v1.0.0.md)
- [产品路线与范围](zhiyu_v0.1/docs/POST_V1_PRODUCT_ROADMAP.md)
- [本地保留与仓库边界](zhiyu_v0.1/docs/REPOSITORY_STORAGE.md)

旧版报告和手册保留原验收日期与界面，不能替代当前前端的验证记录。原始运行日志、完整审计材料、历史封版 ZIP 和本机恢复备份保留在操作员本地；仓库中的源码快照不是这些历史发布包的重新封版。

实际密钥、浏览器会话、数据库、模型权重、临时试验目录和依赖缓存不进入 Git。克隆本仓库不会获得本机既有账号或实验室数据。
