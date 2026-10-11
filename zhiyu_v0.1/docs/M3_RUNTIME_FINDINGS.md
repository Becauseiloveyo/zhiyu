# M3 Docker runtime findings

## Attempt e4a2140fcc77 — failed, retained

Linux suite completed: 200 passed, 0 failures/skips, 94.165 seconds. M1 and M2 checks reached PostgreSQL restart. Runtime then failed its 100-second health deadline. This attempt is not counted as PASS.

Evidence: `m3-runtime/zhiyu-smoke-e4a2140fcc77/251.log` records fast shutdown at 05:29:10 UTC, startup at 05:29:15, interrupted-shutdown recovery, ~90 seconds of data-directory fsync, WAL redo and final checkpoint. PostgreSQL reported ready at 05:30:52.619 UTC. Last health sample still reported starting/rejecting. No OOMKilled or container crash loop was reported. The application returned ready=503 while PostgreSQL was unavailable.

Change: explicit PostgreSQL stop_grace_period=60s; runtime checker allows up to 180 seconds for real PostgreSQL health after restart. It still requires actual healthy state and verifies persisted data digests. This does not change Event Intelligence, PostgreSQL durability settings, schema, or ai.5. Recovery time is not claimed as a production SLA. A fresh full acceptance run is required after this change.

## Attempt 94f668a2c958 — failed, retained

Full Linux suite again passed 200 tests. PostgreSQL restart/recovery and all M1/M2 checks passed after the timing fix. Response Golden Chain completed 4 actual actions, including exactly one HEAD /health. Worker crash/restart recovered generation 2; old worker request was rejected.

The next acceptance snapshot command failed with UndefinedColumn: authorization_decisions.environment_id does not exist (`143.log`). This was a defect in the new read-only acceptance query, not the frozen Contract or execution path. Fix: resolve AuthorizationDecision environment through its ActionRequest foreign key; WorkerLease similarly resolves through Task. No domain table was altered. A local PostgreSQL snapshot preflight and a fresh full Docker run are required before declaring PASS.

## Final attempt zhiyu-smoke-c85b15ffaa87 — PASS

All 81 runtime checks passed in a fresh full run, with 200 Linux tests and the host Compose test passing. Corrected environment snapshot query, actual restart data hashes, 8 negative cases and 100/1000 measured task workloads all passed. See [final report](VALIDATION_REPORT_v0.3.0.md).

## Profile cleanup correction — revalidated PASS

A final docker ps check found the response-test profile target still running after default Compose down. Corrected cleanup explicitly includes response-test and checks project-labeled containers are absent. The corrected function was executed against only the recorded c85b15ffaa87 and 94f668a2c958 projects; remaining targets and networks were removed, database volumes retained. Commands and project_containers_removed=PASS were appended to their original reports. The failed attempt remains FAIL; final acceptance now has 80 functional/performance checks plus 1 actual cleanup check, all PASS. Functional source and measurements are unchanged.
