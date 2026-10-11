"""Generate/check review artifacts. Never changes a database or a migration."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from zhiyu.db import infrastructure, models  # noqa: F401
from zhiyu.db.base import Base
from zhiyu.db.contract_rows import CONTRACT_ROWS

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "0015_ai_decisions", "--sql"],
        cwd=ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    ddl = (
        "-- Generated from fixed Alembic migrations through 0015_ai_decisions; do not edit manually.\n\n"
        + result.stdout
    )
    current = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    lines = [
        "# PostgreSQL Schema — v0.6.0 Remediation / ai.5",
        "",
        "由 `tools/schema_snapshot.py` 从实际 ORM 元数据生成；迁移本身不导入运行时模型。",
        "完整 DDL：[0016_lab_remediation_postgresql.sql](../schema/0016_lab_remediation_postgresql.sql)。历史 SQL 与 0001–0015 迁移保持不变；0016 仅扩展内部执行回执的 Lab 副作用约束。",
        "",
        "| Contract | Table | PK | Columns | Optimistic version |",
        "|---|---|---|---:|---|",
    ]
    for contract, row in CONTRACT_ROWS.items():
        table = row.__table__
        lines.append(
            f"| {contract.__name__} | {table.name} | {', '.join(c.name for c in table.primary_key)} | {len(table.c)} | {'row_version' if 'row_version' in table.c else 'immutable/snapshot'} |"
        )
    lines += [
        "",
        "Internal tables: "
        + ", ".join(sorted(set(Base.metadata.tables) - {row.__tablename__ for row in CONTRACT_ROWS.values()}))
        + ".",
        "",
        "`row_version` 是存储 CAS 计数；`state_version`、`binding_version` 和 Profile/Scope/Policy 的 `version` 保持各自领域语义。",
        "Env/Resource/Scope Repository 使用显式主键字段映射；Scope 的资源关联通过同环境复合 FK 校验。",
        "所有带 environment_id 的契约表均绑定 environments；Incident 下的核心对象用复合 FK 防止跨环境关联。",
        "EventGroup、Decision、Incident 的契约数组保留为快照；成员、输入/排除、Incident→Group/Event→Evidence 使用关系表查询和复合 FK。Evidence FK 同时校验 Incident 归属。",
        "0002 保存原始 BYTEA 与逐条摄取结果；0003 保存分组元数据、成员、决策输入与运行指标；0004 保存晋升记录、风险解释及 Incident 关联。",
        "0005–0007 添加响应规划、授权与执行元数据；0008–0010 添加独立验证与有界 Re-plan，累计 63 张业务/内部表。0011–0015 添加 Context、模型请求/回执/预算、分析、提案与决策元数据，累计 71 张业务/内部表，另有 alembic_version。",
        "降级会删除新增阶段的内部元数据；正向升级保持旧 M1 数据，完整升级/降级测试使用隔离 schema。业务数据回退应使用数据库备份恢复，不能把 schema downgrade 当作无损业务撤回。",
        "",
        "## 约束与事务选择",
        "",
        "- 来源唯一键：environment_id / collector_id / source_type / origin_event_id / event_type。timestamp 不构成重发的逃生通道；同身份内容改变报冲突。",
        "- event_id 是全局标识。相同内容的跨 Collector 转发仍保存；provenance_group 没有 UNIQUE。",
        "- Action 幂等：environment_id / idempotency_key；全字段 action_digest 与授权输入、决策关联。Gateway 分发注册只读执行器及显式授权的隔离 Lab HTTP 路径能力；action_id/generation 唯一，回执不可变。Lab UNKNOWN 只读核对，不自动重放；目标原生 TTL 与 owner/generation/digest CAS 保护补偿。",
        "- Task lease 的 (task_id, generation) 唯一，active_lease 绑定相同 Task；M3 Scheduler 实现 Claim/过期/有界退避和代次守卫，旧 Worker ACK 被拒绝。",
        "- Incident 所有生命周期时间均为真实列；合法枚举、关闭最低字段、时间区间和三个验证维度的 verdict 有 CHECK。",
        "- Audit、事件、收据、ActionRequest、Approval、AuthorizationContext/Decision 禁止 UPDATE/DELETE；受控保留/归档需后续明确实现。数据库管理员仍能改变 schema，哈希链不是外部签名。",
        "- Bootstrap 与事件批次由 Service 管理 BEGIN/COMMIT，Repository 不 commit。每环境按固定顺序加锁；这是 M1 的保守并发选择，尚无吞吐承诺。",
        "- Outbox 使用 SKIP LOCKED、DB 时间、generation、lease_until；ACK 必须匹配未过期的 claim。崩溃后可重领，不承诺 exactly-once。下游必须按 message_id 去重。",
        "- 循环 FK 在所有表创建后显式建立；固定迁移回滚时先移除循环 FK 和不可变触发器，再逆序删除表。",
        "",
    ]
    artifacts = {
        ROOT / "schema/0015_ai_decision_postgresql.sql": ddl,
        ROOT
        / "schema/0016_lab_remediation_postgresql.sql": "-- Generated through 0016_lab_remediation; historical SQL retained separately.\n\n"
        + current.stdout,
        ROOT / "docs/SCHEMA.md": "\n".join(lines),
    }
    for path, content in artifacts.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                print("stale artifact:", path.name)
                return 1
        else:
            path.write_text(content, encoding="utf-8")
    print(f"Schema artifacts {'verified' if args.check else 'generated'}: {len(Base.metadata.tables)} tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
