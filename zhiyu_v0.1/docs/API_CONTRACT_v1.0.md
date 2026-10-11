# Product API v1.0.0

状态：Gate A 实现中。以应用 OpenAPI 和 `product/contracts.py` / `product/registry.py` 为字段来源。
本文件不修改 `/v1/events`、`/v1/incidents`、`/v1/response` 等原有核心 API。

## 身份与读取权限

当前只读 API 复用 HTTP Bearer 认证。凭证只配置在可信服务端，构建产物和日志不包含真实凭证。
必须具有 `product:read`、允许的 environment_ids 以及独立 Product ReadGrant。
`ZHIYU_PRODUCT_GRANTS` 形状：`{"principal-id":{"environment-id":{"version":"reader-policy-1","scope_ids":["scope-id"],"whole_environment":false}}}`。
未配置 Reader Grant 即拒绝；客户端 scope_id 仅能收窄授权。

## 通用查询

environment_id：必填，1–160字符。scope_id：可选，1–160字符。
hours：1–168，默认24；priority：P0–P4；status：原始 SecurityIncident 状态枚举；search：最多120字符，按字面子串匹配 ID/title。
sort：created_desc（默认）/created_asc。相同创建时间再按 incident_id 排序。
列表过滤使用 created_at，详情根可为历史事件；详情关联 Event 使用所选摄取窗口，并显式标记历史不完整。

## 端点

| 方法 | 路径 | 返回/行为 |
|---|---|---|
| GET | /v1/product/access | 当前 Principal 与获准环境、Scope、Grant version |
| GET | /v1/product/overview | 受权事件计数、环比、待处理数量、关联事件数、7日UTC日桶与公式；无防护分数 |
| GET | /v1/product/incidents | items、next_cursor；limit默认50/max200，LIVE_PAGE |
| GET | /v1/product/runtime-health | 实际 Sensor/CapabilityHealth、策略 AI mode；心跳过期标UNKNOWN |
| GET | /v1/product/incidents/{id}/snapshot | 受权、有界、不可变 DTO；不产生业务写入 |
| GET | /v1/product/snapshots/{id} | 同一 DTO；重新核验权限；过期410 |
| GET | /v1/product/snapshots/{id}/timeline | 真实时间字段投影，items与next_cursor；limit50/max200 |
| GET | /v1/product/snapshots/{id}/graph | nodes/edges、来源字段、截断和未解析数量；无攻击因果声明 |
| GET | /v1/product/snapshots/{id}/ai | Context/Request/Receipt/Run/Analysis/Proposal/Decision 白名单事实 |
| GET | /v1/product/snapshots/{id}/verification | Spec/Check/Observation/Result/Evidence/State/Replan 白名单事实 |
| GET | /v1/product/snapshots/{id}/report | 固定快照的正式报告 DTO，UNREVIEWED_DRAFT |

所有读取必须携带创建时相同的环境、Scope、窗口和过滤参数。更改查询需显式创建新快照。
快照 hash 为 facts 的 UTF-8 canonical JSON（key排序、紧凑分隔符、非ASCII原文）的 SHA-256。
浏览器不得将快照 ID 当作访问凭证；它始终受当前身份和授权限制。

## 响应公共字段

projection_version、environment_id、scope_id、access_policy_version、as_of、consistency、run_mode。
当前实时接口 run_mode=LIVE 表示从当前数据库读取，不表示 data_origin 一定为 OBSERVED。
data_origin=SYNTHETIC 的历史测试记录必须仍标合成来源。
快照附带 snapshot_id、expires_at、content_sha256、incident_id、facts、truncated、omitted_count、history_completeness、limits。

Fact：ref（kind:environment:id）、kind、id、fields（固定SQL列白名单）、basis、freshness。
basis 为 OBSERVED/DERIVED/MODEL_INFERENCE/UNKNOWN；SOURCE_ASSERTION 不升级为观察。
freshness 为 CURRENT/EXPIRED/UNKNOWN；无有效期不臆造时效。
所有动态文本视作不可信数据，客户端不得作为 HTML、可执行 Markdown 或外链自动运行。

## 错误与限制

