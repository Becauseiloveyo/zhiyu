# v0.4 Continuous Verification & Re-plan

Status: v0.4 PASS. Gates A–D, full regression and real Docker acceptance passed; see VALIDATION_REPORT_v0.4.0.md.

Gate A reuses frozen VerificationSpec, VerificationCheckSpec, AssertionSpec, Evidence,
ValidationScenario and ValidationRun. Internal metadata binds each spec to an immutable
ActionResult, plan, task, scope, policy, observation window and independent check leases.
SECURITY confirms the resource context through a new database read; BUSINESS issues a new,
bounded HEAD /health; OBSERVATION reads sensor and input evidence health independently.
No action execution receipt establishes a security assertion.

Gate B qualifies assertions before aggregating the frozen three-dimensional verdict.
Missing/stale/conflicting evidence invalidates the security and business conclusions;
their qualified status becomes INCONCLUSIVE while raw assertions remain immutable.
This respects ai.5's FAIL-first aggregation without claiming an untrustworthy failure.

Gate C uses StateEntity OBSERVATION for measured values and separate INFERENCE for
effectiveness. Read-only DETECTION PASS remains VERIFYING: ai.5 has no detection-pass
transition to CONTAINED/RESOLVED. It is not evidence of containment or remediation.
Re-plans retain immutable predecessors, bounded budgets, fingerprints and new authorization.

Gate D exercises actual PostgreSQL and Docker, independent network probes, process recovery,
fencing, duplicate callbacks, migration rollback and the full retained regression suite.
No model calls, real sensor claim, high-risk execution or production SLA.

No frozen contract changes are planned. Gate results are recorded only after execution.
