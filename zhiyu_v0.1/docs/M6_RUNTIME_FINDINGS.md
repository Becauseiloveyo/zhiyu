# RC7 Remediation Final Update

当前 v0.6.0 PASS / CONTROLLED LAB。RC5 构建 PyPI 超时与一次被取代的构建保留；RC6 构建成功但旧模块数断言失败；RC7 将硬编码 103 改为成功导入列表与冻结源码逐项比较（109），产品源码不变，完整 Gate E 重跑。

---

以下是 RC3 及更早的历史报告，原封存内容保留，当前结论以上方及最终报告为准。

# M6 runtime findings

所有失败目录保留；Gate 结论以验收 JSON 与对应报告为准。

## A-001 — Debian HTTP 包索引中断

`sensor-preflight/lab-build.log`：官方源 HTTP 500 / unexpected EOF，apt 保持签名校验并失败。改用同一源 HTTPS 与有限重试；`lab-build-attempt-2.log` 构建成功，实际 Suricata 7.0.10。未关闭 TLS/包签名校验。

## A-002 — Wazuh Lab 规则编号冲突

`sensor-001/wazuh-before-rule-fix.log`：镜像自带 `local_rules.xml` 已使用 100001，analysisd 明确警告 duplicate，忽略本次失败认证规则；成功规则仍产生真实告警。Lab 规则改用 110001/110002；未降低触发断言，需重新产生真实请求验收。

## A-003 — Wazuh Manager 重启初始化提前退出

真实 `docker compose restart wazuh-manager` 后，镜像初始化因 `/var/ossec/var/multigroups` 为空而尝试从已被首次启动删除的 `/var/ossec/data_tmp` 复制，失败退出。s6 仍启动 analysisd，因此单一进程健康检查不足以证明新配置已应用。导致 A-002 修改未装载，`sensor-002/alerts-timeout.raw` 保留失败输出。

最小 Lab 镜像修复：从固定官方 4.14.7 digest 派生，保留镜像原始 seed 目录，以便重复初始化。Indexer 不在本轮感知链范围内，禁止启动无用途的 Filebeat 导出服务。真实配置内容、规则加载、进程状态与新告警必须共同验收；后续重复 stop/start 验证恢复。此修改仅作用于测试基础设施，未改智御核心源码或 ai.5。

## A-004 — 活跃 JSONL 文件尾部尚未写完

`sensor-003` 读取时出现 unterminated string；该次错误发生时尚未保存触发异常的完整原始文件，不能声称拥有该尾部的逐字节复现证据。随后采集器先保存原始快照，解析器只消费换行终止的记录，并记录未完成尾部字节数与哈希。已终止但损坏的记录仍报错。新增测试覆盖 UTF-8 多字节字符的每一个截断位置，完整记录重放保持字节一致。

## A-005 — 真实 HTTP 身份字段缺失导致双来源无法关联

`sensor-004/005/006` 保留了未满足 cross-source 验收的实际输入与数据库快照。现有精确关联键需要同一观测用户名；HTTP 401 本身不提供用户名，未放宽关联键。仅在这个公开、一次性 Lab 测试账户场景显式开启 EVE Authorization 请求头采集。Suricata 7 的真实结构为 `http.request_headers` 数组，原先只处理单字段的接线不能取得身份；`sensor-006` 证明该差异。

修复仅在 Adapter：严格解析 Basic 观测用户名；标注 OBSERVED_CLAIM_NOT_AUTHORIZATION；密码与完整 Authorization 不进入 NormalizedEvent。分支 mapping version 为 `sensor-map/suricata-http-basic/1.0.0`；未出现该头的旧映射保持不变。重复 Authorization、非法编码/字符/长度均拒绝，不通过错误消息回显内容。测试覆盖真实数组格式、同用户关联、不同用户隔离与凭证不进入归一化事件。原始 EVE 保留公开 Lab 凭证用于字节血缘核验；这个日志配置不能直接用于客户真实凭证采集。

## A-006 — 容器大包截断导致缺少 TLS

早期 EVE 中真实 decoder 截断计数为 4，未产生所需 TLS 记录。Lab 捕获缓冲调整为 65535，保留实际统计与完整原始输出；`sensor-006/007/008` 已出现 TLS 1.3，后续健康验收同时检查 decoder invalid/kernel drops。不能单凭容器 Running 声称采集健康。

