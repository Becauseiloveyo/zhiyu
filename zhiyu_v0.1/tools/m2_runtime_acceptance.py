"""M1.1 regression plus real Docker HTTP event-to-incident acceptance."""

import copy
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from runtime_acceptance import ROOT, Acceptance
from runtime_acceptance import main as runtime_main

M2_SNAPSHOT = r"""
import hashlib,json
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from zhiyu.db.session import get_engine
from zhiyu.repositories.audit import AuditRepository
from zhiyu.db.models import IncidentRow,EventRow,EvidenceRow
from zhiyu.db.mapping import contract_from
from zhiyu.domain.contracts import NormalizedEvent
from zhiyu.services.incident_engine import raw_for_events
env='m2-golden'
tables=['raw_records','normalized_events','event_groups','event_group_state','event_group_members','correlation_decisions','correlation_decision_inputs','incidents','incident_analysis','incident_groups','incident_events','incident_promotions','evidence']
with get_engine().connect() as c:
    state={table:c.scalars(text('SELECT row_to_json(r) FROM '+table+' r WHERE environment_id=:env ORDER BY row_to_json(r)::text'),{'env':env}).all() for table in tables}
    operations=dict(c.execute(text('SELECT operation,count(*) FROM audit_entries WHERE environment_id=:env GROUP BY operation'),{'env':env}).all())
    outbox=dict(c.execute(text('SELECT event_type,count(*) FROM outbox WHERE environment_id=:env GROUP BY event_type'),{'env':env}).all())
with Session(get_engine()) as db:
    chain=AuditRepository(db).verify_chain(env)
    incidents=list(db.scalars(select(IncidentRow).where(IncidentRow.environment_id==env)))
    lineage=True
    for incident in incidents:
        events=[contract_from(row,NormalizedEvent) for row in db.scalars(select(EventRow).where(EventRow.environment_id==env,EventRow.event_id.in_(incident.related_event_ids)))]
        raws=raw_for_events(db,env,events)
        evidence=list(db.scalars(select(EvidenceRow).where(EvidenceRow.environment_id==env,EvidenceRow.incident_id==incident.incident_id)))
        lineage &= len(raws)==len(events)==len(evidence)==3
        for item in evidence:
            lineage &= item.integrity_hash==raws[item.source_event_ids[0]].integrity_hash
print(json.dumps({'counts':{table:len(rows) for table,rows in state.items()},'hash':hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest(),'audit_operations':operations,'outbox_events':outbox,'audit_valid':chain,'lineage_valid':lineage}))
"""


