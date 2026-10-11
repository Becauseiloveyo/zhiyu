"""Deterministic, escaped reports derived only from one authorized immutable snapshot."""

import hashlib
import html
import json
import re
from datetime import datetime
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import Field

from zhiyu.product import projections
from zhiyu.product.budgets import response_budget
from zhiyu.product.contracts import DTO, Snapshot, SnapshotMetadata, TimelineEntry
from zhiyu.product.snapshots import digest

MAX_REPORT_BYTES = 10 * 1024 * 1024
SECTIONS: tuple[tuple[str, str, set[str]], ...] = (
    ("summary", "执行摘要", {"incident"}),
    ("scope", "范围与方法", {"resource"}),
    ("evidence", "证据目录", {"evidence", "event"}),
    ("timeline", "事件时间线", {"raw", "normalization", "group", "group_member", "correlation", "audit"}),
    (
        "response",
        "AI 分析、决策与处置",
        {
            "context",
            "ai_context",
            "model_request",
            "model_receipt",
            "model_run",
            "analysis",
            "proposal",
            "decision",
            "plan",
            "task",
            "authorization_context",
            "authorization",
            "risk",
            "approval",
            "action",
            "attempt",
            "result",
        },
    ),
    ("verification", "独立验证", {"verification_spec", "check", "observation", "verification"}),
    ("followup", "状态更新与重规划", {"state_update", "state", "state_relation", "replan"}),
    ("limits", "限制与文档控制", set()),
)
LIMITATIONS = [
    "CONTROLLED LAB；生产环境、长期 SLA、Windows Sensor、Cloud 和 OT/ICS 未验证。",
    "历史记录为 PARTIAL；缺失、未知、过期与截断不等于没有风险。",
    "执行成功不等于安全成功；AI 提案不构成授权；模型自述不能覆盖独立验证。",
    "REFERENCE_GROUNDED 不等于 SEMANTICALLY_CORRECT；模型 confidence 为自报且未校准。",
    "Hash 仅用于关联完整性，不证明内容真实；图和时间线不自动建立攻击因果。",
    "验证结论仅适用于原目标、有效期与三维检查；报告不自动关闭事件。",
    "此文档未经过人工复核、签名或发布审批；没有创建新处置任务。",
]


class Section(DTO):
    id: str
    title: str
    source_refs: list[str]


class Report(SnapshotMetadata):
    schema_version: Literal["zhiyu-incident-report/0.9.0"] = "zhiyu-incident-report/0.9.0"
    report_id: str
    report_status: Literal["UNREVIEWED_DRAFT"] = "UNREVIEWED_DRAFT"
    generated_at: datetime
    report_sha256: str
    snapshot: Snapshot
    summary: dict[str, Any]
    sections: list[Section]
    timeline: list[TimelineEntry] = Field(max_length=2000)
    timeline_truncated: bool
    limitations: list[str]
    reviewer: None = None


def build(snapshot: Snapshot) -> Report:
    if digest([fact.model_dump(mode="json") for fact in snapshot.facts]) != snapshot.content_sha256:
        raise HTTPException(422, "snapshot_integrity_failed")
    root = next(
        (fact for fact in snapshot.facts if fact.kind == "incident" and fact.id == snapshot.incident_id), None
    )
    if root is None:
        raise HTTPException(422, "report_incident_root_missing")
    timeline = projections.timeline(snapshot)
    payload = dict(
        **snapshot.model_dump(mode="json", exclude={"facts"}),
        schema_version="zhiyu-incident-report/0.9.0",
        report_id="RPT-" + snapshot.snapshot_id,
        report_status="UNREVIEWED_DRAFT",
        generated_at=snapshot.as_of.isoformat(),
        snapshot=snapshot.model_dump(mode="json"),
        summary={
            "incident_id": root.id,
            "title": root.fields.get("title"),
            "status": root.fields.get("status"),
            "priority": root.fields.get("priority"),
            "affected_asset_ids": root.fields.get("affected_asset_ids", []),
            "data_origins": sorted(
                {fact.fields["data_origin"] for fact in snapshot.facts if fact.fields.get("data_origin")}
            ),
            "verification_results": [
                {"source_ref": fact.ref, **fact.fields, "freshness_at_snapshot": fact.freshness}
                for fact in snapshot.facts
                if fact.kind == "verification"
            ],
            "execution_results": [
                {"source_ref": fact.ref, "execution_outcome": fact.fields.get("execution_outcome")}
                for fact in snapshot.facts
                if fact.kind == "result"
            ],
            "causal_attack_path": "NOT_ESTABLISHED",
            "overall_security_claim": "NOT_INFERRED_FROM_EXECUTION",
        },
        sections=[
            {
                "id": key,
                "title": title,
                "source_refs": [fact.ref for fact in snapshot.facts if fact.kind in kinds],
            }
            for key, title, kinds in SECTIONS
        ],
        timeline=timeline["entries"],
        timeline_truncated=timeline["truncated"],
        limitations=LIMITATIONS
        + (
            ["RECORDED REPLAY：展示原始快照时的事实与有效性，不表示当前观测；本次读取没有执行模型或 Action。"]
            if snapshot.run_mode == "RECORDED_REPLAY"
            else []
        ),
        reviewer=None,
    )
    # Hash the normalized DTO representation so the downloaded JSON is independently verifiable.
    report = Report.model_validate({**payload, "report_sha256": ""})
    report = report.model_copy(
        update={"report_sha256": digest(report.model_dump(mode="json", exclude={"report_sha256"}))}
    )
    return response_budget(report, MAX_REPORT_BYTES)


def cell(value: Any) -> str:
    text = (
        "未记录"
        if value is None
        else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if isinstance(value, (dict, list))
        else str(value)
    )
    text = html.escape(text, quote=True).replace("\r", " ").replace("\n", " ")
    return re.sub(r"([\\`*_{}\[\]()#+.!|~-])", r"\\\1", text)