## A-007 — 测试顺序与记录实例

`sensor-005` 曾在依赖镜像构建完成前运行采集，配置仍为旧版；保留失败，不计为修复后验证。后续构建、启动、采集串行执行。EVE 目录采用目标网络命名空间 hostname 分隔；该 hostname 与 Suricata 容器 ID 不相同。当前成功实验同时重建 target/Suricata，manifest 记录实际两者身份；不能仅用目录名推断 sensor ID。未来只重建 Suricata 而复用同名旧目录必须拒绝旧时间段，不能把旧输出归给新容器。

## A-008 — Agent 启动不等于日志采集就绪

`gate-a-001/agent-startup-diagnosis.log` 显示 13:13:27 Agent 已连接，13:13:29 logcollector 才启动；该轮请求在 13:13:27–28 已完成。原始请求与轮询告警保留，75 秒未收齐后整轮 FAIL。修复实验启动顺序：按本次容器 StartedAt 等待实际 logcollector 启动日志，再发送有限流量，仍要求全部 request_id 的实际告警到达。`gate-a-002` 完整重跑通过。

每次物理实验使用独立 scenario version（包含本轮目录名），避免同一环境中重试测试误读上一轮不可变 VerificationResult。此处修复测试身份，无核心幂等行为修改。

## Gate A 当前边界

成功证据为 `sensor-007`（包含全部五种 Suricata 事件）、`sensor-008`（本轮完整请求 ID 对照）及 `gate-a-002`。停机/暂停/过期返回 INCONCLUSIVE；恢复后真实新流量覆盖通过才 PASS。只读 DETECTION 验证不能证明隔离、修复、攻击阻断或持续恢复。Windows Agent 与 Production 均 NOT_RUN。

## B-001 — 内部网络不提供本机发布端口

故障栈首次启动后 API 在容器内健康，但 `compose port` 返回 `invalid IP:0`。原检查 FAIL 保存在 `zhiyu-smoke-3aff09145006/attempt-001-internal-network-port-failure.json`。数据面 control 保持 internal；仅 API 加入 ingress 网络，仍只发布到宿主 127.0.0.1 随机端口。数据库、模型与测试目标无公开端口。没有修改宿主网络配置。

## B-002 — 将投递收据误判为重复逻辑对象

首轮事件重放后原始记录、NormalizedEvent、Outbox 均不变，EventReceipt/RawDelivery 与审计按实际新投递增加。最初实验断言要求收据不增加，与既有 `EventIngestService` 契约不符。原失败及前后快照保留，修正只针对验收断言：逻辑事件不重复，每次投递仍有可审计收据。没有修改核心幂等代码。

## Gate B 结论与限制

`zhiyu-smoke-3aff09145006/result.json` 为 PASS。实际执行数据库 stop/SIGKILL、四种事务/模型阶段 API SIGKILL、Worker 进程退出与真实租约等待、模型/网络/存储故障、Outbox 丢 ACK 恢复。最终全环境 Audit 有效，高风险自动执行为 0。

Worker 的 25 个场景按任务要求分为五类；Task/Action 属于既有 ResponseWorker 调用链，AI 的租约与调用前共用同一持久化预留边界，不宣称 25 个独立机制。Event Intelligence 没有 WorkerLease，使用实际事务行锁/并发去重证据。过期提交均没有写入新有效结果。

慢启动可用性用实际暂停模型进程表示，另执行真实 stop/start/restart 与 readiness；真实重启后模型实际消耗 4057 input / 735 output tokens，46.765 秒，结构合法，分析仅 REFERENCE_GROUNDED。该结论不等于语义正确。

证据存储测试在专用 PostgreSQL 实验库为指定环境安装临时触发器抛 SQLSTATE 53100，检验完整回滚并移除触发器恢复。文件/日志失败使用只读容器与 8 KiB tmpfs，不填充宿主磁盘；这是文件系统 harness 的边界测试，产品 Evidence 仍存 PostgreSQL。时钟偏移/乱序测试使用明确标记 SYNTHETIC 的真实格式副本，原始 OBSERVED 文件哈希保持不变。

## C-001 — 模型输出拦截状态的验收断言错误

