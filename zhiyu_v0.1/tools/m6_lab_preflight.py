"""Fresh disposable development evidence; never a frozen RC or release PASS."""

import hashlib
import json

from m6_final_sensors import run
from runtime_acceptance import ROOT, Acceptance


def main():
    acceptance = Acceptance(ROOT / "docs/m6-runtime/remediation-development")
    acceptance.rc = {
        "source_digest": hashlib.sha256(
            b"".join(
                p.relative_to(ROOT / "src").as_posix().encode() + p.read_bytes()
                for p in sorted((ROOT / "src").rglob("*.py"))
            )
        ).hexdigest()
    }
    acceptance.report["scope"] = "DEVELOPMENT_NOT_FINAL_RC"
    acceptance.save()
    print(json.dumps({"project": acceptance.project, "directory": str(acceptance.directory)}), flush=True)
    try:
        for stage, role in (("tests", "tests"), ("runtime", "api")):
            acceptance.docker(
                "build",
                "--target",
                stage,
                "-t",
                acceptance.project + "-" + role + ":latest",
                ".",
                timeout=600,
            )
        acceptance.report["sensors"] = run(acceptance)
        acceptance.report["status"] = "PASS_DEVELOPMENT_ONLY"
    except Exception as error:
        acceptance.report.update(status="FAIL", error=acceptance.sanitize(str(error)))
        raise
    finally:
        acceptance.save()


if __name__ == "__main__":
    main()
