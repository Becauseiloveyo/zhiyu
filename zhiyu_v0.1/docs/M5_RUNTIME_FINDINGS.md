# v0.5 runtime / review findings

这是开发过程中发现的问题与修正记录；失败运行保留，不作为最终通过结果。

| 发现 | 影响 | 修正与证据 |
|---|---|---|
| 私有模型 key 文件使用 Windows CRLF | llama.cpp 认证失败 | 改为 LF 文件，真实重试通过；`m5-real-gateway-preflight-auth-failure.json` 保留 |
| 小模型叙述过长，触及 1,200 输出 token 上限 | finish_reason=length，响应不能进入分析/计划 | 维持拒绝截断 JSON；固定服务端模板要求简短叙述与一个 finding/hypothesis/task，未放松 Schema；`m5-real-gateway-preflight-truncated.json` 保留 |
| 失败生成已有 usage，但原错误分支丢弃了 token/耗时 | 成本/预算观测不准确 | 错误带回已知 usage/latency；未知部分继续保守预留，cost=null；Gateway 回归覆盖 |
| 通用 redactor 键规则将 allowlist 中的授权布尔标志误认成凭据 | 合法 Context 可能被不必要拒绝 | 已投影数据检查标量；原始来源仍按键和值脱敏；canary 测试确认原取证数据不变 |
| JSON 时间 `Z` / `+00:00` 表达差异 | 相同持久化输出可能被误判为更改 | 比较规范化 receipt，不信任调用者重传的生成结果 |
| Context 引用有来源 ID，但缺少支持内容摘要绑定 | Evidence 同 ID 内容更改不能及时发现 | Context 增加 source_hash；分析/提案复核当前内容哈希 |
| AI re-plan 次数预算需要在模型调用前预留 | 并发或失败调用可能漏计 AI 重试 | 持久化 incident budget 内原子计数；原 ResponseCycle 预算仍独立生效 |
| 相同 fallback plan identity 未比较 Scope / 配置 | 决策可能复用另一组规划输入 | 按 environment / incident / version / scope / configuration 全部核对，冲突拒绝；`m5-api-brain-final-tests.xml` 7 passed（含两条新负例） |
| Docker 环境检查硬编码旧模块数 85 | 新版 103 个模块全部导入仍报失败 | 验收断言更新到当前库存；首轮 [失败报告](m5-runtime/zhiyu-smoke-7f160ba457b4/result.json) 留存，重跑 Linux 检查已通过 |
| 旧 live API 测试使用当前时间减 115 秒，三条事件可能跨五分钟窗口 | 偶发生成两个不足阈值的组，测试夹具没有预期 Incident | 基准时间对齐到分钟；产品固定窗口规则与 API 实时时钟不变。失败时为 337 passed / 1 setup error；[失败日志](m5-runtime/zhiyu-smoke-370eed1d5c4f/096.log) 保留。三个边界用例与原 API/周期重放共 [6 passed](m5-api-clock-regression.xml) |
| HTTP/1.0 + Content-Length 在读完后自动关闭 socket，读取循环再次 settimeout | 完整合法响应在 Linux 上误记 CONNECTION_FAILURE，导致恶意输出夹具提前进入回退，未触及预期 Proposal 拒绝分支 | 循环在 HTTPResponse.isclosed() 时停止。旧 Linux 镜像单测稳定复现 Bad file descriptor，修复后通过；网关 [29 passed](m5-gateway-transport-regression.xml)。原失败运行已先通过真实 AI → Action → Verification PASS；[数据库回读](m5-runtime/zhiyu-smoke-42708159842b/hallucination-failure-readback.json) 证明错误分类，未伪装成幻觉拒绝成功 |

真实小模型预检曾对 SYNTHETIC 来源作出不充分的语义解释。REFERENCE_GROUNDED 仅是引用完整性结论，模型状态保持 INFERENCE；最终质量报告逐例列出局限，不把格式通过当作事实准确。
