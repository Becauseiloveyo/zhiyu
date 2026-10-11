# v0.9.0 Browser E2E 验收

日期：2026-10-04，Asia/Shanghai。**Browser E2E PASS**。使用正式 Vite production build、本机真实 FastAPI、独立 canonical PostgreSQL 和 Chromium；未使用预览数据替代 LIVE 结果。机器记录：[browser-e2e.json](../artifacts/v0.9/browser-e2e.json)。

## 页面与一致性

| 检查 | 结果与证据 |
|---|---|
| Overview | 真实 Incident 聚合 KPI、7日趋势、UNKNOWN/N/A 的明确口径；错误后撤下旧 KPI。 |
| Incident list / detail | 有界列表；摘要、决策、验证、证据、记录五页签均可读取。 |
| AI Decision / Authorization / Risk | 实际 Context、ModelRun、分析、SHADOW 提案、授权与 Gateway 回执；不将模型文本当作确定事实。 |
| Verification | 三维结果及过期状态分开；A/C/D/E 的页面文字分别核对真实运行结果。 |
| Timeline / Graph | 同一 snapshot_id/content_sha256；真实时间与 provenance；展开最多两层、200节点、400边、causal=false。 |
| System Status | 实际 SensorHealth；过期/未观测 UNKNOWN。真实停止 API 后旧 KPI 消失且 Sensor 覆盖 UNKNOWN。 |
| Report | 原 Logo 与既定报告布局；JSON/Markdown 下载；报告/事实/文件字节 hash 独立核对。 |
| 分辨率 | 1920×1080 与1366×768无页面级横向溢出；报告与图谱截图已目视检查。图谱画布可内部滚动。 |
| 键盘 | Ctrl K 打开、Escape 关闭命令面板；Tab 可达按钮且2px可见焦点。状态有文本标签。 |

完整操作脚本及原始输出：[gate-e-navigation.cjs](../output/playwright/gate-e-navigation.cjs)、[结果](../output/playwright/gate-e-navigation-result.txt)。截图：[概览](../output/playwright/gate-e-overview-1920.png)、[图谱](../output/playwright/gate-e-graph-1920.png)、[1366报告](../output/playwright/gate-e-report-1366.png)。浏览器导航样本 DOMContentLoaded 414.9ms、load 415.6ms，只有一次本机导航，不是冷缓存 SLA。

## A–E 与重复演示

每个场景均从页面“重置并新建运行”产生新 ID/子环境，执行四步、回放决策/验证/时间线/报告、下载报告，再从页面请求清理。旧记录保留，零所属容器/网络/卷残留已核对。

| 场景 | 重复执行 run_id | 实际结果 |
|---|---|---|
| A | demo-2c165cd7a5bf497dbd842aecaf8be737 | REAL_LOCAL_MODEL；REFERENCE_GROUNDED + SHADOW；独立 PASS |
| B | demo-56d3b10dca6642be8397912b6ce0b4f2 | SCRIPTED_NOT_AI 无效提案 REJECTED；Action=0 |
| C | demo-606cb377989b408094d04ff401ccea7d | 停止 Wazuh Agent，INCONCLUSIVE |
| D | demo-d7a196cd6719410fa05dea6b62294c4a | 脚本声称成功，实际业务故障导致 FAIL；bounded re-plan=1 |
| E | demo-7fca0d0f86ec4896a86794b6507dfd1e | 实际停止模型服务；DETERMINISTIC_FALLBACK；只读基线继续 |

五次回放前后 Event/Action/ModelRun/Verification/Audit 数量完全一致。五份浏览器下载报告的 facts hash、report hash 与预期页面结果通过独立校验。见 [repeatability](../artifacts/v0.9/demo-browser-repeatability.json)、[内容核验](../artifacts/v0.9/demo-browser-content.json)。

最终源码镜像另外从“开始场景 B”按钮创建 `demo-49995d6aa36a4a72b2f9f8859c4f86e1`，完整执行、封存、页面清理通过，见 [final-image-demo](../artifacts/v0.9/final-image-demo.json)。浏览器只提交固定场景意图，Worker 与原安全链负责执行。

## 错误与安全

| 情形 | 方法 | 结果 |
|---|---|---|
| 空列表 | 真实无事件控制环境 | 明确空态 |
| 403 / 404 / 410 | 真实后端拒读、缺失 ID、过期/不存在快照 | 明确说明与重试，无白屏 |
| 500 / 503 / timeout / malformed | 浏览器传输层显式故障注入 | 旧 KPI 撤下；超时8秒结束；解除故障后恢复 |
| API unavailable | 停止经身份核对的本机 API 进程 | 无旧成功状态；恢复进程后重新登录和清理成功 |
| no evidence | 显式响应故障注入，不修改数据库 | “尚无证据记录”空态 |
| HTML / XSS / unsafe Markdown | 在 Incident、Sensor、AI、Evidence 字段注入恶意文本 | 作为文字呈现；0脚本执行、0注入图片、0 javascript 链接 |
| Cookie / CSRF | 实际浏览器请求 | HttpOnly、SameSite=Strict、path=/v1/product；JS不可读取会话；缺CSRF=403 |
| arbitrary payload / foreign env | 实际浏览器直接发起，绕过可见按钮 | 额外 command/target=422；外部环境=403 |
| Core HTTP execution | 当前独立浏览器部署未配置 service token | 503 business_api_not_configured，不能使用 Cookie 执行。配置服务身份后的 Cookie 隔离另由后端测试覆盖。 |

脚本：[错误](../output/playwright/gate-e-errors.cjs)、[不可信输入](../output/playwright/gate-e-untrusted.cjs)、[权限](../output/playwright/gate-e-security.cjs)。故障注入属于 UI 防御测试，不是现场 Sensor 事实或模型质量证据。预期401/403/404/410/500/503、断连会产生控制台网络错误；未为外部浏览器注入脚本放宽 CSP。

范围：本机 Chromium、基本键盘与焦点验证；未声明完整 WCAG、跨浏览器、移动端或长期可靠性认证。
