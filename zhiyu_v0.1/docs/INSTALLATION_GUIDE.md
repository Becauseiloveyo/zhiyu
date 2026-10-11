# 智御 v1.0 Reference Installation

适用架构：Windows 操作员工具 + WSL2 / Docker Desktop Linux Containers + 浏览器 Web Console。验收结果以 `artifacts/v1.0` 和最终 Validation Report 为准。Linux 实体主机的全新安装尚未执行，不能以容器测试替代该结论。仅用于 CONTROLLED LAB。

## 前置条件

在工程根目录操作。安装 Python 3.12、Node.js 24（含 npm）、启用 WSL2 的 Docker Desktop，并切换到 Linux Containers。操作员需要 Docker 权限；Web API 无 Docker socket。检查：

```powershell
python --version
node --version
npm --version
docker version
docker compose version
docker info --format '{{.OSType}}'
```

最后一项须为 `linux`。第一次依赖安装需要访问 PyPI、npm registry、容器 registry；Sensor 镜像构建还需其原 Dockerfile 所列软件源。运行期间模型在本机，不调用云模型。不要使用未知代理或绕过锁文件哈希。

Reference Lab 镜像使用 [Debian 官方镜像列表](https://www.debian.org/mirror/list) 中的 `mirrors.ustc.edu.cn`，分别读取 `/debian` 与 `/debian-security`。仍通过 HTTPS 下载，使用固定 base 内原 Debian archive keyring 验证签名和包哈希；网络失败最多重试5次，软件源更新任一失败即拒绝构建。不得设置 trusted/allow-unauthenticated 或关闭 TLS 检查。软件源切换仅针对这个 Lab Dockerfile，不修改宿主机软件源、DNS 或 Windows 系统代理。

本候选前端锁文件保留既有 npm mirror tarball 来源，实际干净安装访问 `cdn.npmmirror.com`；还需允许该固定锁文件列出的下载来源。npm 校验锁文件 integrity，不能用修改 resolved URL/删 integrity 的方式掩盖网络失败。最终供应链清单记录实际来源和许可证。

`docker version` 成功只证明 Engine 可用，不证明 registry 或容器网络可达。Docker Desktop 若使用本机代理，先确认该代理实际监听；代理连接被拒绝时不能用旧镜像/旧容器的运行结果代替干净构建。修复网络后重试固定镜像拉取及全新安装；操作员不应自动重写全局代理或重启其他项目。

自行取得经许可的 `qwen2.5-1.5b-instruct-q4_k_m.gguf`，放在工程目录之外。必须满足 SHA256：

```text
6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e
```

权重不在发布包中。准备足够磁盘空间及 Docker 内存以容纳 Python/npm 依赖、PostgreSQL、Sensor 和本地模型。端口 `127.0.0.1:18010` 必须空闲。

## 从空目录安装

以下是 PowerShell 示例，替换模型绝对路径及部署目录；部署目录必须新建或为空，不能位于工程内，也不能使用已安装的 v0.9 虚拟环境、数据库 volume 或私密配置：

```powershell
$env:PYTHONUTF8 = '1'
$deployment = 'C:\ZHIYU-private\reference-1'
$model = 'C:\ZHIYU-models\qwen2.5-1.5b-instruct-q4_k_m.gguf'
python tools/release_profile.py install --deployment $deployment --model $model --port 18010
```

入口只依赖 Python 标准库；不需要预装 uv。它会创建独立 venv，使用 `requirements-build.lock` / `requirements-runtime.lock` / `requirements-operator.lock` 的锁定版本及哈希安装运行依赖，关闭 pip 缓存；创建新的 npm cache，执行 `npm ci`、lint、typecheck、15 项测试和生产构建，逐文件校验构建是否与候选一致；使用 `--no-cache` 构建 Release / Sensor 镜像，再创建唯一 Compose project、独立 PostgreSQL volume、空库迁移、操作员账号和控制环境，启动 API。完整 `requirements-dev.lock` 用于工程回归，不作为操作员运行的必要依赖。

Python wheel 地址从原 `uv.lock` 离线选取，平台标签解析使用新 venv 内 pip 已自带的 packaging；既有 setuptools build wheel 的官方地址保存在 `config/reference-build-wheel.json`，必须匹配原 build lock 哈希。生成 direct-URL 清单后使用 `--no-index --only-binary :all: --require-hashes` 安装，并执行 `pip check`，避开容易被截断的大型 Simple Index。缺少匹配 wheel、地址来源异常或哈希不一致时直接失败；不降低校验，不自动升级依赖。

格式依据：[pip Secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/)、[pip requirements 格式](https://pip.pypa.io/en/stable/reference/requirements-file-format/)。唯一补充的 build wheel 地址来自 [setuptools 84.0.0 官方版本元数据](https://pypi.org/pypi/setuptools/84.0.0/json)，原 SHA256 保持不变。

数据库不复用已有容器或 schema。安装所需底层固定 base image 可能已在 Docker 内容存储中，应用依赖和构建层不使用旧开发缓存。每次失败保留其部署目录和私密日志；修复后使用另一个空目录重试。不要用手工修改 schema 或删除历史证据的方式继续半完成安装。

## 配置与凭据

公开默认配置是 `config/reference-profile.json`，端口通过 `--port` 指定；`--model` 必须是上述哈希的本地文件。工程 `.env.example` 属于原核心通用配置示例，Reference 入口生成自身配置，不会从工程 `.env` 导入真实密钥。

入口为数据库、操作员、模型和 Lab 生成独立随机密钥；Windows 部署目录去除继承权限，仅授予当前用户与 SYSTEM，POSIX 使用 0700。私密文件包括 `deployment.private.json`、`api.private.json`、`compose.private.json`、`model-key.private`、`lab-key.private`，以及 `operations.log`。不要上传、截图或把这些文件加入报告、源码或发布包。操作员在本机私密配置中读取 `username` 和 `access_key` 后填入登录页，禁止输出到共享终端日志。

浏览器打开 `http://127.0.0.1:18010`。会话使用 HttpOnly cookie 和 CSRF；操作员访问密钥不保存到 localStorage。HTTP 仅限本机回环，跨机器部署、TLS 终结和生产发布不在已验证范围。

Reference Compose 保留 `internal` control 网络，API/PostgreSQL 本身不发布端口。独立 `ingress` 服务使用同一固定 Release 镜像，只以标准库转发两个固定 TCP 上游：API `api:8000` 与数据库 `canonical-postgres:5432`；它没有凭据挂载、Docker socket 或请求可选的上游。仅此入口连接专用非 internal ingress 网络，发布 `127.0.0.1:18010` 和回环随机数据库端口，禁止 IP forwarding，运行只读且删除全部 capabilities。安装入口检查实际端口必须存在且只绑定回环，不把 PostgreSQL healthy 当作宿主机已能连接。模型及 Lab 继续使用原内部网络。入口的健康检查只证明转发进程在监听；系统是否可用仍以 API `/ready` 为准。

## 运行与基本检查

后续使用新部署自己的 Python：

```powershell
$runtime = Join-Path $deployment 'venv\Scripts\python.exe'
& $runtime tools/release_profile.py status --deployment $deployment
Invoke-RestMethod 'http://127.0.0.1:18010/health'
Invoke-RestMethod 'http://127.0.0.1:18010/ready'
& $runtime tools/release_profile.py run --deployment $deployment --scenario A
```

`run` 输出运行 ID 和最终实际结果，调用原控制器与独立主机 Worker。第一次真实场景会启动 Sensor 和本地模型。不要同时启动多个 Worker。没有 Sensor 事实的初始环境不应显示 Healthy，也不会有虚构事件。真实场景完成后在浏览器检查 Incident、Timeline、Graph、Verification 和报告，再清理该运行：

```powershell
& $runtime tools/release_profile.py cleanup --deployment $deployment --run-id '<上一步运行ID>'
& $runtime tools/release_profile.py stop --deployment $deployment
& $runtime tools/release_profile.py start --deployment $deployment
```

`stop` 停止 Web API，保留数据库与证据；Lab 资源必须先通过 `cleanup` 清理。`start` 更新 PostgreSQL 实际映射端口再启动 API；重启后重新登录和获取快照。长期浏览器演示需要另一终端运行 `worker --deployment $deployment`，以处理 UI 请求。

只有安装、登录、真实受控场景和清理全部验证通过，才可判定 Clean Install PASS；`install-result.json` 不单独代表 Gate B 或最终版本 PASS。

操作日志中pg_dump仅记录大小/SHA256，认证材料脱敏；私密日志与backups禁止放入发布ZIP。实际Sensor仅对固定HTTP1/DNS/TLS Lab流量验证，HTTP2/SMTP禁用，[安全基线](SECURITY_BASELINE_v1.0.md)列明剩余第三方漏洞。
