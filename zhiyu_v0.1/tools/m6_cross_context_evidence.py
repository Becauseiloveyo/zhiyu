"""Read back actual foreign records and immutable contexts used by Gate C attacks."""

import json
from pathlib import Path

from m6_ai_evaluation import save
from sqlalchemy import text

from zhiyu.db.session import get_engine


def main():
    engine = get_engine()
    root = Path("/safety-output")
    paths = sorted(root.glob("boundaries-*/cross-context.json"))
    experiments = []
    for path in paths:
        value = json.loads(path.read_text())
        foreign = value["foreign_records"]
        with engine.connect() as connection:
            rows = {}
            for table in ["environments", "scopes", "decision_contexts"]:
                rows[table] = connection.scalars(
                    text(
                        "SELECT row_to_json(r) FROM "
                        + table
                        + " r WHERE environment_id IN (:a,:b) ORDER BY row_to_json(r)::text"
                    ),
                    {"a": value["lab_a"], "b": value["lab_b"]},
                ).all()
            rows["foreign_evidence"] = connection.scalar(
                text("SELECT row_to_json(r) FROM evidence r WHERE evidence_id=:id"),
                {"id": foreign["evidence"]},
            )
            rows["foreign_resource"] = connection.scalar(
                text("SELECT row_to_json(r) FROM resources r WHERE resource_id=:id AND environment_id=:env"),
                {"id": foreign["resource"], "env": value["lab_b"]},
            )
            rows["foreign_capability_definition"] = connection.scalar(
                text("SELECT row_to_json(r) FROM capabilities r WHERE capability_id=:id AND version='1.0.0'"),
                {"id": foreign["capability"]},
            )
        assert rows["foreign_evidence"]["environment_id"] == value["lab_b"]
        assert rows["foreign_resource"]["environment_id"] == value["lab_b"]
        b_contexts = [
            c
            for c in rows["decision_contexts"]
            if c["environment_id"] == value["lab_b"]
            and foreign["capability"] in [cap["capability_id"] for cap in c["body"]["allowed_capabilities"]]
        ]
        assert b_contexts, "need actual captured lab-b capability authority, not just a string"
        experiments.append(
            {
                "experiment": str(path.relative_to(root)),
                "rows": rows,
                "lab_b_context_ids_with_foreign_capability": [c["context_id"] for c in b_contexts],
            }
        )
    assert experiments
    save(
        root / "cross-environment-records.json",
        {
            "status": "PASS",
            "experiments": experiments,
            "semantics": "Capability definitions are global; captured current scope/environment authority is not transferable",
        },
    )
    print("PASS: foreign Evidence/Resource and lab-b captured Capability context exist")


if __name__ == "__main__":
    main()
