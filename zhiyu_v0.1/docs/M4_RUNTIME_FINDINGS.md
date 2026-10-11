# v0.4 runtime/review findings

## Failed attempt e2bc74c82dc7

Real Docker build/migration/bootstrap and **239 Linux tests passed** (0 failures/skips).
M1–M3 runtime regressions passed. The first M4 cycle executed four actions and the two
verification workers collected distinct independent observations. Host /ready polling
then failed after API restart; the container's own /ready continued returning 200.

An isolated Docker reproduction demonstrated an ephemeral host-port change on restart:
`127.0.0.1:51902 → 127.0.0.1:51914`, recorded in `m4-port-restart-reproduction.json`.
M4 acceptance now discovers the published API address after every API restart.
The failed run and cleanup logs remain under `m4-runtime/zhiyu-smoke-e2bc74c82dc7/`.
This failed attempt is not counted as a complete v0.4 PASS.

## Decision freshness review

Qualified PASS/FAIL must expire no later than their supporting observations, input
evidence, sensor heartbeat/event freshness and verification window. Previously a new
result TTL could outlive an older supporting observation. Decision expiry now uses the
earliest bound; state OBSERVATION snapshots inherit their evidence validity.
INCONCLUSIVE diagnostic validity is separate and never establishes a qualified security
claim. Decision-time Scope/Profile revocation also invalidates qualification.
Dedicated tests cover expiry and Scope changes after checks.

## API/read model integration

New incident verification/timeline paths must precede the existing `{incident_id}/{kind}`
route. PostgreSQL JSON dimension grouping must reuse the same bound expression.
Both integration defects were fixed and checked through real PostgreSQL TestClient calls.
Continuous-plan replay looks up the immutable request identity before evaluating current
lifecycle state, allowing a retry after initial activation without creating another plan.

All changes preserve ai.5 contracts and historical migrations. Final runtime evidence is
reported separately once every gate and the final full run pass.

## Failed attempt fcd2a46d3524 — performance fixture

243 Linux tests passed, all four verification chains and restart/recovery checks passed.
The performance fixture used 127.0.0.1 for both the source HOST and target endpoint;
normalization could bind a Wazuh target to the source resource. TaskGraphValidator
correctly rejected `target outside scope` before dispatch. The benchmark now binds its
source to 127.0.0.2 and target to 127.0.0.1, distinct loopback identities. No authorization
or scope rule was weakened. The failed performance startup and complete preceding
functional evidence are retained in `m4-runtime/zhiyu-smoke-fcd2a46d3524/`.

## Shared Scope probe-rate guard

The first corrected-address preflight completed 100 runs in 33.382 seconds while the
fixture Scope still declared 1 request/second. Review showed independent verification
had not shared the response probe-rate budget. The preflight is retained as historical
evidence (`m4-benchmark-preflight-before-rate-guard.json`), not final acceptance.
Verification now waits at scheduling and rechecks/reserves the same rate budget at the
probe boundary. A PostgreSQL test proves no HTTP request occurs before the budget is
ready. Performance fixtures explicitly configure a 100 RPS ceiling for their isolated
loopback target and record it; ordinary closed-loop scenarios retain the 1 RPS Scope.