`gate-c-001/boundaries-20260918T002356/canary-0.json` 中 canary 输出已被拦截：持久化收据为 `FALLBACK / UNSAFE_MODEL_OUTPUT`，analysis.output 和 state_entity_id 均为空，Context、请求、ModelRun、Audit、Outbox 均无泄露。初版 harness 错将此场景的 analysis.status 断言为 REJECTED。既有契约在 Gateway 阶段失败返回 FALLBACK；结构通过但引用不合法才进入分析层 REJECTED。

修正验收断言后，六个实际 HTTP canary 响应在 `boundaries-20260918T002512` 全部通过。原失败文件和日志保留；没有修改产品代码，没有放宽凭证检查。前五种为公开测试 canary 的受支持表示，第六种为配置的精确 provider key canary；不能外推为识别任意未配置秘密。

## C-002 — 合法引用仍可伴随不可靠的自然语言结论

真实 Qwen 初期输出中，E02/E03/E04/E05 的假设把已明示的 SYNTHETIC fixture 当成真实 sensor finding；E10 从 HTTP 500 推出 security issue；E12 从漏掉一次健康检查推出服务不可达。E10/E12 的引用校验通过，不能因此把自然语言结论称为正确。

这些原始输出完整保留；状态实体仍为 INFERENCE / MODEL_INFERENCE，未变成观察事实。单独的真实 HTTP 脚本用合法 Evidence ID 返回假因果/修复结论，同样证明 Grounding 的边界仅为引用完整性；独立 Verification 的 FAIL 与重规划预算仍然优先。语义评估必须继续标注 `SEMANTIC REVIEW REQUIRED`，不计算没有标注依据的“AI 准确率”。

## C-003 — 连续推理暴露模型容器 OOM 与缓存配置不匹配

首批 `gate-c-001/evaluation.json` 遍历 80 例，但只有 38 例取得可计量响应。E38 的分析正常返回，建议请求随后超过 Context TTL；E39–E42 为 TIMEOUT；E43–E80 为 CONNECTION_FAILURE。整个批次不能计为 80 个有效真实模型评估，也不能据此判 Gate C PASS。

`model-exit-state.json` 记录模型于 2026-09-18T01:04:18Z 退出，`OOMKilled=true`、`ExitCode=137`。完整原日志 `model-runtime-full.log` 显示生成速度从约 30 tokens/s 降至约 1.3 tokens/s，HTTP /health 在退出前仍能返回 200。没有当时逐点 memory/swap 样本，不将低速本身当作已直接测量到 swap 的证明。

固定镜像的 `llama-server-help.txt` 显示默认 `--cache-ram 8192` MiB；实际容器 RAM=4 GiB、MemorySwap=8 GiB，存在明确预算不匹配。为这个真实 OOM 问题，在 `docker-compose.ai.yml` 显式加入 `--cache-ram 256`，其他权重、镜像、上下文、并发、输出预算、超时保持不变。没有提高宿主资源限额或修改业务核心逻辑。缓存增长是合理解释；缺少原 OOM 时分配器诊断，不能声称排除了所有其他内存原因。

`gate-c-002` 使用新实验身份补跑 E38–E80，保留首批全部拒绝、低质量输出和 42 个 fallback。配对汇总保持 E01–E37 首次结果，E38–E80 明确链接恢复批次，最终最多 123 次尝试/80 个唯一输入；不把恢复重跑当成新的独立样本。恢复期间记录 Docker stats、cgroup current/peak/swap/OOM 计数及模型 RSS；这些为故障恢复观测，不替代 Gate D 的正式 soak。

## D-001 — Soak 预检子进程未加载模型凭证

`gate-d-001/pilot.json` 完成 10 秒预检、4 条新事件/4 次重复投递、3 个只读任务与 3 个独立检查，但模型返回 CREDENTIAL_UNAVAILABLE；该预检不能证明模型持续负载。`docker exec` 启动的 Python 不继承 API 进程运行时装载的环境变量。修正测试入口，沿用现有 AI 验收从容器内 secret 文件读取方式，并要求每个计划中的模型调用有实际 token 计量。原预检完整保留；正式 1800 秒 soak 使用新环境身份。无核心代码改动。

## D-002 — 固定事件时间在暂停后改变了负载性质

