"""Backward-compatible entry point for the complete Docker runtime acceptance."""

from m5_runtime_acceptance import M5Acceptance
from runtime_acceptance import main

if __name__ == "__main__":
    import os
    import sys

    if os.environ.get("ZHIYU_M6_FINAL") == "1":
        from m6_final_runtime import M6Acceptance
        from runtime_acceptance import ROOT

        sys.argv.extend(["--report-dir", str(ROOT / "docs/m6-runtime/gate-e-final")])
        raise SystemExit(main(M6Acceptance))
    raise SystemExit(main(M5Acceptance))
