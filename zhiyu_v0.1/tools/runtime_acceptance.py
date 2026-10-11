"""Linux Docker acceptance in a fresh project; its database volume is retained."""

import argparse
import copy
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = """
import hashlib, importlib, json, os, pkgutil, platform
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session
import zhiyu
from zhiyu.db.session import get_engine
from zhiyu.db.mapping import contract_from
from zhiyu.db.models import EnvironmentRow, ResourceRow, ScopeRow
from zhiyu.domain.contracts import EnvironmentProfile, ResourceRef, ScopeDefinition
from zhiyu.repositories.audit import AuditRepository
engine=get_engine()
tables=('environments','resources','scopes','normalized_events','event_receipts','audit_entries','outbox','capabilities','action_requests')
with engine.connect() as c:
    rows={t:c.scalars(text('SELECT row_to_json(r) FROM '+t+' r')).all() for t in tables}
    inspector=inspect(c)
    names=inspector.get_table_names()
    result={'counts':{t:len(r) for t,r in rows.items()},
        'state_hash':hashlib.sha256(json.dumps({t:sorted(r,key=lambda x:json.dumps(x,sort_keys=True)) for t,r in rows.items()},sort_keys=True).encode()).hexdigest(),
        'events':rows['normalized_events'],'outbox':rows['outbox'],
        'postgres':c.scalar(text('SHOW server_version')),'db_timezone':c.scalar(text('SHOW timezone')),
        'migration':c.scalars(text('SELECT version_num FROM alembic_version')).all(),'table_count':len(names)}
    for key in ('foreign_keys','unique_constraints','check_constraints','indexes'):
        result[key]=sum(len(getattr(inspector,'get_'+key)(t)) for t in names)
    result['transaction_ids']={t:c.scalars(text('SELECT xmin::text FROM '+t)).all() for t in ('normalized_events','event_receipts','outbox')}
    result['transaction_ids']['audit_entries']=c.scalars(text("SELECT xmin::text FROM audit_entries WHERE operation='INGEST'")).all()
with Session(engine) as db:
    result['bootstrap']={key:[contract_from(r,contract).model_dump(mode='json') for r in db.scalars(select(row))] for key,row,contract in [('environment',EnvironmentRow,EnvironmentProfile),('resources',ResourceRow,ResourceRef),('scopes',ScopeRow,ScopeDefinition)]}
    result['audit_chain_valid']=AuditRepository(db).verify_chain('lab-zhiyu-01')
modules=list(pkgutil.walk_packages(zhiyu.__path__,zhiyu.__name__+'.'))
for module in modules: importlib.import_module(module.name)
result.update(python=platform.python_version(),system=platform.system(),uid=os.getuid(),imported_modules=len(modules),imported_module_names=sorted(m.name for m in modules),env_file_present=os.path.exists('/app/.env'))
print(json.dumps(result,sort_keys=True))
"""


class RuntimeFailure(RuntimeError):
    pass


