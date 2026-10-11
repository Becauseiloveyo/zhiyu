# v1.0 Release Blocking Findings

## RBF-001 — 参考部署缺少独立入口

Requirement：Gate B/C，新目录安装、私密配置、历史数据升级和恢复。

Root cause：v0.9 的 m9 入口默认读取开发机已有数据库/私有配置；使用说明依赖未列出的 uv。没有正式逻辑备份及空环境恢复入口。

Impact：不能由全新 Reference Profile 重现部署与恢复。

Minimal fix：新增受限操作员 CLI、无缓存构建 Dockerfile、公开配置模板；复用原 m9 controller/worker，不新增产品执行 API。配置、密钥、备份保存在受 ACL 保护的外部部署目录。

Regression required：全新安装、实际场景、备份完整性与拒绝反例、空库恢复、含历史数据升级、故障恢复及最终全回归。当前：OPEN，待 Gate B/C 实测关闭。

## RBF-002 — health 里程碑元数据过时

Requirement：最终版本与文档/运行状态一致。

Root cause：`/health` 仍写死 M4 名称。

Impact：当前部署的版本描述互相矛盾；无安全执行影响。

Minimal fix：仅更新健康端点的里程碑标签为 Stable Prototype，保留原权限和默认关闭策略。

Regression required：现有 API 测试与新候选实际 health/ready。当前：OPEN，待实际启动验证关闭。

## RBF-003 — 首次依赖下载读取超时

Requirement：Gate B，干净依赖安装可完成且不能复用开发缓存。

Root cause：全新 pip 使用默认读取超时，`files.pythonhosted.org` 的 wheel 传输实际 ReadTimeout。官方版本 JSON 确认 setuptools 84.0.0 存在且 wheel SHA256 与锁文件一致；短超时 index probe 的“无匹配”不能作为版本不存在的依据。

Impact：首轮安装 FAIL，数据库/服务尚未创建；不是依赖版本或业务架构失败。

Minimal fix：参考部署的 pip 与新 Release Dockerfile 使用既有工程曾采用的120秒读取超时与5次网络重试，保持 --no-cache-dir / --require-hashes 和所有锁定版本。新空目录重试，保留首轮失败。

Regression required：重新冻结 RC2，全新依赖下载、独立构建和完整 Gate B；最终回归再次验证候选。当前：OPEN。

## RBF-004 — 新安装总时限不足且混入开发检查依赖

Requirement：Gate B，在真实 Reference 网络条件下完成干净安装，并保留故障诊断。

Root cause：RC2 的单次 pip 总时限为1200秒，实际仍在持续下载时超时；入口使用完整 dev lock，含11MB mypy 等 Reference 运行不需要的检查工具。TimeoutExpired 路径未把已捕获输出写入私密日志。

Impact：第二次安装 FAIL，尚未创建数据库或服务；新环境未初始化 schema。原开发环境未被复用。

Minimal fix：Reference venv 仅安装既有 runtime/build/operator 锁定依赖，完整 dev lock 留给最终回归；依赖安装/镜像构建总时限调整为7200秒；超时诊断保存在原受 ACL 保护目录。保持版本、哈希、无缓存、空目录重试及所有安全默认值。

Regression required：RC3 重新冻结，空目录完整 Gate B，最终 dev lock 全回归。当前：OPEN。

## RBF-005 — Docker 的既有系统代理不可连接

Requirement：Gate B 的真实依赖前提、无缓存镜像构建和新 Compose 环境。

Root cause：实际拉取固定 Python base image 时，Docker Desktop 报告 static system HTTPS proxy `http://127.0.0.1:10808` 连接被拒绝；只读端口检查没有监听者。全新诊断容器的 HTTPS 请求也失败。Windows 直接 pip 下载仍在推进。

Impact：新 Reference 镜像无法证明可构建，Gate B 不得 PASS。诊断容器不计入安装/应用验收证据；旧产品的成功运行不能覆盖此项。

