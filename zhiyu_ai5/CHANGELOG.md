# 智御变更记录

## 2026-09-12｜ai.4：从概念补充转为可接续的工程设计基线

本轮是资料设计更新，没有实际平台代码或性能结果。

1. 重整入口、状态、主题文档、数据契约、状态机、示例与单文件阅读版；修复错误引用，消除旧摘要与新增设计不同步的问题。
2. 保留八层功能与五平面部署、Linux主控、跨平台感知/响应、隔离验证、私有化和完整版扩展。
3. 环境分类拆分部署阶段、资产领域、联网条件和运营模式；继续区分 AutonomyMode 与 LoadMode。
4. 动作按风险/影响/参数分级；R5 与高业务影响不能自动批准。人工审批绑定具体参数摘要及有效期，执行前重新评估。
5. 增加执行结果未知、状态核对、幂等、资源级冲突、租约代次、ownership 补偿、清理失败和持久任务要求。
6. 区分遏制、修复、恢复、检测和清理；验证同时检查安全效果、正常业务、观测有效性。PASS不直接关闭Incident。
7. 明确来源认证与内容真实的区别；增加证据血缘、时间有效性、冲突和未校准模型置信度语义。
8. 增加可信测试运行登记、自响应反馈控制、事件级预算/停止条件和恢复资源预留。
9. 补全有界队列/留存/丢失统计、数据全路径出域、工作流参数保护和站点离线处理。
10. 将第一条演示链收敛为 SCN-LAB-AUTH-01 合成认证异常→临时范围限制→独立安全/业务复测；SCN-LAB-AUTH-02为修复扩展设计。
11. 增加固定编排与AI的公平对照、A01–A15平台验收、M0–M5里程碑。Atomic/CALDERA改为第一条场景非必需的扩展能力，避免无必要地同时集成。
12. 形成可生成 JSON Schema 的 Pydantic 契约、合成样例、包自检与哈希清单；自检不代表平台验收。

## ai.3 保留的关键决策

五平面部署、Linux主控与跨OS数据面、独立Linux/Windows验证池、Durable Workflow、Policy-as-Code、Workload Identity、分层存储、HA/DR与图投影单事实源。ai.4将这些作为按规模选择的完整概念配置，V1仍保持模块化单体。

## ai.2 保留的关键决策

EnvironmentProfile、SensorHealth/Coverage、最小身份/审批、出域控制、版本溯源、独立验证、时间一致性、幂等、环境上线基线与冲突补偿。

## 长期保留与否决方向

保留：事件先压缩再模型、外置状态与三层记忆、证据约束、规则兜底、受控授权执行、持续验证。

后移/否决：通用安全知识库作为核心、Anthropic-Cybersecurity-Skills运行时依赖、默认多Agent、V1完整数字孪生/图数据库、模型直持高权限凭据、精确预测攻击者下一步、未授权公网自主攻击。

## 2026-09-12 — ai.5 Engineering Freeze

- 将 `TargetRef` 替换为跨平台 `ResourceRef`，Scope 从 IP/Port 专用结构提升为资源级授权 + 可选网络约束。
- `NormalizedEvent` 增加 CloudEvents-like envelope 与安全活动语义（activity/outcome/actor/source/target/observable），保留 OCSF mapping 路径而不强依赖完整 OCSF。
- `EventGroup` 与 `CorrelationDecision` 成为一等契约，事件压缩必须可解释、可版本化。
- Incident / Task / ActionAttempt 增加可测生命周期时间与租约/worker 字段；新增 `WorkerLease`。
- `ValidationScenario` 不再保存自然语言验证规则；新增可执行 `VerificationSpec` / `VerificationCheckSpec` / `AssertionSpec`。
- 新增 `AuthorizationContext`，AuthorizationDecision 必须可追溯当时的环境、Scope、风险、业务影响和传感器状态输入。
- 新增 `ModelRun`，模型/provider/prompt/context/token/latency/schema-validity 进入正式审计与评测对象。
- Capability 静态定义与动态 `CapabilityHealth` 分离，并补充权限、Secret 引用、并发、锁、取消/dry-run/验证与补偿信息。
- 新增最小 `AuditEntry` 与 `OutboxMessage` 合约，为 M1/M2 的 durable intent、审计和事务 outbox 提供基线。
- ai.5 状态定义为 `FROZEN_FOR_IMPLEMENTATION`；之后核心契约变更必须由实现、测试、安全或实测瓶颈驱动。