class Acceptance:
    cleanup_profiles: tuple[str, ...] = ()

    def __init__(self, report_dir: Path) -> None:
        self.project = "zhiyu-smoke-" + uuid4().hex[:12]
        self.directory = report_dir / self.project
        self.directory.mkdir(parents=True, exist_ok=False)
        self.token, self.password = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        self.env = os.environ.copy()
        self.env.update(
            ZHIYU_API_PORT="0",
            POSTGRES_PASSWORD=self.password,
            COMPOSE_ANSI="never",
            BUILDKIT_PROGRESS="plain",
            ZHIYU_SERVICE_TOKENS=json.dumps(
                {
                    hashlib.sha256(self.token.encode()).hexdigest(): {
                        "principal_id": "compose-smoke",
                        "environment_ids": ["lab-zhiyu-01"],
                        "collector_ids": ["sensor-suricata", "sensor-wazuh"],
                        "source_types": ["suricata", "wazuh_forwarded_suricata"],
                        "permissions": ["events:write", "incidents:read"],
                    }
                }
            ),
        )
        self.report: dict[str, Any] = {
            "status": "RUNNING",
            "project": self.project,
            "started_at": datetime.now(UTC).isoformat(),
            "checks": {},
            "commands": [],
            "real_sensor_runtime": "NOT_RUN",
            "platform_acceptance_A01_A15": "NOT_RUN",
        }
        self.base = ""
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def sanitize(self, value: str) -> str:
        for secret in (self.password, self.token, self.env["ZHIYU_SERVICE_TOKENS"]):
            value = value.replace(secret, "<redacted>")
        return value

    def save(self) -> None:
        (self.directory / "result.json").write_text(
            self.sanitize(json.dumps(self.report, ensure_ascii=False, indent=2)), encoding="utf-8"
        )

    def check(self, name: str, condition: bool, detail: Any = None) -> None:
        self.report["checks"][name] = {"status": "PASS" if condition else "FAIL", "detail": detail}
        self.save()
        print(f"{'PASS' if condition else 'FAIL'}: {name}", flush=True)
        if not condition:
            raise RuntimeFailure(name)

    def docker(
        self, *args: str, expected: int | None = 0, timeout: int = 120
    ) -> subprocess.CompletedProcess[str]:
        index = len(self.report["commands"]) + 1
        started = time.monotonic()
        result = subprocess.run(
            ["docker", *args],
            cwd=ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        name = f"{index:03d}.log"
        (self.directory / name).write_text(self.sanitize(result.stdout + result.stderr), encoding="utf-8")
        self.report["commands"].append(
            {
                "args": ["<database snapshot code>" if a == SNAPSHOT else a for a in args],
                "exit_code": result.returncode,
                "seconds": round(time.monotonic() - started, 3),
                "log": name,
            }
        )
        self.save()
        if expected is not None and result.returncode != expected:
            raise RuntimeFailure(f"docker command {index} exited {result.returncode}; see {name}")
        return result

    def compose(self, *args: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return self.docker(
            "compose", "--project-name", self.project, "-f", str(ROOT / "docker-compose.yml"), *args, **kwargs
        )

    def cleanup(self) -> None:
        profiles = [part for profile in self.cleanup_profiles for part in ("--profile", profile)]
        self.compose(*profiles, "logs", "--no-color", "--tail=200", expected=None)
        self.compose(*profiles, "down", "--remove-orphans", timeout=120)
        remaining = self.docker(
            "ps", "--all", "--quiet", "--filter", "label=com.docker.compose.project=" + self.project
        )
        self.check(
            "project_containers_removed",
            not remaining.stdout.strip(),
            {"remaining_containers": remaining.stdout.split(), "volumes": "retained"},
        )
        self.report["containers_after_test"] = "stopped_removed_volume_retained"

    def container(self, service: str) -> dict[str, Any]:
        cid = self.compose("ps", "--all", "--quiet", service).stdout.strip()
        if not cid or "\n" in cid:
            raise RuntimeFailure(f"expected exactly one {service} container")
        return json.loads(self.docker("inspect", cid).stdout)[0]

    def wait_service(self, service: str, *, job: bool = False) -> dict[str, Any]:
        # Real WSL2 recovery after schema-heavy tests can spend ~100s fsyncing WAL/data.
        # Keep checking actual health; this is an acceptance deadline, not a recovery SLA.
        deadline = time.monotonic() + (180 if service == "postgres" else 100)
        while time.monotonic() < deadline:
            container = self.container(service)
            state = container["State"]
            if job and state["Status"] == "exited":
                self.check(service + "_exit", state["ExitCode"] == 0, state["ExitCode"])
                return container
            if not job and state.get("Health", {}).get("Status") == "healthy":
                return container
            if state["Status"] == "exited":
                raise RuntimeFailure(service + " exited before healthy")
            time.sleep(1)
        raise RuntimeFailure(service + " did not become healthy/complete")

    def locate_api(self) -> None:
        address = self.compose("port", "api", "8000").stdout.strip()
        self.check("loopback_api_port", address.startswith("127.0.0.1:"), address)
        self.base = "http://" + address
        self.report.setdefault("api_endpoints", []).append(
            {"observed_at": datetime.now(UTC).isoformat(), "url": self.base}
        )
        self.save()

    def fetch(self, path: str, event: dict[str, Any] | None = None) -> tuple[int, Any]:
        request = urllib.request.Request(
            self.base + path,
            data=None if event is None else json.dumps({"events": [event]}).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"},
        )
        try:
            with self.http.open(request, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def await_http(self, path: str, status: int) -> None:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                if self.fetch(path)[0] == status:
                    return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                pass
            time.sleep(1)
        raise RuntimeFailure(f"{path} did not return {status}")

    def snapshot(self) -> dict[str, Any]:
        return json.loads(self.compose("exec", "-T", "api", "python", "-c", SNAPSHOT).stdout)

    def run(self, *, no_cache: bool) -> None:
        self.report["versions"] = json.loads(self.docker("version", "--format", "{{json .}}").stdout)
        info = json.loads(self.docker("info", "--format", "{{json .}}").stdout)
        self.check(
            "linux_engine",
            info["OSType"] == "linux",
            {k: info[k] for k in ("OSType", "KernelVersion", "ServerVersion", "OperatingSystem")},
        )
        self.docker("--version")
        self.docker("compose", "version")
        self.docker("context", "ls")
        hello = self.docker("run", "--rm", "hello-world", timeout=180)
        self.check("hello_world", "Hello from Docker!" in hello.stdout)
        self.compose("config")
        self.check("compose_config", True)
        print("BUILD: runtime and tests images", flush=True)
        self.compose("--profile", "test", "build", *(["--no-cache"] if no_cache else []), timeout=900)
        self.check("image_build", True, {"no_cache": no_cache})
        # Fresh random project only. Never downgrade an existing development database.
        self.compose("up", "--detach", "postgres", "api", timeout=240)
        pg = self.wait_service("postgres")
        self.check("postgres_healthy", True)
        self.locate_api()
        self.await_http("/health", 200)
        self.await_http("/ready", 503)
        self.check("unmigrated_not_ready", True)
        failed = self.compose(
            "run",
            "--rm",
            "--no-deps",
            "migrate",
            "python",
            "-m",
            "alembic",
            "upgrade",
            "missing_test_revision",
            expected=None,
        )
        self.check("migration_failure_not_ready", failed.returncode != 0 and self.fetch("/ready")[0] == 503)
        failed = self.compose("run", "--rm", "--no-deps", "bootstrap", expected=None)
        self.check(
            "bootstrap_failure_observable", failed.returncode != 0 and '"status": "error"' in failed.stdout
        )
        self.compose("up", "--detach", "migrate")
        self.wait_service("migrate", job=True)
        self.await_http("/ready", 200)
        self.compose("run", "--rm", "--no-deps", "migrate", "python", "-m", "alembic", "downgrade", "base")
        self.check("downgraded_not_ready", self.fetch("/ready")[0] == 503)
        self.compose("run", "--rm", "--no-deps", "migrate")
        self.compose("run", "--rm", "--no-deps", "migrate", "python", "-m", "alembic", "check")
        self.check("migration_roundtrip_and_drift", True)
        self.compose("up", "--detach", "bootstrap")
        self.wait_service("bootstrap", job=True)
        self.wait_service("api")
        self.check("compose_up", True)
        initial = self.snapshot()
        self.report["bootstrap"] = initial["bootstrap"]
        self.report["database_structure"] = {
            k: initial[k]
            for k in (
                "table_count",
                "foreign_keys",
                "unique_constraints",
                "check_constraints",
                "indexes",
                "migration",
            )
        }
        self.report["runtime"] = {
            k: initial[k] for k in ("python", "postgres", "db_timezone", "uid", "system", "imported_modules")
        }
        environment = initial["bootstrap"]["environment"][0]
        self.check(
            "bootstrap_contract_and_passive_defaults",
            initial["counts"]["environments"] == 1
            and initial["counts"]["resources"] == 3
            and initial["counts"]["scopes"] == 1
            and initial["counts"]["capabilities"] == initial["counts"]["action_requests"] == 0
            and environment["autonomy_mode"] == "OBSERVE_ONLY"
            and environment["active_validation"] == "DISABLED"
            and environment["max_auto_risk"] == "R0",
        )
        self.check(
            "schema_constraints_present",
            initial["table_count"] == 72
            and all(
                initial[k] > 0 for k in ("foreign_keys", "unique_constraints", "check_constraints", "indexes")
            ),
        )
        repeat = self.compose("run", "--rm", "--no-deps", "bootstrap")
        self.check(
            "bootstrap_idempotent",
            json.loads(repeat.stdout) == {"environments": 0, "resources": 0, "scopes": 0}
            and initial["state_hash"] == self.snapshot()["state_hash"],
        )
        expected_modules = sorted(
            ".".join(
                p.relative_to(ROOT / "src").parts[:-1]
                if p.name == "__init__.py"
                else p.relative_to(ROOT / "src").with_suffix("").parts
            )
            for p in (ROOT / "src/zhiyu").rglob("*.py")
            if p != ROOT / "src/zhiyu/__init__.py"
        )
        self.check(
            "linux_nonroot_utc_import",
            initial["system"] == "Linux"
            and initial["uid"] == 10001
            and initial["db_timezone"] == "UTC"
            and initial["imported_modules"] == len(expected_modules)
            and initial["imported_module_names"] == expected_modules
            and not initial["env_file_present"],
            {
                "expected_modules": expected_modules,
                "actual_modules": initial["imported_module_names"],
                "system": initial["system"],
                "uid": initial["uid"],
                "db_timezone": initial["db_timezone"],
            },
        )
        api = self.container("api")
        image = json.loads(self.docker("image", "inspect", api["Image"]).stdout)[0]
        history = self.docker("history", "--no-trunc", api["Image"]).stdout
        self.check(
            "image_secret_boundary",
            self.password not in json.dumps(image) + history
            and self.token not in json.dumps(image) + history
            and image["Config"]["User"] == "zhiyu",
        )
        self.check(
            "managed_volume_and_ports",
            all(not p for p in pg["NetworkSettings"]["Ports"].values())
            and any(
                m["Type"] == "volume" and m["Destination"] == "/var/lib/postgresql/data" for m in pg["Mounts"]
            )
            and not api["HostConfig"]["Privileged"],
        )
        health = self.fetch("/health")
        self.check(
            "normal_health_ready",
            health[0] == self.fetch("/ready")[0] == 200
            and health[1]["ai_enabled"] is False
            and health[1]["active_security_actions_enabled"] is False,
        )
        objects = json.loads((ROOT / "tests/fixtures/ai5/golden_chain.json").read_text(encoding="utf-8"))[
            "objects"
        ]
        event = next(o for o in objects if o.get("event_id") == "evt-net")
        event["validation_run_id"] = None
        first = self.fetch("/v1/events/batches", event)
        after_first = self.snapshot()
        txids = [i for values in after_first["transaction_ids"].values() for i in values]
        self.check(
            "event_A_atomic_ingest",
            first[0] == 202
            and first[1]["accepted"] == 1
            and len(txids) == 4
            and len(set(txids)) == 1
            and after_first["counts"]["audit_entries"] == 6,
            first,
        )
        duplicate = self.fetch("/v1/events/batches", event)
        after_duplicate = self.snapshot()
        self.check(
            "event_B_duplicate",
            duplicate[0] == 202
            and duplicate[1]["duplicates"] == 1
            and after_duplicate["counts"]["normalized_events"] == after_duplicate["counts"]["outbox"] == 1
            and after_duplicate["counts"]["event_receipts"] == 2,
            duplicate,
        )
        changed = copy.deepcopy(event)
        changed["severity_signal"] = 8 if event["severity_signal"] != 8 else 7
        conflict = self.fetch("/v1/events/batches", changed)
        self.check(
            "event_C_conflict_no_overwrite",
            conflict[0] == 409 and after_duplicate["state_hash"] == self.snapshot()["state_hash"],
            conflict,
        )
        forwarded = copy.deepcopy(event)
        forwarded.update(
            event_id="evt-docker-forwarded",
            collector_id="sensor-wazuh",
            source_type="wazuh_forwarded_suricata",
        )
        forward = self.fetch("/v1/events/batches", forwarded)
        after_forward = self.snapshot()
        self.check(
            "event_D_same_fingerprint_provenance_retained",
            forward[0] == 202
            and forward[1]["accepted"] == 1
            and len(after_forward["events"]) == 2
            and len({e["fingerprint"] for e in after_forward["events"]}) == 1
            and len({e["collector_id"] for e in after_forward["events"]}) == 2,
            forward,
        )
        for field in ("environment_id", "collector_id", "source_type"):
            invalid = copy.deepcopy(event)
            invalid[field] = "outside-authorized-identity"
            response = self.fetch("/v1/events/batches", invalid)
            self.check(
                "event_E_reject_" + field,
                response[0] == 403 and after_forward["state_hash"] == self.snapshot()["state_hash"],
                response,
            )
        self.check(
            "audit_outbox", after_forward["audit_chain_valid"] and after_forward["counts"]["outbox"] == 2
        )
        self.compose("stop", "postgres")
        self.check(
            "db_down_health_ready_write",
            self.fetch("/health")[0] == 200
            and self.fetch("/ready")[0] == self.fetch("/v1/events/batches", event)[0] == 503,
        )
        self.compose("start", "postgres")
        self.wait_service("postgres")
        self.await_http("/ready", 200)
        recovered = self.container("api")
        self.check(
            "db_recovery_without_api_restart",
            recovered["Id"] == api["Id"]
            and recovered["State"]["StartedAt"] == api["State"]["StartedAt"]
            and self.fetch("/health")[0] == 200,
        )
        self.check("recovery_replay_duplicate", self.fetch("/v1/events/batches", event)[1]["duplicates"] == 1)
        saved = self.snapshot()
        self.compose("restart", "api")
        self.wait_service("api")
        # A published port of 0 can be reallocated even when the container ID survives.
        self.locate_api()
        self.await_http("/ready", 200)
        self.check("api_restart_persistence", self.snapshot()["state_hash"] == saved["state_hash"])
        volume_name = next(m["Name"] for m in pg["Mounts"] if m["Type"] == "volume")
        volume_before = json.loads(self.docker("volume", "inspect", volume_name).stdout)[0]
        self.compose("down")  # Never pass -v: persistence is part of acceptance.
        self.compose("up", "--detach", timeout=180)
        self.wait_service("postgres")
        self.wait_service("migrate", job=True)
        self.wait_service("bootstrap", job=True)
        self.wait_service("api")
        self.locate_api()
        self.await_http("/ready", 200)
        volume_after = json.loads(self.docker("volume", "inspect", volume_name).stdout)[0]
        self.check(
            "compose_down_up_volume_persistence",
            volume_before["CreatedAt"] == volume_after["CreatedAt"]
            and self.snapshot()["state_hash"] == saved["state_hash"],
        )
        print("TEST: full non-Compose suite inside Linux container", flush=True)
        test_container = self.project + "-tests-report"
        self.compose(
            "--profile",
            "test",
            "run",
            "--no-deps",
            "-T",
            "--name",
            test_container,
            "tests",
            "python",
            "-m",
            "pytest",
            "-q",
            "-m",
            "not compose",
            "--junitxml=/tmp/test-results.xml",
            timeout=600,
        )
        self.docker("cp", test_container + ":/tmp/test-results.xml", str(self.directory / "test-results.xml"))
        self.docker("rm", test_container)
        suite = next(ET.parse(self.directory / "test-results.xml").getroot().iter("testsuite"))
        self.report["pytest"] = suite.attrib
        self.check(
            "postgres_test_suite",
            int(suite.attrib["tests"]) >= 46
            and int(suite.attrib["skipped"])
            == int(suite.attrib["failures"])
            == int(suite.attrib["errors"])
            == 0,
            suite.attrib,
        )
        final = {s: self.wait_service(s) for s in ("api", "postgres")}
        self.check(
            "no_crash_loop",
            all(c["RestartCount"] == 0 and c["State"]["Status"] == "running" for c in final.values()),
        )
        self.report["final_counts"] = self.snapshot()["counts"]
        self.report.update(volume=volume_name, api_url=self.base)
        self.compose("ps", "--all")
        self.compose("logs", "--no-color", "--tail=200")
        self.check(
            "ai5_unchanged",
            (ROOT / "baseline/ai5/models.py").read_bytes()
            == (ROOT / "src/zhiyu/domain/contracts.py").read_bytes(),
        )


def main(acceptance_type: type[Acceptance] = Acceptance) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=ROOT
        / (
            "docs/docker-runtime"
            if acceptance_type is Acceptance
            else "docs/m5-runtime"
            if acceptance_type.__name__ == "M5Acceptance"
            else "docs/m4-runtime"
            if acceptance_type.__name__ == "M4Acceptance"
            else "docs/m3-runtime"
            if acceptance_type.__name__ == "M3Acceptance"
            else "docs/m2-runtime"
        ),
    )
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--benchmark", action="store_true", default=os.environ.get("ZHIYU_BENCHMARK") == "1")
    args = parser.parse_args()
    if not shutil.which("docker"):
        print("NOT_RUN: Docker CLI/Engine unavailable")
        return 2
    acceptance = acceptance_type(args.report_dir.resolve())
    acceptance.benchmark = args.benchmark
    try:
        acceptance.run(no_cache=args.no_cache)
        acceptance.report["status"] = "PASS"
        code = 0
    except (
        subprocess.SubprocessError,
        OSError,
        ValueError,
        KeyError,
        AssertionError,
        RuntimeFailure,
    ) as error:
        acceptance.report["status"] = "FAIL"
        acceptance.report["failure"] = acceptance.sanitize(str(error))
        print("FAIL:", acceptance.report["failure"], flush=True)
        code = 1
    finally:
        try:
            acceptance.cleanup()
        except (subprocess.SubprocessError, OSError, RuntimeFailure) as error:
            acceptance.report["cleanup_error"] = acceptance.sanitize(str(error))
            acceptance.report["status"] = "FAIL"
            code = 1
        acceptance.report["finished_at"] = datetime.now(UTC).isoformat()
        acceptance.save()
    print("REPORT:", acceptance.directory / "result.json", flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
