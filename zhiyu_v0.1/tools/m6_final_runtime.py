"""Fresh final RC runtime, representative adversarial cases and final full regression."""

import hashlib
import json
import xml.etree.ElementTree as ET

import yaml
from m5_runtime_acceptance import M5Acceptance
from runtime_acceptance import ROOT, main


class M6Acceptance(M5Acceptance):
    evaluation_indices = [15, 18]

    def valid_decision_expected(self, decision):
        if decision["status"] != "DETERMINISTIC_FALLBACK":
            return "AI_ASSISTED"
        snapshot = self.ai_fixture("snapshot", "m3-m5-valid")
        runs = snapshot["rows"]["model_runs"]
        proposals = snapshot["rows"]["ai_plan_proposals"]
        self.check(
            "m6_real_model_stale_context_safe_fallback",
            len(runs) == 2
            and all(r["provider"] == "local" and r["input_tokens"] > 0 for r in runs)
            and len(proposals) == 1
            and proposals[0]["status"] == "FALLBACK"
            and proposals[0]["validation"]["reasons"] == ["STALE_CONTEXT"]
            and proposals[0]["validation"]["authorization"] == "NOT_GRANTED"
            and snapshot["high_risk_executions"] == 0
            and snapshot["audit_valid"],
            {"reason": "STALE_CONTEXT", "snapshot": snapshot},
        )
        return "DETERMINISTIC_FALLBACK"

    def __init__(self, directory):
        assert (
            json.loads((ROOT / "docs/m6-runtime/gate-d-acceptance.json").read_text())["status"]
            == "PASS_CONTROLLED_LAB"
        )
        self.rc = json.loads((ROOT / "RC_STATE_v0.6.0.json").read_text())
        super().__init__(directory)
        self.report.update(
            rc_revision=self.rc["revision"],
            source_digest=self.rc["source_digest"],
            scope="CONTROLLED_LAB_FINAL_RC",
        )
        tokens = json.loads(self.env["ZHIYU_SERVICE_TOKENS"])
        for principal in tokens.values():
            principal["environment_ids"] += ["m3-m6-lab-a", "m3-m6-lab-b"]
        self.env["ZHIYU_SERVICE_TOKENS"] = json.dumps(tokens)
        overlay = {
            "services": {
                "api": {
                    "volumes": [{"type": "bind", "source": str(self.directory), "target": "/safety-output"}]
                }
            }
        }
        (self.directory / "compose.final.yml").write_text(yaml.safe_dump(overlay), encoding="utf-8")
        # Recovery state is private and is never included in the project or release archive.
        (ROOT.parent / ".work/m6-final-state.json").write_text(
            json.dumps(
                {
                    "project": self.project,
                    "directory": str(self.directory),
                    "token": self.token,
                    "password": self.password,
                    "env": {
                        k: v
                        for k, v in self.env.items()
                        if k.startswith("ZHIYU_") or k == "POSTGRES_PASSWORD"
                    },
                }
            ),
            encoding="utf-8",
        )

    def compose(self, *args, **kwargs):
        return self.docker(
            "compose",
            "--project-name",
            self.project,
            "-f",
            str(ROOT / "docker-compose.yml"),
            "-f",
            str(ROOT / "docker-compose.ai.yml"),
            "-f",
            str(self.directory / "compose.final.yml"),
            *args,
            **kwargs,
        )

    def correspondence(self):
        script = "import pathlib,json,hashlib,zhiyu; p=pathlib.Path(zhiyu.__file__).parent; print(json.dumps({str(x.relative_to(p.parent)).replace(chr(92),'/'):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(p.rglob('*.py'))}))"
        expected = {
            p.relative_to(ROOT / "src").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "src").rglob("*.py"))
        }
        images = {}
        for role in ["api", "tests"]:
            tag = self.project + "-" + role + ":latest"
            meta = json.loads(self.docker("image", "inspect", tag).stdout)[0]
            actual = json.loads(
                self.docker("run", "--rm", "--entrypoint", "python", tag, "-c", script).stdout
            )
            self.check("m6_" + role + "_source_bytes", actual == expected)
            lock_script = "import pathlib,hashlib,json; print(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path('/app').glob('*.lock')}))"
            locks = json.loads(
                self.docker("run", "--rm", "--entrypoint", "python", meta["Id"], "-c", lock_script).stdout
            )
            expected_locks = {
                name: digest
                for name, digest in self.rc["dependency_lock_digest"].items()
                if role == "tests" or name in {"requirements-runtime.lock", "uv.lock"}
            }
            self.check("m6_" + role + "_dependency_lock_bytes", locks == expected_locks)
            images[role] = {
                "tag": tag,
                "id": meta["Id"],
                "repo_digests": meta["RepoDigests"],
                "created": meta["Created"],
                "source_digest": self.rc["source_digest"],
                "source_sha256": actual,
                "dependency_lock_digest": locks,
                "registry_digest_note": "Locally built images may have no RepoDigest; image ID is retained.",
            }
        (self.directory / "image-source-correspondence.json").write_text(
            json.dumps(
                {
                    "status": "PASS_RAW_BYTES",
                    "workspace_source_digest": self.rc["source_digest"],
                    "images": images,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def run(self, *, no_cache):
        self.check(
            "m6_rc_controlled_files_match",
            all(
                (ROOT / name).exists() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
                for name, digest in self.rc["controlled_files"].items()
            ),
        )
        super().run(no_cache=no_cache)
        self.correspondence()
        from m6_final_sensors import run as confirm_sensors

        sensors = confirm_sensors(self)
        self.check("m6_fresh_real_sensors", sensors["status"] == "PASS", sensors)
        self.compose(
            "exec",
            "-T",
            "api",
            "python",
            "tools/response_benchmark.py",
            "--sizes",
            "100",
            "1000",
            "--output",
            "/safety-output/remediation-task-benchmark.json",
            timeout=900,
        )
        benchmark = json.loads((self.directory / "remediation-task-benchmark.json").read_text())
        self.check(
            "m6_affected_gate_d_task_queue_benchmark",
            benchmark["source_digest"] == self.rc["source_digest"]
            and [r["tasks_executed"] for r in benchmark["results"]] == [100, 1000]
            and all(r["logical_actions"] == r["tasks_executed"] for r in benchmark["results"]),
            {
                "results": [
                    {
                        k: r[k]
                        for k in (
                            "environment_id",
                            "tasks_executed",
                            "logical_actions",
                            "elapsed_seconds",
                            "unexecuted_tail_tasks",
                        )
                    }
                    for r in benchmark["results"]
                ],
                "scope": "Affected default task/queue path; opt-in reservations tested separately with saturation. No production SLA.",
            },
        )
        self.compose(
            "exec",
            "-T",
            "api",
            "python",
            "tools/m6_safety_boundaries.py",
            self.target_ip,
            self.source_ip,
            timeout=600,
        )
        boundary = json.loads((self.directory / "boundary-index.json").read_text())
        self.check(
            "m6_critical_scripted_adversarial",
            boundary["status"] == "PASS" and boundary["cases"] == 26,
            boundary,
        )
        self.compose("exec", "-T", "api", "python", "tools/m6_final_migration.py", timeout=180)
        self.check(
            "m6_final_migration_roundtrip",
            json.loads((self.directory / "final-migration.json").read_text())["status"] == "PASS",
        )
        for script, evidence in [
            ("m6_final_binding.py", "a02-binding-result.json"),
            ("m6_final_validation_registry.py", "a12-registry-result.json"),
        ]:
            self.compose("exec", "-T", "api", "python", "tools/" + script, timeout=180)
            result = json.loads((self.directory / evidence).read_text())
            self.check("m6_" + evidence.removesuffix(".json"), result["status"] == "PASS", result)
        from m6_final_reset import run as reset_lab

        reset = reset_lab(self)
        self.check("m6_a15_repeatable_lab_reset", reset["status"] == "PASS")
        database = json.loads(
            self.compose(
                "exec",
                "-T",
                "api",
                "python",
                "tools/m6_database_snapshot.py",
                "--statement-timeout-ms",
                "180000",
                timeout=240,
            ).stdout
        )
        (self.directory / "final-database-snapshot.json").write_text(
            json.dumps(database, indent=2), encoding="utf-8"
        )
        self.check(
            "m6_final_audit_and_no_high_risk",
            all(database["audit_chains"].values()) and database["high_risk_automatic_actions"] == 0,
        )
        # The complete suite runs again AFTER the final acceptance scenarios, on unchanged RC bytes.
        name = self.project + "-final-tests"
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
            "-m",
            "pytest",
            "-q",
            "-m",
            "not compose",
            "--junitxml=/tmp/final-tests.xml",
            timeout=900,
        )
        self.docker("cp", name + ":/tmp/final-tests.xml", str(self.directory / "final-test-results.xml"))
        self.docker("rm", name)
        suite = next(ET.parse(self.directory / "final-test-results.xml").getroot().iter("testsuite"))
        self.check(
            "m6_final_full_regression",
            int(suite.attrib["tests"]) == self.rc["test_inventory_count"] - 1
            and all(int(suite.attrib[k]) == 0 for k in ["failures", "errors", "skipped"]),
            suite.attrib,
        )
        self.report["final_pytest"] = suite.attrib
        self.check(
            "m6_rc_unchanged_after_tests",
            all(
                hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
                for name, digest in self.rc["controlled_files"].items()
            ),
        )
        self.save()


if __name__ == "__main__":
    raise SystemExit(main(M6Acceptance))