def markdown(report: Report) -> dict[str, Any]:
    snapshot = report.snapshot
    lines = [
        "# 智御 · 安全事件响应与独立验证报告",
        "",
        "**未复核草稿 / CONTROLLED LAB**",
        "",
        f"- 报告编号：{cell(report.report_id)}",
        f"- 事件：{cell(snapshot.incident_id)}",
        f"- 运行模式：{snapshot.run_mode}",
        f"- 封存记录 / 来源运行：{cell(snapshot.recording_id)} / {cell(snapshot.source_run_id)}",
        f"- 原快照 / 封存 SHA-256：{cell(snapshot.source_snapshot_id)} / {cell(snapshot.recording_sha256)}",
        f"- 数据来源：{cell(report.summary['data_origins'])}",
        f"- 快照时间：{snapshot.as_of.isoformat()}",
        f"- 快照 ID：{snapshot.snapshot_id}",
        f"- 快照内容 SHA-256：{snapshot.content_sha256}",
        f"- 报告 JSON SHA-256：{report.report_sha256}",
        f"- 环境 / Scope：{cell(snapshot.environment_id)} / {cell(snapshot.scope_id or '获准整环境')}",
        f"- 读取授权版本：{cell(snapshot.access_policy_version)}",
        "- 时间格式：ISO 8601，保留时区。",
        "",
        "报告 JSON Hash 的校验材料为完整 JSON 删除 report_sha256 后的 canonical JSON；快照 Hash 仅覆盖 facts。",
        "",
    ]
    by_ref = {fact.ref: fact for fact in snapshot.facts}
    for index, section in enumerate(report.sections, 1):
        lines += [f"## {index:02d} {section.title}", ""]
        if section.id == "summary":
            lines += [
                f"**{cell(report.summary['title'])}**",
                "",
                f"事件状态：{cell(report.summary['status'])}；优先级：{cell(report.summary['priority'])}。",
                "",
                "执行回执与独立验证分开展示。报告不从执行结果推导总体安全结论。",
                "",
            ]
        if section.id == "scope":
            lines += [
                f"受影响资源：{cell(report.summary['affected_asset_ids'])}",
                "",
                "按原系统明确引用重建记录；原始正文、凭证、敏感 locator 和任意执行参数不包含在工作台报告中。",
                "",
            ]
        if section.id == "timeline":
            lines += ["| 时间 | 阶段 / 时间语义 | 对象来源 | 状态 | 时钟 / 依据 |", "|---|---|---|---|---|"]
            for entry in report.timeline:
                lines.append(
                    "| "
                    + " | ".join(
                        cell(value)
                        for value in (
                            entry.at.isoformat(),
                            entry.stage + " / " + entry.time_semantics,
                            entry.object_ref,
                            entry.status,
                            entry.clock_status + " / " + entry.basis,
                        )
                    )
                    + " |"
                )
            lines += [
                "",
                f"时间线条目：{len(report.timeline)}；截断：{'是' if report.timeline_truncated else '否'}。时间相邻不代表因果。",
                "",
            ]
        if section.id == "verification":
            lines += [
                "SECURITY / BUSINESS / OBSERVABILITY 保留各自原始结果和有效期；过期 PASS 不能证明当前安全。",
                "",
            ]
        if section.id == "response":
            lines += [
                "MODEL_INFERENCE / 模型假设不等于事实；Proposal 不等于 Authorization。授权、风险和 Action Gateway 的已有决定分别保留。",
                "",
            ]
        if section.source_refs:
            lines += ["| 来源记录 | 类型 | 依据 / 快照时有效性 | 记录内容 |", "|---|---|---|---|"]
            for ref in section.source_refs:
                fact = by_ref[ref]
                lines.append(
                    "| "
                    + " | ".join(
                        cell(value)
                        for value in (fact.ref, fact.kind, fact.basis + " / " + fact.freshness, fact.fields)
                    )
                    + " |"
                )
            lines.append("")
        elif section.id != "limits":
            lines += ["本快照未读取到对应记录；不补造步骤、证据或判断。", ""]
        if section.id == "limits":
            lines += [f"- {cell(limit)}" for limit in report.limitations]
            lines += [
                "",
                f"- 快照历史完整性：{snapshot.history_completeness}",
                f"- 快照截断：{'是' if snapshot.truncated else '否'}",
                "- 复核人：未指定；签名及发布审批：未提供。",
                "",
            ]
    if len(lines) > 10000:
        raise HTTPException(413, "report_row_budget_exceeded")
    content = "\n".join(lines)
    result = {
        "report_id": report.report_id,
        "snapshot_id": snapshot.snapshot_id,
        "content_sha256": snapshot.content_sha256,
        "report_sha256": report.report_sha256,
        "filename": report.report_id + ".md",
        "media_type": "text/markdown; charset=utf-8",
        "content": content,
        "export_sha256": hashlib.sha256(content.encode()).hexdigest(),
    }
    return response_budget(result, MAX_REPORT_BYTES)


def json_export(report: Report) -> dict[str, Any]:
    # Preserve exact decimal JSON serialization; browser stringify would change 1.0 to 1.
    content = json.dumps(
        report.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
    )
    return response_budget(
        {
            "report_id": report.report_id,
            "snapshot_id": report.snapshot_id,
            "content_sha256": report.content_sha256,
            "report_sha256": report.report_sha256,
            "filename": report.report_id + ".json",
            "media_type": "application/json; charset=utf-8",
            "content": content,
            "export_sha256": hashlib.sha256(content.encode()).hexdigest(),
        },
        MAX_REPORT_BYTES,
    )
