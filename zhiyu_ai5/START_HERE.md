# START HERE — 智御 ai.5 Engineering Freeze

这是“智御——网络安全自主决策与持续验证平台”的工程冻结上下文包。当前版本 **2026.09.12-ai.5**。

## 读取顺序

1. `PROJECT_STATE.yaml`：当前唯一状态与冻结规则。
2. `docs/01_项目定位与总体架构.md`：功能架构与部署平面。
3. `docs/10_ai5工程冻结与实现入口.md`：ai.5 新增的工程契约和开工顺序。
4. `contracts/models.py`：API/DB/Worker/AI 的权威数据契约。
5. `contracts/state_machines.json`：Incident / Task / Action 状态迁移。
6. `docs/06_V1场景与开发接口.md`：第一条确定性闭环与 API 草案。
7. `examples/`：全部是 `SYNTHETIC` 设计 fixtures，不是实测结果。

## 当前里程碑

`M0_engineering_freeze -> M1_infrastructure -> M2_deterministic_closed_loop -> M3_ai_planner -> M4_acceptance`

## 不可误读

- ai.5 通过资料包自检，不代表真实平台通过 A01–A15。
- 主动安全能力仅限自有/教学/隔离或明确授权环境。
- LLM 不直接执行高权限动作，也不持有真实 Credential。
- ai.5 后不因“新框架更酷”修改核心 Contract；必须由实现/测试/安全/实测约束驱动。
