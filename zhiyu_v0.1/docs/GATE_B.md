# Gate B — PASS

Passed before Gate C implementation, 2026-09-14: **122 passed, 0 failed, 0 skipped**, Compose test deselected here (passed at Gate A, will be rerun for final acceptance). [JUnit](gate-b-tests.xml). Ruff and mypy passed (50 modules). The same two upstream deprecation warning classes remain.

Positive cross-source authentication joins; different users, targets, source IPs, environments, outcomes, windows and validation contexts do not join. Same fingerprints with independent provenance retain every event. Two concurrent workers create one logical group/decision; process recreation and engine disposal preserve checkpoints. Failure before outbox commit rolls back all correlation state and retries safely. The database enforces same-environment FKs and unique membership.

Migration `0003_correlation` adds group state, relational event memberships, relational decision inputs/exclusions and measured worker runs. Existing frozen EventGroup/CorrelationDecision objects are persisted. Their JSON member/input arrays are contract snapshots; evidence lookup and pending-event selection use relations.

Windows: fixed UTC auth=300s, network alert=60s, web=120s, other=60s; grace=120s. Reception more than 24h after source time is EXPIRED; >300s before source time is FUTURE; reception after window end+grace is LATE. These records become isolated, non-promotable groups. Timely out-of-order records join OPEN groups. A CLOSED group is never changed. Closing waits until the environment backlog is drained, so processing a previously received batch in chunks cannot split its group. Configuration and hash are persisted.

Exclusion explanations contain a bounded earliest-100 same-window candidate sample; this is explicitly not an exhaustive negative join across history. Confidence is identity-dimension coverage, not probability. Compression is members/groups, not deletion.

Additional integration fixes: resource locators use ai.5 `address`; network endpoint binding requires address, port and protocol. Invalid Unicode and mapped NUL are per-record errors with raw bytes retained. Regression includes both fixes.
