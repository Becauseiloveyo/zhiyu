"""Render actual load and resource measurements with explicit measurement boundaries."""

import json
import re
from datetime import datetime

from runtime_acceptance import ROOT

DIRECTORY = ROOT / "docs/m6-runtime/gate-d-001"


def read(name):
    path = DIRECTORY / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def resources(path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    cpu, docker_memory, model_memory, rss, swaps, states = {}, {}, [], [], [], []
    errors = 0
    for row in rows:
        for line in row.get("stats", {}).get("stdout", "").splitlines():
            stat = json.loads(line)
            service = stat["Name"].rsplit("-", 2)[-2]
            if stat["Name"].endswith("-local-model-1"):
                service = "local-model"
            cpu.setdefault(service, []).append(float(stat["CPUPerc"].rstrip("%")))
            docker_memory.setdefault(service, []).append(stat["MemUsage"])
        raw = row.get("model_memory", {}).get("stdout", "")
        if raw and raw.splitlines()[0].isdigit():
            model_memory.append(int(raw.splitlines()[0]))
            swaps.append(int(raw.splitlines()[2]))
            match = re.search(r"^VmRSS:\s+(\d+) kB$", raw, re.MULTILINE)
            if match:
                rss.append(int(match[1]) * 1024)
        for line in row.get("states", {}).get("stdout", "").splitlines():
            state, restarts = line.rsplit(" ", 1)
            state = json.loads(state)
            states.append({"running": state["Running"], "oom": state["OOMKilled"], "restarts": int(restarts)})
        errors += sum(
            value.get("returncode", 1) != 0
            for key, value in row.items()
            if key in {"stats", "states", "model_memory"}
        )
    return {
        "samples": len(rows),
        "first": rows[0]["observed_at"],
        "last": rows[-1]["observed_at"],
        "span_seconds": (
            datetime.fromisoformat(rows[-1]["observed_at"]) - datetime.fromisoformat(rows[0]["observed_at"])
        ).total_seconds(),
        "cpu_percent_max": {key: max(values) for key, values in cpu.items()},
        "docker_memory_first_last": {key: [values[0], values[-1]] for key, values in docker_memory.items()},
        "model_cgroup_current_bytes": {
            "first": model_memory[0],
            "last": model_memory[-1],
            "max_observed": max(model_memory),
        }
        if model_memory
        else None,
        "model_rss_max_observed_bytes": max(rss) if rss else None,
        "model_swap_max_observed_bytes": max(swaps) if swaps else None,
        "all_observed_running": bool(states) and all(s["running"] for s in states),
        "oom_observed": any(s["oom"] for s in states),
        "restart_counts_observed": sorted({s["restarts"] for s in states}),
        "metrics_errors": errors,
        "limits": "Periodic samples, not continuous extrema. CPU percent sums logical cores. Docker memory and cgroup/process RSS use different accounting.",
    }


def main():
    collected = {
        p.name.removesuffix("-resources.jsonl"): resources(p) for p in DIRECTORY.glob("*-resources.jsonl")
    }
    for phase, row in collected.items():
        measurement = read(("ai-load" if phase == "ai" else phase) + ".json")
        if measurement and measurement.get("started_at") and measurement.get("finished_at"):
            row["coverage"] = {
                "workload_started_at": measurement["started_at"],
                "workload_finished_at": measurement["finished_at"],
                "unobserved_head_seconds": max(
                    0,
                    (
                        datetime.fromisoformat(row["first"])
                        - datetime.fromisoformat(measurement["started_at"])
                    ).total_seconds(),
                ),
                "unobserved_tail_seconds": max(
                    0,
                    (
                        datetime.fromisoformat(measurement["finished_at"])
                        - datetime.fromisoformat(row["last"])
                    ).total_seconds(),
                ),
                "semantics": "Periodic samples only; no interpolation or claim about unobserved intervals.",
            }
    (DIRECTORY / "resource-review.json").write_text(json.dumps(collected, indent=2), encoding="utf-8")
    soak = read("soak.json")
    events = read("events.json")
    completion = read("events-streaming.json")
    ai = read("ai-load.json")
    final_path = DIRECTORY.parent / "gate-d-acceptance.json"
    status = json.loads(final_path.read_text())["status"] if final_path.exists() else "IN_PROGRESS"
    lines = [
        "# v0.6.0 Performance / Resource Baseline",
        "",
        f"**Gate D：{status}。本机受控 Lab 的合成负载实测，不是生产 SLA 或长期稳定性证明。**",
        "",
        "所有原始数据位于 [gate-d-001](m6-runtime/gate-d-001/result.json)。真实传感器链已在 Gate A 单独验收，本性能实验中的事件与健康夹具仍标为 SYNTHETIC。使用真实 PostgreSQL、只读执行器、独立 HTTP HEAD 和本地模型；没有外部目标扫描。",
        "",
        "数据库复用 B/C 专用 Lab，保留已有数据；各负载创建独立实验环境。soak 在 9 月 18 日完成，其后分级负载跨日继续，各阶段实际起止时间在原始 JSON 中；中间空闲时间不计入 soak。源码只读挂载在已验证依赖镜像中，最终烘焙镜像验收属于 Gate E。",
        "",
        "## 事件负载",
        "",
        "Adapter 归一化另作一次独立计时；ingest 自身也包含归一化、数据库和事务开销，两者不可相加冒充独立流水线阶段。分组/关联合并计时；下表累计耗时排除准备工作、最终指标读取与明确记录的暂停。批次 p50/p95/p99 的单位是每 1000 条事件批次，不是单事件延迟。",
        "",
        "| 请求条数 | 实际条数 | 状态 | ingest s | group/correlate s | promotion s | pipeline s |",
        "|---:|---:|---|---:|---:|---:|---:|",
    ]
    if events:
        values = events["results"][:]
        if completion and completion.get("status") == "COMPLETED_MEASUREMENT":
            values[-1] = completion["result"]
        for row in values:
            lines.append(
                f"| {row['requested_events']} | {row['events']} | {row['status']} | {row['ingest_seconds']:.2f} | {row['correlation_total_seconds']:.2f} | {row['promotion_total_seconds']:.2f} | {row['pipeline_total_seconds']:.2f} |"
            )
    else:
        lines.append("| — | — | NOT_RUN | — | — | — | — |")
    lines += [
        "",
        "100k 首段采用 1200 秒预算，在完整批次边界结束，66,000 条记录保留为 PARTIAL_TIME_BUDGET。暂停后用原时间戳继续，输入已跨过固定窗口及迟到宽限，正确变成大量 LATE 单事件隔离，测量中止并保留；其 73,000 条已提交事件和审计经复核完整，pending 已清零。这些慢样本不冒充正常分组吞吐。新的 [events-streaming.json](m6-runtime/gate-d-001/events-streaming.json) 在独立环境以每批实际生成时间完整重测 100k，保持相同关联/迟到策略；上表只在其完成后采用新结果。原始首段、续跑和迟到诊断分别保留在 events.json、events-completed.json 与 late-continuation-review.json。",
        "",
        "## 只读响应与独立验证负载",
        "",
        "响应每批最多 300 个任务，验证每批最多 100 组三维检查，使用新 Incident/Scope 控制夹具有效期。该分区方法不能外推为同一租户或 Incident 的容量。验证的 100/1000/10000 表示 individual checks；每组含三项，因此实际数量向上取三的倍数。每批末次检查故意让安全断言 FAIL，检验独立判定和一次诊断 replan；不能把预期的安全断言 FAIL 算作执行故障。",
        "",
        "| 类别 | 请求 | 实际 | 状态 | 累计秒 | 有意保留的后续任务 |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for kind in ["response", "verification"]:
        report = read(kind + ".json")
        if not report:
            lines.append(f"| {kind} | — | — | NOT_RUN | — | — |")
            continue
        for row in report["results"]:
            lines.append(
                f"| {kind} | {row['requested']} | {row.get('actual', 0)} | {row['status']} | {row.get('elapsed_seconds', 0):.2f} | {row.get('intentional_unexecuted_tail_tasks', 'pending')} |"
            )
    lines += [
        "",
        "原始样本覆盖 Scheduler lease、Authorization、Risk Gate、Action Gateway/Executor，以及 verification scheduling/execution/decision/Evidence/State update。汇总同时给 p50/p95/p99，样本数较小时尾分位只能视为观察值。排队未执行的尾部任务与诊断后续任务如实列出；不声称已经排空所有业务队列。",
        "",
        "最大已测档的阶段延迟（ms；事件为 1000 条批次，任务/检查为各次阶段操作）：",
        "",
        "| 负载 | 阶段 | 样本 | p50 | p95 | p99 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    stages = {}
    if completion and completion.get("status") == "COMPLETED_MEASUREMENT":
        stages["events-100k"] = completion["result"].get("stage_batch_latency", {})
    for kind in ["response", "verification"]:
        measured = read(kind + ".json")
        if measured and measured.get("status") == "COMPLETED_MEASUREMENT":
            stages[kind + "-10k"] = measured["results"][-1]["stage_latency"]
    for kind, stage in stages.items():
        for name, values in stage.items():
            lines.append(
                f"| {kind} | {name} | {values['count']} | {values['p50_ms']:.2f} | {values['p95_ms']:.2f} | {values['p99_ms']:.2f} |"
            )
    lines += [
        "",
        "## AI 小负载",
        "",
        "保持单模型 slot、6 线程、1200 输出 tokens、110 秒客户端超时，测 10 次顺序与 2/4 请求同步小并发，不提高并行 slot。provider_ms 包含传输、排队和推理，Gateway overhead、Context build 单独计量。当前接口未单独暴露逐请求排队时长，故标为 NOT_SEPARATELY_MEASURED；以同时到达/完成时间、超时与服务器 slot 日志反映排队行为。",
        "",
        "| 模式 | 请求 | 可计量响应 | 结果 | p50/p95/p99 总分析 ms |",
        "|---|---:|---:|---|---|",
    ]
    if ai:
        for group in ai["groups"]:
            latency = group.get("analysis_latency", {})
            lines.append(
                f"| {group['kind']} | {group['requested_calls']} | {group.get('metered_responses', 'pending')} | {json.dumps(group.get('analysis_statuses', {}))} | {', '.join(str(round(latency[k], 2)) for k in ['p50_ms', 'p95_ms', 'p99_ms'] if k in latency)} |"
            )
    else:
        lines.append("| — | — | — | NOT_RUN | — |")
    if ai and ai.get("status") == "COMPLETED_MEASUREMENT":
        lines += [
            "",
            "| 模式 | 已计量 input / output tokens | 传输/排队/推理 p50 / p95 / p99 ms | Gateway overhead p50 / p95 / p99 ms |",
            "|---|---|---|---|",
        ]
        for group in ai["groups"]:
            runs = [run for row in group["results"] for run in row["runs"]]
            tokens = (
                f"{sum(r['input_tokens'] or 0 for r in runs)} / {sum(r['output_tokens'] or 0 for r in runs)}"
            )
            timing = [
                " / ".join(f"{group[name][key]:.2f}" for key in ["p50_ms", "p95_ms", "p99_ms"])
                for name in ["provider_latency", "gateway_overhead"]
            ]
            lines.append(f"| {group['kind']} | {tokens} | {timing[0]} | {timing[1]} |")
        lines += [
            "",
            "超时而未返回 usage 的请求不能据零计量推断零服务器计算；服务端原日志保留排队、处理与取消记录。",
        ]
    lines += [
        "",
        "预算耗尽必须在第二次 Gateway 请求处阻止 provider 调用；不把拒绝计作一次模型推理。SHADOW 始终无 AI Executor 调用。实际 token、失败码、模型输出与数据库快照保留，不发布语义准确率。",
        "",
        "## 30 分钟 soak",
        "",
    ]
    if soak:
        lines += [
            f"状态 {soak['status']}，实际 {soak.get('elapsed_seconds', 0):.3f} 秒，完成 {len(soak['cycles'])} 轮；每轮四条新事件及四次重放、三个只读任务、三项独立检查。每十轮一次真实模型分析。",
            "",
            f"最终数据库/队列指标：`{json.dumps(soak.get('final_metrics', {}), ensure_ascii=False)}`",
            "",
            "未配置 Outbox 消费者，待发布消息增长是明确的持久化积压，不冒充已投递或零队列。业务任务与验证检查的状态另行记录。10 秒 pilot 因未装载模型凭证发生 CREDENTIAL_UNAVAILABLE；修正入口后正式 soak 重新使用独立身份，失败预检仍保留。",
        ]
    lines += [
        "",
        "## 资源观测",
        "",
        "| 阶段 | 样本 | 模型 cgroup 最大观测 bytes | 模型 RSS 最大观测 bytes | swap 最大观测 bytes | OOM / restart counts |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name, row in collected.items():
        mem = row["model_cgroup_current_bytes"] or {}
        lines.append(
            f"| {name} | {row['samples']} | {mem.get('max_observed', 'N/A')} | {row['model_rss_max_observed_bytes']} | {row['model_swap_max_observed_bytes']} | {row['oom_observed']} / {row['restart_counts_observed']} |"
        )
    lines += ["", "资源采样与实际负载的覆盖缺口（秒；正常采样周期也会留下边缘间隔）：", ""]
    for name, row in collected.items():
        coverage = row.get("coverage")
        if coverage:
            lines.append(
                f"- {name}：开始前未覆盖 {coverage['unobserved_head_seconds']:.2f}，结束前未覆盖 {coverage['unobserved_tail_seconds']:.2f}。"
            )
    lines += [
        "",
        "[resource-review.json](m6-runtime/gate-d-001/resource-review.json) 保留各容器 CPU 峰值、Docker 内存首尾、采样范围与采集错误数；原 JSONL 保留全部实际读数。Docker stats 内存与 cgroup/RSS 口径不同，不能混用。短期观测未增长不等于证明没有内存泄漏；没有数据的时段不作稳定性结论。",
        "",
        "| 阶段 | 容器 | CPU 最大观测 % | Docker 内存首值 | Docker 内存末值 |",
        "|---|---|---:|---|---|",
    ]
    for name, row in collected.items():
        for service, cpu in row["cpu_percent_max"].items():
            first, last = row["docker_memory_first_last"][service]
            lines.append(f"| {name} | {service} | {cpu:.2f} | {first} | {last} |")
    lines += [
        "",
        "各阶段数据库体积与连接数（包含先前 Lab 数据，连接数为边界采样，不是持续峰值）：",
        "",
        "| 阶段 | 初始 bytes | 最终 bytes | 初始连接 | 最终连接 |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in ["events", "events-streaming", "response", "verification"]:
        measured = read(name + ".json")
        if measured and measured.get("final_database"):
            first, last = measured["initial_database"], measured["final_database"]
            lines.append(
                f"| {name} | {first['size_bytes']} | {last['size_bytes']} | {first['connections']} | {last['connections']} |"
            )
    lines += [
        "",
        "## 瓶颈与剩余",
        "",
        "阶段耗时用于定位 ingest 的 ORM/事务开销、分组/关联和 promotion 的相对占比；它们尚不能单独证明某条 SQL 是根因。单 slot 的模型服务会串行处理请求，较长队列可能触发客户端超时并安全回退。未引入新的消息中间件或调度架构。最终 Gate D 结论必须结合完整负载结果、Audit/幂等/安全检查与数据库快照；总版本仍以 VALIDATION_REPORT_v0.6.0.md 为准。",
        "",
    ]
    queues = read("load-queue-review.json")
    if queues:
        lines += [
            f"最终 [队列复核](m6-runtime/gate-d-001/load-queue-review.json)：{len(queues['environments'])} 个已记录实验环境，运行中任务 {queues['running_tasks']}，未分组事件 {queues['ungrouped_events']}，有意保留的后续任务 {queues['actual_pending_tasks']}，未发布 Outbox {queues['pending_outbox']}。所有积压均保留并明确计数，没有为了得到零队列而清除数据。",
            "",
        ]
    (ROOT / "docs/PERFORMANCE_REPORT_v0.6.0.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"gate_d": status, "resource_phases": len(collected)}))


if __name__ == "__main__":
    main()
