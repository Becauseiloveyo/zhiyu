# 智御 v0.9 Web Console 架构

状态：v0.9.0 PASS / CONTROLLED LAB。2026-10-04。见 [最终验收](VALIDATION_REPORT_v0.9.0.md)。

## 既有产品与事实来源

采用已定稿的 React + Vite Web Console，保留 Recharts、cmdk、Sonner、Lucide、自有路由和图谱组件。
用户提供的盾牌眼睛 Logo 保留原图，不进行重绘或全局换色。
原设计目录 `.ui-preview/workbench-20260929` 和前端第一版封存包是视觉历史，不作为 LIVE 业务数据来源。

唯一 canonical database 仍为 PostgreSQL。现有摄取、关联、AI、授权、执行、验证和重规划服务继续负责全部业务写入。
`product/` 的查询投影不写入核心业务事实；演示控制器只登记固定运行意图与步骤元数据，独立 Worker 经受控适配器调用既有核心链路。不改变 ai.5 Domain Contracts。
不引入图数据库、工作流引擎或新的事实状态机。

## 当前新增只读服务

`api/routes/product.py` 提供 `/v1/product` 命名空间，复用服务身份认证。
`product/access.py` 从服务器的 `ZHIYU_PRODUCT_GRANTS` 读取当前 Reader 授权：Principal → Environment → Scope IDs。
执行权限与读取权限分开；有 `incidents:read` 不自动拥有 `product:read`，只读 Viewer 不能调用摄取/智能处理/执行接口。

Scope 只缩小结果。受限 Viewer 只能看到资源绑定完整且全部落在允许资源集合的 Incident。
事件直接引用、IncidentEvent 关系、EventResource、Actor、Task 和 Verification target/scope 都参与可见性判断。
未登记、混合 Scope 或无法解释的绑定默认不可见；列表、数量、详情和已有快照使用相同规则。
整环境访问必须通过 `whole_environment=true` 显式授予。历史执行 Scope 到期不改变历史事实，但也不能据此授权新执行。

## 一致性、预算和快照

产品事实查询使用短时 `REPEATABLE READ READ ONLY` PostgreSQL 事务。演示启动、清理和重置使用独立的受权元数据事务，不适用只读事务描述。
单语句超时 2 秒，进程内每 Viewer 最多 2 个并发读、每 Environment 最多 8 个。容量不足返回 429/Retry-After。
这不是分布式全局限流，也不是已验证 SLA。多副本部署需要共享边缘限流；当前受控 Lab 验收使用单 API 进程。

列表声明 `LIVE_PAGE`，以 created_at + incident_id keyset 排序。跨页并发状态变化可能影响集合成员，不伪称严格冻结列表。
游标经 HMAC 签名，绑定当前授权指纹、过滤、排序、窗口，五分钟有效。

详情快照在同一个只读事务内裁剪固定字段与有限行数，形成不可变 DTO。
缓存只保存经过授权的 DTO 字节，最多 32 MiB、TTL 300 秒。它可以丢弃；数据库才是事实来源。
返回 snapshot_id、as_of、content_sha256、expires_at、预算、截断标记。
as_of 是投影采集时间，不是 PostgreSQL commit timestamp；不以客户端时间或 audit head 代替事务一致性。
缓存读取重新核对当前 Grant、Scope 绑定和 Incident 可见性，撤权后不得读取旧快照。
过期/进程重启返回 410，浏览器须明确刷新，不能悄悄替换报告依据。

初始预算：列表 default50/max200；事实最多2000条/每类200条/1 MiB；时间线最多2000条并分页；图谱最多200节点400边。
达限明确 TRUNCATED 或 413，不将缺失条目计为通过。所有历史投影标记 PARTIAL，当前状态表不伪装完整历史事件日志。

## 字段与安全

`product/registry.py` 定义 SQL 列白名单，查询时即排除原始 content、模型 input/output、parameters、locator、content_ref/raw_ref、配置与凭证。
文本长度、列表长度、嵌套 JSON 键受限，常见凭证形式脱敏。返回原始 integrity_hash 仅用于记录关联，不把哈希正确等同内容真实。
模型分析/提案与观察分开；模型置信度始终注明自报且未校准，语义正确性 NOT_VALIDATED。
浏览器渲染必须使用 React 文本节点，报告 HTML 必须转义；不得执行日志中的 HTML/Markdown/脚本。

## 投影语义

时间线只使用实际存在的时间字段，保留 source_timestamp/ingested_at/observed_at/created_at 等语义。
按时间瞬间、来源引用、时间字段稳定排序；同一时刻不表示因果，缺失阶段不补造。
图谱来自明确记录引用，所有边标注 source_ref/source_field。拒绝提案可独立悬空，不补假 Plan/Action。
`causal_attack_path=NOT_ESTABLISHED`；Event source/target 边需要实际 EventResource 行。
Verification 保留历史 PASS/FAIL/INCONCLUSIVE 与 freshness，执行成功不会升级为安全通过。

## 浏览器会话与固定演示（2026-10-03）

正式前端采用已定稿的 React/Vite 工作台、项目原 Logo 与同源 Product API。浏览器只保存显示偏好；HttpOnly 会话承载低权限 principal，写入要求 Origin、CSRF、demo:run 与当前 Scope。核心 API 不接受浏览器会话执行动作。

同一个 canonical PostgreSQL 中独立 `zhiyu_product` schema 只保存 DemoRun/Step 的 intent、租约、幂等与引用；原72张核心表及原迁移不变。它不替代 TaskScheduler、ActionGateway、Verification 或第二套安全事实。默认无执行 profile。

独立的固定 Lab Worker 持有 Docker 权限；API 和 runner 无 Docker socket。每轮服务端 ID 对应独立子 Environment 和独占 disposable Compose project。部署模板限定 Sensor、受控 HTTP 目标、固定流量和本地模型。模型提案保持 SHADOW；真正处置复用现有授权、风险、Gateway。B/D 的脚本模型明确标 SCRIPTED_NOT_AI。E 停止本轮模型容器触发真实 Gateway 失败和已有确定性降级。

父环境读取授权只在产品层推导到已登记运行的子范围，并与父 Scope 当前资源集合相交。取消、撤权、模板/配置变化和失效租约阻止后续调用；步骤意图先提交，在途未知不自动重发。

ARCHIVE 生成单一 Snapshot，固定文件名和 hash 由已完成步骤登记。Replay 严格重新校验当前授权、canonical Incident 可见性、文件/字段白名单/事实 hash，保留历史 as_of，不写 Event/Action/ModelRun/Verification/Audit。JSON/Markdown 报告由同一不可变 Snapshot 构成。

Cleanup 核对 project/run/owner/service 白名单，采集 Sensor 实际停止观测，删除本轮可销毁容器/卷/网络，再检查零残留。控制数据库和历史证据保留；reset 新建 run 和子环境，旧 UNKNOWN/FAIL 不被覆盖。

Gate A–E 已通过，当前状态见 `V0.9_STATUS.json`；生产/长期可用性仍未验证。历史阶段记录和失败证据保留，不替代最终报告。
