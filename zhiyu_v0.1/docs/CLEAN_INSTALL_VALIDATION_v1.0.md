# v1.0 Clean Install 验证

当前候选 RC6_v1.0.0，Gate B PASS；完整 v1.0 NOT PASS。记录时间为 2026-10-05（Asia/Shanghai）。RC5 的 RBF-009 FAIL 保留；RC6 完整新空环境安装、浏览器登录、真实受控场景和清理成功。正式机器结果：[Gate B](../artifacts/v1.0/gate-b-final.json)。

## 实际 Reference Profile

Windows 操作员 + WSL2 / Docker Desktop Linux Containers + Browser Web Console；RC6 使用新的独立空部署目录 `v1-reference-rc6`，API 回环地址 `http://127.0.0.1:18010`。Python 3.12.14，Node 24.18.0，Docker Engine 29.8.0；Linux 实体主机全新安装 NOT_RUN。

安装遵循 [Installation Guide](INSTALLATION_GUIDE.md)，使用标准库入口、新 venv、新 npm cache、哈希锁定的官方 wheel、无缓存 Docker 应用/Sensor 构建、新 PostgreSQL volume 及空 schema。四组随机密钥保存在工程外的 ACL 保护目录，公开证据不含凭据值。

## 前一尝试的阶段证据

RC6 正式结果：新项目 `zhiyu-v1-efac7e3aa5c8`；[前置条件](../artifacts/v1.0/gate-b-rc6-preconditions.json)、[独立 Python](../artifacts/v1.0/gate-b-rc6-python.json)、[前端检查及字节对应](../artifacts/v1.0/gate-b-rc6-frontend.json)、[无缓存构建](../artifacts/v1.0/gate-b-rc6-builds.json)、[镜像内源码/前端/安全默认值](../artifacts/v1.0/gate-b-rc6-image-correspondence.json)、[空库及初始 HTTP](../artifacts/v1.0/gate-b-initial-http.json)、[真实场景与报告读取](../artifacts/v1.0/gate-b-scenario-http.json)均通过。安装耗时1224.25秒。

实际浏览器登录并从演示页打开场景 A 事件详情。初始会话 GET 401 是登录前预期鉴权；登录成功后没有新增控制台错误。场景 A 使用真实 Suricata/Wazuh、新构建的源代码镜像与本地模型，18条原始/规范化记录、一个 OBSERVED Incident；AI 分析 REFERENCE_GROUNDED、提案 SHADOW、独立验证实际 PASS。读取 timeline/graph/AI/verification/report/JSON/Markdown 未改变 canonical 表哈希；封存文件 SHA256 与 API 登记一致。清理后专属容器、Lab 网络和 volume 均为空，历史保留。当前 LIVE 页若证据已过有效期，会如实显示 UNKNOWN/历史过期；封存结论不能代替当前健康结论。

下表为 RC5 已完成步骤，保留用于追溯与影响分析，不能作为 RC6 完整安装已通过的证据。RC6 正式安装结果待完成后独立记录。

| 检查 | 实际结果 | 证据 |
| --- | --- | --- |
| 新项目在建库前无容器/volume；28 个固定 wheel URL | PASS | [前置检查](../artifacts/v1.0/gate-b-rc5-preconditions.json) |
| 新 venv 的依赖一致性和129个安装源码文件对应 | PASS | [Python](../artifacts/v1.0/gate-b-rc5-bootstrap-python.json) |
| 新 npm cache，281 cache misses，15测试/lint/typecheck/build，15个产物字节对应 | PASS | [Frontend](../artifacts/v1.0/gate-b-rc5-frontend.json) |
| 固定 base、官方列出的区域 Debian 源、完整 apt 验证与无缓存 Sensor 预检 | PASS，仅诊断 | [预检](../artifacts/v1.0/gate-b-rbf008-sensor-preflight.json) |
| 正式新后端和 Sensor 镜像构建 | PASS，RC5 | [后端镜像对应](../artifacts/v1.0/gate-b-rc5-image-correspondence.json)；安装失败记录含全部镜像构建结果 |
| 空库迁移、API health/ready、初始环境、浏览器登录 | NOT_RUN，RC5 | [RBF-009 失败](../artifacts/v1.0/gate-b-rc5-failure.json)，新 PostgreSQL 表数0，未执行迁移 |
| 本地真实模型、Sensor、受控场景 A、报告、清理 | NOT_RUN，RC5 | 前述启动尚未完成 |

## 失败保留与最小修复

此前 RC4 第二次尝试的后端构建已完成，Sensor apt 下载遇到 DNS/连接错误，数据库尚未创建，该尝试正式记为 FAIL。不能用它的旧镜像替代本次 RC5 新安装。见 [失败记录](../artifacts/v1.0/gate-b-rc4-retry1-failure.json)、[RBF-008](RELEASE_BLOCKING_FINDINGS_v1.0.md)。

连接探测后仅修改 Lab Dockerfile：使用 Debian 官方列出的 USTC HTTPS 镜像、有限重试、软件源更新任一错误即失败；保留原固定 base、archive keyring、签名与包哈希验证。完整预检 apt 阶段约31.7秒。RC5 相对 RC4 唯一受控文件差异为该 Dockerfile，见 [影响检查](../artifacts/v1.0/gate-a-rc5-impact.json)。预检不等于正式 Clean Install 验收。

RBF-009 的固定入口网络预检通过，见 [实际连接与隔离](../artifacts/v1.0/gate-b-rbf009-network-preflight.json)，安装保护与传输测试20/20通过。RC5 空数据库停止且 volume 保留，RC6 不复用该数据库或旧依赖安装目录。

Gate C 已在 Gate B PASS 后进入；D/E 尚未启动。Linux 实体主机全新安装 NOT_RUN，不用容器验收替代。