最初 100k 档在 1200 秒预算内完成 66,000 条，660 个分组、每组 100 条、两个独立来源，pending/error/duplicate 均为 0。原始事件时间为 2026-09-23T13:38:55Z，固定一小时窗口于 14:00 结束，加允许迟到 120 秒。14:20 的续跑保留原事件时间，因此新到达数据正确进入 LATE 单事件隔离，不能再和正常分组吞吐直接比较。

`events-finish.progress.json` 的 71k 批次记录 ingest 10.341 秒、group/correlate 75.146 秒、promotion 38.795 秒。现场数据库显示 TIMELY/CLOSED 660 组、LATE/CLOSED 6000 组；normalized clock_status 仍为 TRUSTED，时间可信与关联及时性不是同一个判断。观察到的增长主要伴随分组数量变化，不能仅凭耗时归咎于 PostgreSQL 查询退化。

仅对已核对 argv 的 `python tools/m6_finish_events.py` 子进程发送 SIGINT，退出 130 的 012.log 保留。当前事务正常回滚，已经提交的原始/归一化事件保留；`late-continuation-review.json` 记录中止前后和已提交 pending 输入的受控处理，不追加新事件。这个实验只支持迟到路径、持久性与成本观察，不算完整 100k 正常负载。

新 `events-streaming.json` 在独立环境重新生成 100k；每批使用实际生成时间，仍使用相同的 1 小时关联窗口和 120 秒允许迟到，不放宽产品规则，不回写原数据时间。原始首段、慢续跑、失败日志均保留。

## D-003 — 宿主协调进程结束后，容器任务完成但资源采样存在缺口

9 月 24 日恢复工作时，原宿主 session 已不存在；容器内也没有遗留 benchmark 进程。`response.json` 实际于 9 月 23 日 15:35:36Z 完成：100 / 1,000 / 10,000 个只读任务全部完成，逐批数据库状态、无重复 Action、NONE side effect 和审计校验保留。协调器未记录该命令的最终退出日志，也没有启动下一阶段；仅凭现有证据不能确定宿主进程退出的原因。

`response-resources.jsonl` 保留 94 个真实样本，但最后样本到负载完成相差 153.813523 秒。这一段标为未观测，不补造资源数据，不由之前零 OOM 推出这段没有异常。恢复入口检查实际完成 JSON 后登记结果，再开始此前未运行的 verification / AI 阶段；未重跑或覆盖已完成的任务负载。报告生成器现在对每个阶段明确记录采样与负载的首尾覆盖缺口。

## D-004 — 大数据集最终校验排序触发 statement timeout

全部负载完成后，只读全表校验在 `audit_entries` 的 `ORDER BY row_to_json(r)::text` 阶段发生真实 PostgreSQL `QueryCanceled: canceling statement due to statement timeout`；原始失败见 `gate-d-001/019.log`。这不是负载任务失败或数据损坏的证明，而是最终哈希校验尚未完成。

快照工具增加可选 `--statement-timeout-ms`，本次使用 180000 ms，通过事务本地 `set_config(..., true)` 仅延长校验连接的查询预算；未修改数据库全局配置、应用默认超时或产品逻辑。逐表排序规则和 SHA256 语义保持不变，行数据按服务端游标流式读入，避免在 Python 中一次性拼接大表。原失败记录保留，后续验收只接受实际完成的 72 表快照与所有环境审计校验。

## Gate E — RC 冻结与运行发现

E001：首轮宿主协调器消失，保留原证据并标 INTERRUPTED_NOT_AUTHORITATIVE；隔夜 idle 不计为 soak。E002：A12 夹具首次写入缺少依赖 flush，FK 失败，修正夹具顺序后隔离重跑通过；未修改产品。E003：RC2 真实两阶段推理超过 Context TTL，产品 STALE_CONTEXT 安全回退；旧 harness 对 AI_ASSISTED 的假设失败。RC3 仅接受已验证真实计量与安全不变量的精确过期回退，完整 fresh runtime 与最终回归重跑，原失败保存。E004：A05/A06/A07/A09/A11 缺少完整软件/实验 prerequisite，发布阻断；本轮不新增功能。完整入口见 [Final Evidence Index](FINAL_EVIDENCE_INDEX_v0.6.0.md)。