401未认证；403环境/Scope/读取权限不足；404对象不可见或不存在；410快照过期/缓存丢失；413响应预算超限；422输入/游标无效；429读取并发超限；503数据库不可用/查询超时。
错误不得附加SQL、数据库URL、原始输入或凭证。
GET 不调用 AI、ActionExecutor 或 VerificationWorker。快照材料化只写可丢弃内存缓存，不写业务表。
LIVE_PAGE 不保证并发修改下跨页集合不变；同一 Snapshot 的各个投影共享不可变材料。

## 浏览器会话与演示接口（2026-10-03）

POST/GET/DELETE `/v1/product/session` 创建/检查/注销低权限浏览器会话。HttpOnly、SameSite=Strict；所有浏览器写入额外要求允许 Origin 和 X-Zhiyu-CSRF。浏览器身份只含 product:read/demo:run，不作为核心执行身份。Cookie 不能调用核心 Action API。

| 方法 | 路径（统一 /v1/product 前缀） | 语义 |
|---|---|---|
| GET | /access | 当前直接读取范围，以及最多50个有授权且已准备的演示子环境 |
| GET | /snapshots/{id}/report-json | 服务器精确 JSON 字节及 export_sha256 |
| GET | /snapshots/{id}/report-markdown | 转义 Markdown 及 export_sha256 |
| GET | /recordings | 当前范围登记的只读档案；固定配置或已完成 ARCHIVE step 的 SHA-256 |
| GET | /recordings/{id}/snapshot | 严格文件/内容/授权校验；RECORDED_REPLAY；保留原始 as_of/facts |
| GET | /demos/catalog | 固定 A–E、已登记 profile、can_run、如实 UNKNOWN 的 Worker 健康 |
| GET | /demos/runs | 有界运行记录（默认20，最多50），truncated |
| GET | /demos/runs/{id} | 运行和最多5个持久步骤 |
| POST | /demos/runs | 仅 scenario_id、profile_id、idempotency_key；202 表示 intent 已记录 |
| POST | /demos/runs/{id}/cancel | expected_version；阻止后续步骤，保留已产生事实 |
| POST | /demos/runs/{id}/cleanup | expected_version；终态才能申请，独立 Worker 校验资源归属与残留 |
| POST | /demos/runs/{id}/reset | CLEAN、expected_version、idempotency_key；新 run_id，保留 predecessor |

运行 DTO 由 `product/demo_contracts.py` 声明：原环境/源数据子环境、Scope、场景与 template hash、actor/predecessor、LIVE、实际/计划模型来源、status、cleanup_status、version、deadline、实际/预期结果与 StepOutput。StepOutput 只含对象引用、artifact hash、结果和清理核验，不返回 subprocess 输出或部署配置。模型来源在执行后更新，不能把计划来源当成已执行模型。

每轮 source_environment_id 固定为 `m6-real-<服务端 run_id>`。授权从注册的 parent/profile/Scope 和当前资源上限推导，仅扩展 Product read，不改变核心 ServicePrincipal 的执行权限。子环境并发查询共享8个槽，不能用伪造 ID 扩大资源预算。

409 表示版本冲突、幂等内容冲突、未清理或需要人工核对。崩溃/租约丢失进入 UNKNOWN/NEEDS_RECONCILIATION，不重派同一个不确定步骤。每步骤最大600秒，整个运行30分钟；cleanup 有独立有限租约。

Report 的事实 hash、整体 report hash 与精确下载字节 hash 分开校验。Replay 增加 recording_id、recording_sha256、source_snapshot_id、source_run_id、model_source。未登记/撤权404、文件篡改或无效422；没有上传或用户可选路径接口。

## 版本与验收状态

应用与health版本1.0.0，冻结Product DTO `projection_version=0.9.0`、报告template版本与登记场景版本保持原协议身份，不批量改写历史对象版本。迁移head0016，全部身份见 [RC_STATE](../artifacts/RC_STATE_v1.0.0.json)。

本版本未新增业务API；操作员安装/备份/恢复/协调/日志脱敏不通过浏览器暴露。当前A/B/C证据已建立，D/E最终签署见 [V1.0_STATUS](../V1.0_STATUS.json)。接口说明和历史测试不能单独代表整体v1.0 PASS。
