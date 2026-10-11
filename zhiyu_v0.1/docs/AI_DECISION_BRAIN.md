# AI Decision Brain — v0.5

AI 默认关闭；启用后的默认影响模式为 SHADOW。模型只接收持久化、脱敏、受预算约束的 Context，输出结构化分析或提案。执行始终由现有 Response Worker、Authorization、Risk Gate 和 Action Gateway 完成。模型没有工具调用权限。

## 运行与配置

基础服务仍使用 README 中的启动步骤，不需要模型容器。操作者通过服务端 `ZHIYU_AI_POLICIES`（按 environment_id）和 `ZHIYU_AI_PROVIDERS`（按 provider_id）配置路由。API 请求不能修改 provider、endpoint、mode、budget 或凭据。

```json
{
  "lab-zhiyu-01": {
    "enabled": true,
    "mode": "SHADOW",
    "provider_id": "local",
    "budget": {"max_calls": 6, "max_tokens": 96000, "max_ai_replans": 1, "max_wall_seconds": 900}
  }
}
```

```json
{
  "local": {
    "provider": "local",
    "location": "LOCAL",
    "endpoint": "http://local-model:8080/v1",
    "model": "zhiyu-qwen2.5-1.5b",
    "revision": "91cad51170dc346986eccefdc2dd33a9da36ead9",
    "api_key_env": "ZHIYU_LOCAL_MODEL_KEY",
    "timeout_seconds": 110,
    "max_output_tokens": 1200,
    "structured_format": "JSON_OBJECT_SCHEMA"
  }
}
```

示例仅描述路由，不能为资源或动作授予权限。ASSISTED 仅允许 Lab；其他环境默认最高 R1，Lab 也需要现有策略明确允许才可到 R2；R3/R4、状态变更和未知执行器均不进入自动执行。

SHADOW 的 AIPlanner 只保存提案，不创建 Task。显式调用 DecisionBrain 的 SHADOW 决策时，仍由既有确定性 Planner 产生正式计划；不会自动触发 Worker。ASSISTED 下合格提案转成冻结 AIPlan/TaskGraph。不可用模型走确定性回退；非法或幻觉提案保留拒绝结果。

## 权限和 API

服务令牌的环境范围与旧 API 一致，查询没有权限的对象返回 404。除下表权限外，正式计划与周期操作仍要求既有 `response:plan`、`incidents:write`、`verification:write` 或 `verification:replan` 权限。Worker 权限独立。

| 方法 / 路径（前缀 `/v1`） | 请求主体 | AI 权限 / 用途 |
|---|---|---|
| POST `/incidents/{id}/contexts` | environment_id, scope_id | ai:context；生成有界快照 |
| POST `/incidents/{id}/ai-analysis` | environment_id, scope_id | ai:context + ai:analyze |
| POST `/contexts/{id}/ai-analysis` | environment_id | ai:analyze；只读该 Context |
| POST `/analyses/{id}/plan-proposals` | environment_id | ai:plan；只用已落库分析 |
| POST `/contexts/{id}/ai-decision` | environment_id | ai:analyze + ai:plan；协调分析、提案、旧周期激活 |
| POST `/contexts/{id}/ai-replan` | environment_id, verification_id | ai:analyze + ai:plan；复用原 Re-plan 预算 |
| GET `/contexts/{id}`, `/analyses/{id}`, `/plan-proposals/{id}`, `/model-runs/{id}` | 无 | ai:read；审计查询 |
| GET `/ai-contexts`, `/ai-analyses`, `/ai-proposals`, `/model-runs` | 查询 environment_id, limit, cursor | ai:read；keyset 分页，limit ≤ 100 |
| GET `/ai-metrics` | 查询 environment_id | ai:read；分阶段计时、用量和回退 |

Context 默认最多 12 个事件、12 个 Evidence、8 个时间线条目、3 个历史计划、4 个 Verification、16 个 State，24,000 字符及 16,000 保守 token 上界，有效期最多 120 秒并受 Evidence/Scope 截止时间进一步收紧。压缩规则确定性，不使用模型改写来源事实。实际选取和排除原因随 Context/manifest 持久化。

`REFERENCE_GROUNDED` 表示引用存在、属于当前环境/Incident/Context、未过期且内容摘要仍匹配；**不表示自然语言结论已经被证明**。来源和内容仍可能存在语义歧义。所有模型 State 都是带 `MODEL_INFERENCE` 来源的 INFERENCE；模型 confidence 为未校准自报值。配置记录没有被当作实时探测 FACT。

ModelRun 的 `safety_status=PASS` 仅表示传输、格式与 Schema 检查通过。Proposal 必须继续经过当前 Evidence、Scope、Capability Registry、健康、DAG、参数和组合风险检查；随后每个动作再次经过现有授权。

## 本地模型复现

模型来源、固定 revision、GGUF SHA256 和镜像 digest 见 [Model Runtime](M5_MODEL_RUNTIME.md)。下载对应权重到工程外的私有运行目录，验证 SHA256；生成随机 API key 并以 UTF-8/LF 写入另一个私有文件。权重、凭据和 `.env` 不包含在工程包中。

设置 `ZHIYU_MODEL_PATH` 为 GGUF 绝对路径，`ZHIYU_MODEL_KEY_FILE` 为私有 key 文件绝对路径；使用 Python 3.12、Docker Linux Engine 和已安装的锁定依赖：

```bash
uv run --locked python tools/compose_smoke.py --benchmark
```

脚本组合基础 Compose 与 `docker-compose.ai.yml`，生成隔离项目和临时服务身份，完成旧闭环、真实模型链、故障注入、重启、完整 Linux 测试及 24 个受控 Context 案例；结果保存在 `docs/m5-runtime/`。结束时删除本次容器和网络，保留命名卷。不会部署到生产。

模型容器没有宿主端口，以 uid 10001、只读文件系统、无 capabilities、`no-new-privileges` 运行。权重和 key 只读挂载；API 入口 `tools/ai_api.py` 在进程内读取私有 key。`model-fault-fixture` 是明确标注的脚本故障夹具，不能用于证明真实模型质量。

更换兼容模型只需 provider 配置；仍需重新验收其 Schema 协议、token 预算和输出质量。Cloud 分支要求显式授权、允许的数据分级、egress 与公网 HTTPS；offline/air-gap 禁止 Cloud。本轮实际模型调用均为 LOCAL，未验收任何真实 Cloud 服务。

## 恢复与限制

调用前独立事务预留 incident 预算和请求身份，完成后原子持久化 ModelRun、receipt 与审计。运行中同身份返回 IN_PROGRESS；终态重放不重新采样。租期结束仍无回执则记 INTERRUPTED_CALL 并回退。模型可能已经在远端消费 token，但失去回执时真实用量未知，预算保守占用，费用保持 null，不能解释为免费。

AI 重规划与原 ResponseCycle 共用次数、总动作、时间、风险 ceiling、新证据和重复计划限制。模型不可用不增加原执行权限。不同 Scope/配置不能复用同一确定性回退计划。

真实 Sensor、A01–A15、生产 SLA、广泛对抗评估、Dashboard/比赛 UI 另行验收。受控 Lab 中只读任务及安全边界通过，不等价于真实攻击检测准确率或自动修复能力。
