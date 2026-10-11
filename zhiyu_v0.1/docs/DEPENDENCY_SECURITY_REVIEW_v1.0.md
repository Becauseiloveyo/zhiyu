# v1.0 Dependency security review

Trivy 0.75.0；数据库更新时间 2026-10-04T14:28:15.152965452Z。保留扫描原严重级别，没有删除告警或宣称零漏洞。

工程判定：只对已注册、固定流量、可信本机操作员的 CONTROLLED LAB 继续最终验收。库仍有漏洞；这不构成生产、恶意任意网络流量或客户部署的安全批准。开放端口/增加采集输入/启用额外 Wazuh 功能必须重新评估。

[全部逐条判定](../artifacts/v1.0/security/vulnerability-disposition.json)；[Critical/High逐条CSV](../artifacts/v1.0/security/critical-high-disposition.csv)；[精确镜像扫描](../artifacts/v1.0/security/container-vulnerabilities.json)；[实际配置检查](../artifacts/v1.0/security/runtime-feature-review.json)。

| 镜像 | Critical | High | 镜像SHA256 |
|---|---:|---:|---|
| wazuh | 8 | 177 | sha256:5ae8fe72fb0d2fb28f9d83b07f041e3911ecb765248d99e578d4f394379f5869 |
| postgres | 14 | 114 | sha256:67f41722b7a8cbdb868a44a4995c846eddfdc2973bccb291ce937dce88ad5675 |
| model | 0 | 2 | sha256:b15cd87030b2eb8a284d398c095e03c6ba8baf386b68e1b83ab8b46e9555ffe8 |
| wazuh-agent | 0 | 50 | sha256:6a61eac6b6d55b0bb59c85b3d33f7859c60b4ef9e81475f890d2de8a097122c7 |
| sensor | 6 | 85 | sha256:dead224de5b67c4f93629c92bf4c0a0429026b755546070a8527b351d81aaf6b |
| backend | 3 | 61 | sha256:84c687d5bad5c4d0ead08e8d1d73df8a418e23b696c90cc61eb54b60540d0a5f |

以上为 package/target 漏洞出现次数，不能当作独立CVE数量。

全部出现次数 2175；独立CVE 632；Critical/High 出现次数 520。

所有 Critical/High 的名称、版本、原级别、供应商补丁版本、原始URL、运行可达性及保留理由均在CSV。NO_REGISTERED_TRIGGER仅针对固定路径，不等于组件普遍不受影响。RETAINED_CONTROLLED_RUNTIME_RISK明确承认运行库或内部API仍在，不能当作已修复。

RC10关闭实际SMTP/QP与HTTP2解析，保留Debian对Suricata7.0.10+deb13u4的告警；Debian回移植可能导致其范围不同于上游说明，未据此删去CVE。其他解析器不宣称全部关闭。高权限Sensor只处理项目固定私网流量，不能连接客户/公网网卡。

补丁可用性以逐条FixedVersion列为准；UNKNOWN不代表无补丁。整体升级第三方镜像/主要依赖会改变已冻结运行基线，本版没有以未验证的大规模升级代替路径评估。剩余风险为明确交付限制，不是隐藏PASS。

Python冻结48项实际OSV扫描0告警；npm实际锁文件审计0告警。容器包含操作系统/第三方嵌入包，结果不等同Python/npm结果。Docker Scout CVE需登录和曾失败的DB下载保留尝试证据，最终完整扫描使用SHA验证的Trivy0.75.0与官方GHCR数据库。

官方参考：[Trivy](https://trivy.dev/docs/latest/)、[OSV API](https://google.github.io/osv.dev/api/)、[Suricata SMTP advisory](https://github.com/OISF/suricata/security/advisories/GHSA-qxm4-q7vx-7xj4)、[Debian tracker](https://security-tracker.debian.org/tracker/CVE-2026-57228)。
