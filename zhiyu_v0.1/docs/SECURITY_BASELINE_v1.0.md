# v1.0 Security Baseline

范围是单操作员、可信本机、固定注册目标与流量的 CONTROLLED LAB。Production/Customer/SLA/Cloud/Windows Sensor/OT-ICS NOT VALIDATED，HA/Multi-tenancy NOT IMPLEMENTED。第三方镜像存在未修复Critical/High；[完整判定](DEPENDENCY_SECURITY_REVIEW_v1.0.md)记录原严重级别、补丁与可达路径。禁止将该基线解释为可直接接入任意敌对流量的生产IDS或对外开放部署。

| 服务/工具 | 默认端口与曝光 | 身份/TLS/权限 |
|---|---|---|
| Browser API | 主机127.0.0.1:18010，内部8000 | 本地私密访问密钥；HttpOnly、SameSite Strict会话，CSRF与Origin校验；会话30分钟；本机HTTP，Cookie Secure=false |
| ingress | 固定8000/5432上游；PG随机loopback端口 | 单一TCP转发；zhiyu非root、read-only、cap_drop ALL、ip_forward=0；无密钥或Docker socket |
| PostgreSQL17.11 | 内部5432，主机经ingress随机loopback | 随机新密码、网络scram-sha-256；容器本地socket/localhost trust；不对外开放，无TLS；可信入口初始化root后切换postgres，未声称cap_drop ALL |
| Worker/operator | 无监听 | 当前用户私密目录ACL；可信本机Docker权限；只能固定注册Adapter；操作锁与owner/project校验 |
| Suricata | target共享网络namespace，无主机端口 | root + NET_ADMIN/NET_RAW/SYS_NICE仅一次性私网Lab；固定规则与固定HTTP1/DNS/TLS流量；HTTP2/SMTP/QP关闭 |
| Wazuh Manager/Agent | 私网1514TCP、1515TLS注册；base API55000可能运行，未发布/未使用 | 固定Agent/目标日志；1515无注册密码只在一次性隔离Lab；indexer/feeds/active-response/cluster关闭；不是生产Wazuh加固配置 |
| 本地模型 | 私网HTTP8080，无主机端口 | 私密API key、固定weights SHA256，只读挂载、cap_drop ALL；无云调用；AI默认OFF，启用默认SHADOW |
| Lab target/client | 内部HTTP8080、DNS53、TLS8443 | 固定私网IP、无外部/用户选择目标；TLS自签名仅实验；无客户数据/真实主机网络采集 |

[实际服务检查](../artifacts/v1.0/security/service-inventory.json)保留host bind、image ID、UID配置、cap、挂载与网络。全部Reference主机published ports仅127.0.0.1。控制网络internal，ingress单独loopback入口，无泛用路由/Docker socket；禁止将0.0.0.0内部监听误写为主机公网开放。Sensor内网与模型内网隔离范围由固定Lab Compose/Adapter约束。

认证只保护本机工作台，非多用户IAM。产品登录密钥、DB密码、Lab/model key在工程外deployment.private.json/*-key.private，Windows仅当前用户与SYSTEM访问，POSIX0700；每个新部署重新生成，恢复仅恢复工作台/模型/Lab身份，保留新DB密码。发布包不包含真实密钥或.env。环境变量为可信操作员配置，浏览器不返回其值。CSRF/session/无权限读写/跨环境拒绝由最终后端及Browser验收复验。

依赖取自冻结hash锁；28runtime wheels固定URL、SHA256；npm ci使用冻结lock；Docker基础/第三方镜像固定digest；Suricata apt使用Debian登记HTTPS镜像、签名校验、固定运行镜像ID与实际包inventory。Model固定revision+weights SHA256，权重不进入发布包。构建/依赖网络和运行时控制网络分开。安装网络失败记录为失败，不关闭TLS/GPG校验。Prompt/策略/场景/报告模板hash见[RC_STATE](../artifacts/RC_STATE_v1.0.0.json)。

日志不记录原始pg_dump；仅大小/SHA256。命令结果继续用于真实备份，但诊断日志脱敏DB URL、DB/API/model/Lab key，timeout路径同样处理。私密操作日志不进入发布包。[日志检查](../artifacts/v1.0/security/operator-log-redaction.json)与最终包扫描均需通过。Backup含DB与认证材料，非加密格式；ACL保护且排除发布包，传输需负责人选择加密存储。压缩成员路径/CRC/逐文件SHA256/格式/迁移head检查后才恢复到owned新空DB，禁止恢复到原数据库。

不可信Sensor文本/日志/模型输出不能授权行动、改变Scope/身份、提供任意URL或shell。只接受受约束提案，未知Evidence/Capability、循环依赖、跨环境、越界/过期授权、摘要变化、高风险自动请求拒绝。动作成功不等于安全成功；独立Verification、三态结果、审计与Outbox保持。数据库/模型/Sensor故障不允许静默成功，缺观测=INCONCLUSIVE。AI主张Option B，闭环优越性NOT CLAIMED，G0 NOT INCLUDED。

实际OSV/npm锁扫描均0告警，但六镜像扫描共520个Critical/High package/target出现项，未被这两个结果覆盖。禁用特定解析器仅为缓解，不是包修复。运行库与内部Wazuh API存在剩余风险，逐条记录在CSV，未经验证的项明确保留。公开端口、任意流量、陌生Lab peer/规则/配置/日志、额外第三方工作流都要求重新评估和修补，不能沿用本版PASS。此为工程范围决定，没有声称负责人已批准生产风险。
