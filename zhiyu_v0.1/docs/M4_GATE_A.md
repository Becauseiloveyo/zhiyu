# Gate A — PASS

2026-09-15: real PostgreSQL + independent local HTTP service: **12 passed, 0 failed,
0 skipped** (`m4-gate-a-tests.xml`, 19.16 s). Ruff and mypy passed for Gate A code.

Frozen VerificationSpec/VerificationCheckSpec/AssertionSpec/Evidence/Scenario/Run reused.
Three separate jobs, explicit execution versus assertion outcomes, generation leases,
bounded recovery, immutable observation payloads and fresh evidence are persisted.
Checks cover independent DB + HEAD, HTTP 500, timeout, unavailable/stale sensors,
absent evidence lookup, executor error, malformed assertion, identity mutation,
two-worker contention, expired worker fencing, durable replay and restart.

This gate alone does not establish v0.4 PASS. Sensor fixtures are synthetic.