Minimal fix：用户已明确允许 Docker 改直连及必要重启。私密备份原 settings-store 后，仅将 `ProxyHTTPMode` / `ContainersProxyHTTPMode` 设为当前版本的 `disabled`；原容器 ID/volume/就绪状态保留，不修改 Windows 系统代理。Docker 实际日志确认 host/Linux disabled；固定 Python image pull 与全新 pinned-base 诊断容器 HTTPS 均通过。

Regression required：固定镜像拉取、Docker build 的实际网络访问、无缓存构建、完整 Gate B。当前：网络恢复 PASS；OPEN，待无缓存应用/Sensor 构建及完整 Gate B。证据：`artifacts/v1.0/gate-b-docker-network-recovery.json`。

## RBF-006 — PyPI Simple Index 响应截断

Requirement：Gate B 全新依赖安装及无缓存镜像构建必须可重现。

Root cause：RC3 新 venv 与前端已完成；Docker pip 25.0.1 在约1810秒后解析 PyPI Simple Index JSON 失败，`Unterminated string ... column 1080975`。普通网络重试未覆盖成功 HTTP 响应后的 JSON 解析错误。不能把已下载 wheel 或旧镜像算作成功构建。

Impact：第三次 Gate B FAIL，未创建数据库/volume/schema。前端15测试、lint、typecheck、生产构建及产物字节比较 PASS；独立 Python 锁定依赖与 pip check PASS。证据：`artifacts/v1.0/gate-b-third-install-sanitized.log`。

Minimal fix：从既有 uv.lock 和 requirements 锁中的 URL/版本/SHA256 离线选择当前 Python 平台匹配 wheel，生成 direct-URL requirements；唯一不在 uv.lock 中的既有 setuptools build wheel 地址来自官方版本 JSON，哈希必须与原 build lock 一致。使用 --no-index / --require-hashes / --only-binary，并执行 pip check；不修改任何已有依赖版本/哈希，不引入镜像站或复用缓存。新空目录、全新 venv/npm cache/Compose project 重跑。

Regression required：锁与 URL 哈希不一致拒绝、平台兼容性、Windows/Linux 选取、RC4 冻结、新空目录完整 Gate B。当前：OPEN。

## RBF-007 — Reference 安装中断且 Docker Desktop 已停止

Requirement：Gate B 必须完成一次可追溯的新空环境安装。

Observed：RC4 后端无缓存构建完成，镜像 `sha256:cbc7f97647f508b9f286cad244b8fd9d63bdaa4e032fe9c4be13cdea440965d3` 的源码/前端/依赖检查 PASS；Suricata apt 构建正在执行时，安装进程及 Docker Desktop/Engine 随后均不再运行。22:45 本机检查没有相关进程，Engine named pipe 不存在，Desktop status 不可取得。没有 compose 文件或 install-result，数据库尚未创建。中断原因未确认，不推断为产品故障或用户操作。

Impact：RC4 首次尝试 INTERRUPTED / NOT COMPLETED，不得判 Gate B PASS；已完成子步骤与387个冻结文件保留。后续操作系统检查确认 LastBootUpTime 为本地 2026-10-04 19:30:01，安装期间发生主机重启；不推断重启原因。

Recovery：沿用用户已明确批准的 Docker 直连/必要启动重启权限；确认两个 proxy mode 仍 disabled，恢复 Desktop，保持原 PostgreSQL container/volume。候选代码未变化；新空目录重跑同一 RC4，不冒充原中断流程已完成。

Regression required：Engine ready、旧 canonical volume 保留、新空目录完整 Gate B。当前：OPEN。

## RBF-008 — Debian CDN 包下载连接失败

Requirement：Gate B 的 Suricata 镜像必须实际从固定 base 无缓存构建成功。

Observed：RC4 第二次安装的新 Python、前端及后端镜像通过；Suricata 在约997秒后 apt 退出100。多项包报告 `Could not resolve deb.debian.org` / `Unable to connect to debian.map.fastly.net:443`，Acquire::Retries=3 已耗尽。没有创建新数据库/schema/服务。证据：`artifacts/v1.0/gate-b-rc4-retry1-install-sanitized.log`。

