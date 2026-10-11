"""Summarize recorded recovery measurements; never substitute them for Gate D soak."""

import argparse
import json
import re
from datetime import datetime

from runtime_acceptance import ROOT


def main(final=False):
    directory = ROOT / "docs/m6-runtime/gate-c-002"
    samples = [
        json.loads(line)
        for line in (directory / "model-recovery-resources.jsonl").read_text().splitlines()
        if line.strip()
    ]
    evaluation = json.loads((directory / "evaluation.json").read_text(encoding="utf-8"))
    measurements = []
    for sample in samples:
        raw = sample["cgroup_and_model_status"]
        lines = raw.splitlines()
        assert len(lines) > 3 and all(line.isdigit() for line in lines[:3])
        rss = re.search(r"^VmRSS:\s+(\d+) kB$", raw, re.MULTILINE)
        oom = re.search(r"^oom_kill (\d+)$", raw, re.MULTILINE)
        assert rss and oom
        measurements.append(
            {
                "memory_current_bytes": int(lines[0]),
                "memory_peak_bytes": int(lines[1]),
                "swap_bytes": int(lines[2]),
                "rss_bytes": int(rss[1]) * 1024,
                "oom_kill_count": int(oom[1]),
            }
        )
    checks = {
        "all_samples_running": all(s["container_state"]["Running"] for s in samples),
        "no_recorded_oom": all(
            not s["container_state"]["OOMKilled"] and m["oom_kill_count"] == 0
            for s, m in zip(samples, measurements, strict=True)
        ),
        "memory_below_4gib_limit": all(m["memory_peak_bytes"] < 4 * 1024**3 for m in measurements),
        "no_recorded_swap": all(m["swap_bytes"] == 0 for m in measurements),
        "evaluation_completed": evaluation["status"] == "COMPLETED",
    }
    if final:
        assert all(checks.values()), checks
    report = {
        "status": "PASS_RECOVERY_WINDOW" if final else "IN_PROGRESS",
        "scope": "Gate C model recovery only. Not Gate D soak or proof of long-term stability.",
        "first_observed_at": samples[0]["observed_at"],
        "last_observed_at": samples[-1]["observed_at"],
        "observation_span_seconds": (
            datetime.fromisoformat(samples[-1]["observed_at"])
            - datetime.fromisoformat(samples[0]["observed_at"])
        ).total_seconds(),
        "sample_count": len(samples),
        "sample_period_nominal_seconds": 30,
        "checks": checks,
        "first_measurement": measurements[0],
        "last_measurement": measurements[-1],
        "maximum": {key: max(m[key] for m in measurements) for key in measurements[0]},
        "units": "bytes, including process RSS; cgroup memory includes file cache; Docker stats has different accounting",
        "cache_budget_mib": 256,
        "container_memory_limit_bytes": 4 * 1024**3,
        "limitations": "Periodic observations are not continuous CPU/memory traces. No equivalent cgroup/swap history was captured before the original OOM; cache mismatch is an evidenced cause candidate, not a proof excluding other allocations.",
    }
    (directory / "model-recovery-review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true")
    main(parser.parse_args().final)
