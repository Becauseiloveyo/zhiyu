"""Two clean-volume controlled Lab cycles on the exact final API image."""

import json
import time
from uuid import uuid4

import yaml


def run(parent):
    a = type(parent).__new__(type(parent))
    a.project = "zhiyu-reset-" + uuid4().hex[:12]
    a.directory = parent.directory / "a15-reset"
    a.directory.mkdir(exist_ok=False)
    a.token, a.password, a.model_key = parent.token, parent.password, parent.model_key
    a.env, a.rc, a.http = parent.env.copy(), parent.rc, parent.http
    a.base = ""
    a.report = {
        "status": "RUNNING",
        "project": a.project,
        "scope": "CONTROLLED_LAB_SYNTHETIC_REPEAT",
        "checks": {},
        "commands": [],
        "cycles": [],
    }
    meta = json.loads(a.docker("image", "inspect", parent.project + "-api:latest").stdout)[0]
    a.report["image_id"] = meta["Id"]
    a.report["source_digest"] = a.rc["source_digest"]
    overlay = {
        "services": {
            name: {"image": meta["Id"]} for name in ["api", "migrate", "bootstrap", "response-target"]
        }
    }
    (a.directory / "compose.final.yml").write_text(yaml.safe_dump(overlay), encoding="utf-8")
    baseline = None
    try:
        for cycle in [1, 2]:
            a.compose("up", "-d", "--no-build", "postgres", timeout=180)
            a.wait_service("postgres")
            a.compose("run", "--rm", "--no-deps", "migrate", timeout=120)
            a.compose("run", "--rm", "--no-deps", "bootstrap", timeout=90)
            a.compose(
                "--profile", "response-test", "up", "-d", "--no-build", "api", "response-target", timeout=180
            )
            a.locate_api()
            a.await_http("/ready", 200)
            snapshot = a.snapshot()
            required = {
                "environments": 1,
                "resources": 3,
                "scopes": 1,
                "normalized_events": 0,
                "action_requests": 0,
                "capabilities": 0,
            }
            a.check(
                f"cycle_{cycle}_fresh_baseline",
                all(snapshot["counts"][k] == v for k, v in required.items()),
                snapshot,
            )
            summary = {
                "counts": {k: snapshot["counts"][k] for k in required},
                "bootstrap": snapshot["bootstrap"],
                "table_count": snapshot["table_count"],
                "migration": snapshot["migration"],
            }
            if baseline is None:
                baseline = summary
            else:
                a.check("baseline_restored_after_volume_reset", summary == baseline, summary)
            network = a.project + "_control"
            target = a.container("response-target")["NetworkSettings"]["Networks"][network]["IPAddress"]
            source = a.container("api")["NetworkSettings"]["Networks"][network]["IPAddress"]
            env = "m3-m4-pass"
            body = {"environment_id": env}
            fixture = a.fixture("seed", env, target, source)
            plan = a.call(
                "/v1/continuous-plans",
                {
                    **body,
                    "incident_id": fixture["incident_id"],
                    "expected_version": 2,
                    "scope_id": "scope-lab-web",
                },
            )
            actions = [a.call("/v1/response/worker/tick", body) for _ in plan["tasks"]]
            a.check(
                f"cycle_{cycle}_read_only_actions",
                len(actions) == 4
                and all(x["result"]["execution_outcome"] == "EXECUTION_SUCCESS" for x in actions),
                actions,
            )
            time.sleep(1.1)
            specification = a.fixture("spec", env, "pass")
            identifier = a.call("/v1/verifications", specification)["verification_spec_id"]
            for _ in range(3):
                a.call("/v1/verifications/" + identifier + "/tick", body)
            verdict = a.call("/v1/verifications/" + identifier + "/decide", body)
            a.check(f"cycle_{cycle}_independent_verification", verdict["status"] == "PASS", verdict)
            after = a.fixture("snapshot", env)
            a.check(
                f"cycle_{cycle}_audit_and_no_high_risk",
                after["audit_valid"] and after["high_risk_executions"] == 0,
                after,
            )
            a.report["cycles"].append(
                {
                    "cycle": cycle,
                    "baseline": summary,
                    "inputs": fixture,
                    "plan": plan,
                    "verification": verdict,
                    "snapshot": after,
                }
            )
            volumes = a.docker(
                "volume", "ls", "-q", "--filter", "label=com.docker.compose.project=" + a.project
            ).stdout.split()
            assert volumes
            for volume in volumes:
                info = json.loads(a.docker("volume", "inspect", volume).stdout)[0]
                assert info["Labels"]["com.docker.compose.project"] == a.project
            a.compose("--profile", "response-test", "down", "--volumes", "--remove-orphans", timeout=120)
            remaining = {
                kind: a.docker(
                    kind, "ls", "-q", "--filter", "label=com.docker.compose.project=" + a.project
                ).stdout.split()
                for kind in ["container", "volume", "network"]
            }
            a.check(
                f"cycle_{cycle}_resources_removed",
                all(not items for items in remaining.values()),
                {"removed_volumes": volumes, "remaining": remaining},
            )
        a.report["status"] = "PASS"
    except Exception:
        a.report["status"] = "FAIL"
        raise
    finally:
        a.compose("--profile", "response-test", "down", "--volumes", "--remove-orphans", timeout=120)
        a.save()
    return a.report
