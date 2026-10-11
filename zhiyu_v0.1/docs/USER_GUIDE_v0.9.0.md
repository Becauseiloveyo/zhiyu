# 智御 v0.9.0 Web Console 使用说明

状态：v0.9.0 PASS / CONTROLLED LAB；生产部署未验证。沿用现有 React 浏览器工作台及 Linux 核心，不需要 Electron。

## 本机受控演示环境

使用 Python 3.12、Node 与 Docker Desktop/Linux Engine。首次解包先执行 `uv sync --locked --all-extras --python 3.12` 安装锁定 Python 依赖；以下 `python` 使用该虚拟环境，也可写为 `uv run --locked python`。以下命令在工程根目录执行：

```text
python tools/m9_local_validation.py --ensure-only
docker compose -f docker-compose.sensors.yml build target wazuh-manager
npm --prefix frontend ci
npm --prefix frontend run build
python tools/m9_demo.py prepare
```

本地模型权重应放在工作区父目录 `.work/m5-model/qwen2.5-1.5b-instruct-q4_k_m.gguf`。固定 SHA-256 为 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`，预检校验；权重不打入代码镜像。`prepare` 为演示创建独立数据库，安装原核心迁移和 `zhiyu_product` 元数据，构建源代码镜像，生成独立本机操作员密钥。普通 API 的默认配置仍没有启用任何演示 profile。

Docker 重启后 PostgreSQL 的随机宿主端口可能改变。先重新执行 `prepare` 更新本机连接配置，再启动 API/Worker；该操作保留原数据库与运行历史。旧会话和内存快照在 API 重启后需重新取得。

两个终端分别启动：

```text
python tools/m9_demo.py serve
python tools/m9_demo.py worker
```

打开 `http://127.0.0.1:8000`。本地管理员从工作区父目录 `.work/m9-demo/deployment.private.json` 取得 username/access_key。该文件还含数据库配置，不能上传、截图、加入演示资料或交付包。浏览器使用 HttpOnly 会话和 CSRF，访问密钥不会写入 localStorage。

API 进程不持有 Docker 控制接口。独立 Worker 仅支持固定受控适配器；runner 容器没有 Docker socket、任意主机日志挂载或外部攻击目标。授权、风险和执行仍由原核心完成。

## 查询与分析

- 环境和 Scope 决定当前可读范围；演示子环境继承登记控制环境的当前授权，撤权后历史回放同样不可读。
- “事件”提供状态、优先级、文本及时间窗筛选；列表最多50条并分页。详情以固定快照贯穿时间线、图谱和报告。
- Snapshot 过期时明确提示刷新；历史回放刷新仍读同一个封存档案，不切到 LIVE。
- 证据、模型推断、提案、授权、执行收据与 Verification 分开展示。REFERENCE_GROUNDED 只表示引用检查，不证明模型语义正确。
- 图谱来自实际引用关系，未证实因果关系不会画成攻击事实。大记录集有明确截断与分页提示。
- 系统健康读取实际 SensorHealth；观测过期/未覆盖显示 UNKNOWN。页面在可见期间定时重读健康，API 失败不继续显示旧的 Healthy。

## 固定演示、清理与回放

在 `v09-demo-control` 的“演示”页选择登记 profile，启动 A–E。每个 profile 同时只允许一个未清理运行。模型、故障注入、目标地址与能力都在服务端固定，浏览器不能修改。

运行记录区显示步骤、实际/预期结果、模型来源、错误和清理状态。点击“刷新运行状态”获取进展。“停止后续步骤”不会声称撤销已经发出的 Action；在途结果保留，不确定步骤不会自动重派。

终态可请求清理。只有经过归属校验及零残留核对才成为 CLEAN；核心事件、审计、报告、回放继续保留。之后“重置并新建运行”使用新的运行 ID/环境，不覆盖旧结果。查看本次事件使用 LIVE 当前数据库投影；历史回放使用已封存的不可变快照，页面明确标记 RECORDED REPLAY，仅读取，不调用模型或执行安全动作。

CLI 的 `run --scenario A`、`cleanup --run-id …` 和 `status` 是验收驱动，复用相同控制器和 Worker。不要同时用两个驱动抢占同一 profile。不要手工把未知步骤改成 COMPLETED。

包内 `artifacts/v0.9/recordings`、`output/playwright/downloads` 与截图保存本次验收样本。复制档案文件不会自动导入旧数据库或授予历史环境权限；新部署应运行固定场景生成本地事实与回放登记，已有部署则保留其 canonical 数据库。离线 JSON/Markdown 样本可直接审阅。

## 报告与范围

报告提供 JSON 和转义 Markdown，下载前浏览器核对原始字节 SHA-256；封存事实 hash、报告内容 hash 和文件 hash 是不同值。文档为未复核草稿，没有人工签名、发布审批或自动关闭 Incident 的含义。缺失证据与未验证结论按原样保留。

CONTROLLED LAB 不等于生产可用性证明；Production、客户部署、长期 SLA、Cloud、Windows Sensor、OT/ICS 均未验证。模型一般语义准确性未被证明。高风险自主执行不在本版本范围。