Root cause：本机 Docker 直连下 Debian CDN 的持续下载出现 DNS/连接失败；短 HTTPS 探测成功不能代替完整包下载。与已修复的 PyPI JSON 截断不同。

Impact：RC4 第二次尝试 FAIL，Gate B FAIL；不得沿用旧 Sensor 镜像冒充本次构建成功。

Minimal fix：先验证 Debian 官方列出的区域镜像，再仅调整 Lab 镜像的包下载源和有界网络重试。保留 HTTPS、Debian archive keyring 签名及包哈希检查、固定 Python base；不得关闭验证或复用旧应用镜像。

Regression required：实际 apt 签名验证与完整下载、无缓存 Sensor 构建、重新冻结候选、全新 Reference 安装及真实场景。当前：OPEN。

## RBF-009 — 内部网络未提供主机发布端口

Requirement：Gate B，操作员可连接新空 PostgreSQL，Web API 仅通过回环发布且运行网络保持隔离。

Observed：RC5 后端/Suricata/Wazuh 无缓存构建均成功。新 PostgreSQL healthy，但 `HostConfig.PortBindings` 请求 `127.0.0.1::5432`，`NetworkSettings.Ports[5432/tcp]` 实际为 `[]`，docker port 显示没有发布端口。仅连接 internal=true 的 control 网络。安装入口 refresh 索引空列表报 IndexError；没有初始化 schema 或启动 API。

Root cause：安装入口错误地假设仅在 internal 网络上也会提供主机端口，且未检查实际映射。正在基于当前 Docker 行为验证可用的隔离配置，不能直接取消所有网络隔离。

Impact：RC5 首次尝试 FAIL；新空数据库 volume 保留，未对历史数据库执行操作。证据：`artifacts/v1.0/gate-b-rc5-failure.json`。

Minimal fix：保留 internal control/Lab 网络，API/PostgreSQL 本身不发布端口；增加无凭据、只读、cap_drop ALL 的固定 TCP ingress，通过专用入口网发布两个回环端口，禁止 IP forwarding。请求无法选择上游，仅允许版本内固定 API/DB。refresh 验证实际映射和所有权，空映射或非回环绑定明确拒绝。没有修改 Docker daemon、Windows 全局路由或其他项目。

Regression required：回环端口可用、未开放0.0.0.0、非许可出站不可达、canonical DB/Worker 可用、新空环境完整安装与场景。当前：OPEN。

Preflight：实际 Windows 通过回环入口读取新库，public/product 表数为0；独立 control-only 容器可连接 canonical DB，连接两个外部443测试地址均被阻断。诊断入口和网络已清理。原15新增测试加本次5项传输/端口拒绝测试，20/20 PASS。证据：`artifacts/v1.0/gate-b-rbf009-network-preflight.json`、`rc6-installer-tests.xml`。正式 RC6 Clean Install 仍待执行，预检不能代替完整 Gate B。

## Gate B 关闭记录 — 2026-10-05

RC6 的完整 Clean Install、空库迁移、实际 health/ready、浏览器登录、真实 Sensor/本地模型场景 A、报告/封存读取与清理 PASS。机器证据：`artifacts/v1.0/gate-b-final.json`。RBF-002 至 RBF-009 的 Gate B 回归要求已满足，状态 CLOSED_GATE_B；先前失败和中断记录保留。最终 Gate E 仍须全回归。RBF-001 的安装部分已通过，升级/备份/恢复部分仍 OPEN，等待 Gate C。

## RBF-010 — 备份覆盖不足且缺少历史部署迁入入口

Requirement：Gate C，实际历史 v0.9 升级；完整 PostgreSQL/config/reports/artifacts/scenario/manifests 备份；新空环境恢复。