class M2Acceptance(Acceptance):
    benchmark = False

    def __init__(self, report_dir: Path) -> None:
        super().__init__(report_dir)
        tokens = json.loads(self.env["ZHIYU_SERVICE_TOKENS"])
        for principal in tokens.values():
            principal["environment_ids"].append("m2-golden")
            principal["source_types"].append("wazuh")
            principal["permissions"] += ["events:synthetic", "intelligence:write", "incidents:write"]
        self.env["ZHIYU_SERVICE_TOKENS"] = json.dumps(tokens)

    def request(self, path: str, body: dict | None = None) -> tuple[int, dict]:
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.token},
        )
        try:
            with self.http.open(request, timeout=30) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def m2_snapshot(self) -> dict:
        return json.loads(self.compose("exec", "-T", "api", "python", "-c", M2_SNAPSHOT).stdout)

    def run(self, *, no_cache: bool) -> None:
        super().run(no_cache=no_cache)
        bootstrap = """
from pathlib import Path
from sqlalchemy.orm import Session
from zhiyu.db.session import get_engine
from zhiyu.services.bootstrap import BootstrapBundle,BootstrapService
bundle=BootstrapBundle.model_validate_json(Path('config/bootstrap.lab.json').read_text())
bundle.environment.environment_id='m2-golden'
for resource in bundle.resources: resource.environment_id='m2-golden'
for scope in bundle.scopes: scope.environment_id='m2-golden'
with Session(get_engine()) as db: print(BootstrapService(db).apply(bundle,actor_id='m2-golden-bootstrap'))
"""
        self.compose("exec", "-T", "api", "python", "-c", bootstrap)
        fixture = json.loads((ROOT / "tests/fixtures/golden_chain_m2.json").read_text(encoding="utf-8"))
        # All fixtures share one actual current minute, avoiding stale historical test timestamps.
        reference = datetime.now(UTC).replace(second=0, microsecond=0)
        batches = []
        for source in ("suricata", "wazuh"):
            records = []
            for item in fixture["records"]:
                if item["source_type"] != source:
                    continue
                raw = copy.deepcopy(item["raw"])
                raw["timestamp"] = reference.isoformat()
                records.append({"record": json.dumps(raw), "origin_event_id": item["origin"]})
            batch = {
                "environment_id": "m2-golden",
                "collector_id": "sensor-" + source,
                "source_type": source,
                "data_origin": "SYNTHETIC",
                "records": records,
            }
            batches.append(batch)
            status, result = self.request("/v1/events/raw-batches", batch)
            self.check(
                "m2_raw_" + source,
                status == 202 and result["accepted"] == len(records) and result["errors"] == 0,
                result,
            )
        (self.directory / "golden-effective-inputs.json").write_text(
            json.dumps(batches, indent=2), encoding="utf-8"
        )
        status, pipeline = self.request("/v1/intelligence/process", {"environment_id": "m2-golden"})
        self.check(
            "m2_pipeline",
            status == 200
            and pipeline["correlation"]["processed"] == 4
            and pipeline["correlation"]["groups_created"] == 2
            and len(pipeline["correlation"]["decision_ids"]) == 2
            and pipeline["incidents"]["created"] == 1,
            pipeline,
        )
        identifier = next(x["incident_id"] for x in pipeline["incidents"]["results"] if x["incident_id"])
        _, assessment = self.request(f"/v1/incidents/{identifier}/assessment")
        _, events = self.request(f"/v1/incidents/{identifier}/events?limit=2")
        _, next_page = self.request(
            f"/v1/incidents/{identifier}/events?cursor=" + urllib.parse.quote(events["next_cursor"])
        )
        self.check(
            "m2_risk_pagination_unrelated_excluded",
            assessment["risk"]["score"] == 62
            and len(events["items"]) == 2
            and len(next_page["items"]) == 1
            and all(
                not any(o["value"] == "unrelated-bob" for o in event["observables"])
                for event in events["items"] + next_page["items"]
            ),
            assessment,
        )
        initial = self.m2_snapshot()
        self.check(
            "m2_audit_outbox_lineage",
            initial["audit_valid"]
            and initial["lineage_valid"]
            and initial["outbox_events"]["EventGroupCreated"] == 2
            and initial["outbox_events"]["CorrelationDecisionCreated"] == 2
            and initial["outbox_events"]["IncidentCreated"] == 1,
            initial,
        )
        for target, version in [("TRIAGED", 1), ("INVESTIGATING", 2)]:
            body = {"environment_id": "m2-golden", "target": target, "expected_version": version}
            status, result = self.request(f"/v1/incidents/{identifier}/transitions", body)
            self.check(
                "m2_transition_" + target,
                status == 200 and result["status"] == target and result["state_version"] == version + 1,
            )
        saved = self.m2_snapshot()
        self.compose("restart", "api")
        self.locate_api()
        self.await_http("/ready", 200)
        self.check("m2_api_restart", self.m2_snapshot()["hash"] == saved["hash"])
        self.compose("restart", "postgres")
        self.wait_service("postgres")
        self.await_http("/ready", 200)
        self.check("m2_db_restart", self.m2_snapshot()["hash"] == saved["hash"])
        for batch in batches:
            status, result = self.request("/v1/events/raw-batches", batch)
            self.check(
                "m2_replay_" + batch["source_type"],
                status == 202 and result["duplicates"] == len(batch["records"]) and result["accepted"] == 0,
            )
        status, replay = self.request("/v1/intelligence/process", {"environment_id": "m2-golden"})
        self.check(
            "m2_no_duplicate_groups_decisions_incidents",
            status == 200
            and replay["correlation"]["processed"] == 0
            and replay["incidents"]["evaluated"] == 0
            and self.m2_snapshot()["hash"] == saved["hash"],
        )
        self.report["golden_chain"] = {
            "fixture_label": fixture["label"],
            "raw": 4,
            "normalized": 4,
            "groups": 2,
            "decisions": 2,
            "incidents": 1,
            "evidence": 3,
            "risk_score": assessment["risk"]["score"],
            "unrelated_excluded": True,
            "snapshot": self.m2_snapshot(),
        }
        _, self.report["m2_metrics"] = self.request("/v1/intelligence/metrics?environment_id=m2-golden")
        if self.benchmark:
            name = self.project + "-benchmark"
            print("BENCHMARK: 1k and 10k synthetic events in Linux container", flush=True)
            runner = "import os,runpy; os.environ['ZHIYU_DATABASE_URL']=os.environ['ZHIYU_TEST_DATABASE_URL']; runpy.run_path('tools/benchmark.py',run_name='__main__')"
            self.compose(
                "--profile",
                "test",
                "run",
                "--no-deps",
                "-T",
                "--name",
                name,
                "tests",
                "python",
                "-c",
                runner,
                "--output",
                "/tmp/benchmark.json",
                timeout=1800,
            )
            self.docker("cp", name + ":/tmp/benchmark.json", str(self.directory / "benchmark.json"))
            self.docker("rm", name)
            measured = json.loads((self.directory / "benchmark.json").read_text())
            self.check(
                "m2_benchmark_measured", [x["events"] for x in measured["results"]] == [1000, 10000], measured
            )
            self.report["benchmark"] = measured
        self.save()


if __name__ == "__main__":
    raise SystemExit(runtime_main(M2Acceptance))
