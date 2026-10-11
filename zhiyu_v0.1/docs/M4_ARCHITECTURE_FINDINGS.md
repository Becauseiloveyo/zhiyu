# v0.4 compatibility findings

## AF-M4-01 — evidence qualification before frozen aggregation

Requirement: untrustworthy observations must yield INCONCLUSIVE even beside raw failure.
ai.5 `expected_verdict(FAIL, PASS, INCONCLUSIVE)` and the SQL constraint yield FAIL.
Reproduction: direct call of the frozen function with those inputs.
Resolution: retain raw assertions separately and qualify dimension conclusions before
aggregation. Unqualified dimensions are INCONCLUSIVE. No frozen contract change.

## AF-M4-02 — read-only detection lifecycle

Requirement: truthful post-action verification without artificial security state changes.
The frozen Incident machine has containment_pass/remediation_pass, no detection_pass
edge to CONTAINED or RESOLVED. Resolution: DETECTION PASS remains VERIFYING with
effectiveness and residual risk recorded. No automatic closure or frozen contract change.

## AF-M4-03 — existing response runtime admission

Requirement: actual PLANNED → EXECUTING → VERIFYING lifecycle and bounded new plans.
Reproduction: v0.3 AuthorizationService rejects a PLANNED incident with
`stale_incident_version`; v0.3 planner always emits max_replans=0.
This is an implementation milestone boundary, not a frozen-contract defect.
Minimal change: add an opt-in max_replans planner setting (default remains zero);
bind enabled cycles to their exact plan and incident semantic snapshot. Pre-dispatch
authorization admits only the exact next EXECUTING version; Gateway records the legal
transition after fresh ALLOW and durable intent in the same transaction. Existing
dispatch boundary still requires exact ActionRequest.expected_state_version.
All scopes, risk gates, leases, digests, capability health and evidence checks remain.
Unmanaged v0.3 plans retain their original admission semantics; old tests are retained.

No ai.5 architecture change required.