Observed：实际执行 RC6 backup 得到可校验的153229字节私密 ZIP、CRC/成员哈希通过，但仅含数据库、配置、密钥和一份封存快照，没有报告/现场 artifacts 或 scenario manifest。备份工具的 PASS 只覆盖已实现步骤，不满足完整 Gate C。现有 Reference CLI 也未提供受限的历史 m9 部署迁入/新空恢复环境建立入口。证据：`artifacts/v1.0/gate-c-rc6-backup-gap.json`。

Root cause：首次入口只枚举 deployment/recordings，未登记关联运行的报告与采集证据；install/restore 假定配置已是 v1 Reference 形态。backup 还会修改任意 output.parent 的 ACL，目标目录需要限制在已保护的部署目录内。Worker 意图写入早于互斥锁，需要与备份协调。

Impact：Gate C 不得 PASS；既有备份保留作为不完整覆盖的证据，历史数据库尚未修改。

Minimal fix：只补操作员部署/备份/恢复逻辑，基于受限所有权的历史容器与数据库只读导出；完整登记 reports/artifacts/scenario/版本身份，限制私密输出路径，协调操作员互斥；在新项目/空 volume 恢复，保留原始所有表哈希与审计链。冻结0016及原464测试不变，不引入新业务功能或迁移。

Regression required：实际历史数据前后对照、完整覆盖和成员哈希、新空环境恢复/浏览器、失败升级与恢复、0016降级阻断、最终全回归。当前：OPEN。

Gate C 关闭记录：RC8 的真实历史导出、两次新空 volume 恢复、74表完整摘要/审计链/外键对照、五类故障处理、浏览器回放/报告下载、恢复后场景 B 与 CLEAN 均 PASS，见 `artifacts/v1.0/gate-c-final.json`。RBF-001 恢复部分与 RBF-010 状态 CLOSED_GATE_C；Gate E 全回归仍未运行。

## RBF-011 — 私密操作日志包含数据库密码

Requirement：Gate D Secret Baseline，实际凭据不得进入日志。

Observed：对 RC6 Reference 的 `operations.log` 以实际私密配置做字节匹配，数据库密码命中，访问密钥未命中。该日志受 ACL 保护且未公开、未进入源码/前端/报告或交付 ZIP，仍不满足日志基线。

Root cause：操作员工具把 subprocess stdout/stderr 原样写入诊断日志；Docker inspect 含 POSTGRES_PASSWORD，pg_dump 二进制 stdout 也被错误地当作诊断写入。

Impact：Gate D 保持 IN_PROGRESS，不得封版。原始私密失败材料保持隔离；当前部署日志需要脱敏。

Minimal fix：仅在诊断写入处遮蔽已知凭据和带密码 URL，不改变返回给工具的原始数据；pg_dump 的 stdout 只记大小与 SHA256；同步处理 timeout 分支。当前受管部署日志脱敏，完整备份仍保持私密。核心/API/冻结迁移不变。

Regression required：日志实际零凭据、dump 可完整恢复、timeout/失败诊断仍可用、镜像源码对应、B/C 受影响流程复验、最终全回归。当前：OPEN。

RC9 回归：新增3项实际命令/timeout/dump日志边界测试，总27项发布工具测试PASS；三个受管部署旧日志脱敏，已知凭据剩余0。重建RC9后端，源码/前端对应、bootstrap/no-op摘要不变、完整1493成员备份及第三个新空volume恢复/74表对照PASS。最终日志扫描和Gate E仍待完成。

## RBF-012 — Sensor 未使用协议解析器默认开启

Requirement：Gate D Critical/High实际调用路径与处置；Sensor-only CONTROLLED LAB范围。

Observed：Trivy0.75.0实际扫描固定Sensor镜像，Suricata出现CVE-2026-57228/94083/94084；Debian Security Tracker列为vulnerable/will_not_fix。实际dump-config显示HTTP2与SMTP解析器开启；固定场景仅使用HTTP1认证、DNS和固定自签名TLS，不需要这些协议。pkg扫描不代表漏洞已被触发，但默认开启无关解析器留下可避免的攻击面。

Root cause：7.0.10 Debian包沿用全协议默认配置，没有按受控场景最小化。上游SMTP/MIME公告给出关闭quoted-printable解码的workaround；7.0.10未提供DoH2解析器，仍需保留Debian扫描记录，不根据上游版本范围擅自删告警。

Minimal fix：仅在Lab的固定Suricata启动参数关闭HTTP2、SMTP及SMTP quoted-printable，保持HTTP1/DNS/TLS观测与原规则/能力不变。重建Sensor镜像，核对实际生效配置/源码及真实场景A。其余基础系统/第三方告警逐项记录路径、补丁和限于本机固定Lab的处置，不能宣称容器零漏洞或可处理任意网络流量。

Primary sources：https://security-tracker.debian.org/tracker/CVE-2026-57228；https://security-tracker.debian.org/tracker/CVE-2026-94083；https://security-tracker.debian.org/tracker/CVE-2026-94084；https://github.com/OISF/suricata/security/advisories/GHSA-qxm4-q7vx-7xj4。

Regression required：实际parser配置、固定流量保持且指定HTTP2/SMTP解析禁用、保留OBSERVED provenance/真实Sensor/本地模型场景A、stop/recovery、受影响Gate B/E，SBOM与扫描/处置对应新镜像。当前：OPEN。

## Gate D current delta

RC10：RC9日志修复实际backup/第三个空库restore通过，27个工具测试通过，所有当前操作日志实际检查脱敏；RBF-011 CLOSED_GATE_D（最终ZIP扫描仍须Gate E）。RBF-012实际禁用HTTP2/SMTP/QP配置与真实场景A PASS，仅为当前运行路径缓解，包漏洞保留。Final Sensor stop/recovery 仍须Gate E。

## RBF-013 — release version import style

Final frontend 15/lint/typecheck/build passed, additional full-source Ruff found I001 in src/zhiyu/main.py import layout. Minimal ruff fix reformats only the import list, no API/logic/architecture change. RC10 final backend attempt interrupted and isolated runtime stopped without deleting volume; does not count as PASS. RC11 rebuild + affected source/image/current regression required.

## RBF-014 — Linux test image packaging omission

Actual built Linux test image contained all five new release wheel tests but omitted requirements-operator.lock, causing 5 fixture errors. Original tests not deleted/ignored. Minimal Dockerfile tests-stage COPY of unchanged operator lock; runtime/release/Sensor images and business source unchanged. RC12 freeze; rebuild Linux tests and restart full regression. Pre-fix evidence artifacts/v1.0/rbf014-pre-fix-linux.txt retained.

## Final RC12 closure

RBF-001至014的观察/失败/中断不覆盖。当前最小修复的受影响B/C/D已实测或以精确字节/AST影响说明承接；最终491 host /490 Linux /189 runtime /15 frontend全部通过。RBF-013 CLOSED_GATE_E：仅import排版，源码重建对应且全回归通过。RBF-014 CLOSED_GATE_E：Linux tests-stage补入既有operator lock，原5项fixture错误消失且490全通过。RBF-011实际5部署日志与最终public/package已知凭据0命中；RBF-012仅HTTP2/SMTP/QP运行路径缓解，实际A/C Sensor smoke/stop/recovery通过，未修复的包漏洞按520 Critical/High明示保留可信固定Lab处置。历史OPEN字样描述当时状态，以本关闭段和最终机器证据为准。

PKG-001：首次暂存包的CRC/成员SHA/source均通过，但附加证据一致性读回发现旧governance摘要引用了之后重新生成的link/secret报告。首次包已撤回并私密保留，当前源码391字节身份未变，不是产品行为或冻结Contract修复。最小修复为稳定证据摘要+派生最终报告走Manifest，发布前重新逐一核对所有索引/引用hash，并重复最终包装全部检查。见 `artifacts/v1.0/package-first-staging-review.json`。
