# v0.3.0 inspection and implementation record

Baseline inspected: v0.2.0 ZIP SHA256 `3741139833ecdefa3ae7c4f9aab17375c52fd0b8d27c3436c2586937a8d7776f`; current source matches that archive. Existing 147 tests and 50 Docker checks remain the regression floor. ai.5 models, Schema and state machines stay frozen.

Contract mapping: deterministic response plans reuse **AIPlan** with `model_run_id=null`, zero model calls and an explicitly unproven authentication hypothesis. ContextBundle records inputs; no model is invoked. Policy decisions reuse **AuthorizationDecision**. Execution lifecycle reuses **ActionAttempt**; ActionResult is its persisted executor output metadata, never a VerificationResult. Capability definition uses **CapabilityManifest**, separate from **CapabilityHealth**. No second Event/Incident/Plan domain model is introduced.

Task states follow ai.5: QUEUED/BLOCKED/WAITING_APPROVAL/RUNNING/SUCCEEDED/FAILED/CANCELLED/TIMED_OUT. READY is a scheduler predicate; claiming a lease moves QUEUED→RUNNING. There are no invented READY/LEASED contract enums. Failed/expired work retries through the frozen transitions and a new WorkerLease generation. Depends-on edges are relational; reverse edges provide blocks. ai.5 has no optional-dependency semantic, so optional edges are not invented.

Inspection found that existing contract tables already store plans, tasks, capabilities, health, leases, requests, authorization snapshots/decisions and attempts. Add only runtime metadata, graph membership/edges and execution receipts. Existing migrations 0001–0004 and v0.2 event intelligence implementation are preserved.

Gate order is mandatory:

1. A: deterministic planner, immutable input snapshot and natural identity; relational task graph, validation, dependency readiness, lifecycle, transaction/restart tests.
2. B: managed capability registry and health; structured inputs; scope, current resource/profile/policy/evidence/sensor/budget checks; immutable authorization snapshot and explained decisions; fail-closed negatives.
3. C: PostgreSQL scheduler, worker identity/generation, bounded retry/backoff; gateway rechecks all authority before registered executor dispatch; persisted intent/receipt and explicit read-only recovery policy.
4. D: isolated Docker HTTP target; complete response chain, negative authorization cases, restart/retry and measured 100/1,000 workload. Final regression, review, report and full verified ZIP.

The first executors are bounded database reads and fixed read-only service probes. HTTP probing remains ACTIVE_CHECK / R2 under ai.5 even though it sends no state-changing method; OBSERVE_ONLY cannot authorize it. No firewall/account changes, arbitrary commands, external targets, approval-based high-risk execution, Verification or re-plan runtime are introduced. Network probes must bind current managed source/target identity and Scope network constraints; no caller-supplied URL, proxy, redirect or shell.

Performance is measured by stage, not inferred from fixture count. Execution success means a valid executor result only. Incident security disposition remains unchanged by task success.

Gate A PASS: 155 non-Compose tests, Ruff and mypy passed before Gate B implementation; see M3_GATE_A.md. Gate B PASS: full 180 tests plus final 27 focused tests including two additions; see M3_GATE_B.md. Gate C PASS: full 200 non-Compose tests; see M3_GATE_C.md. Gate D PASS: 81 Docker checks and 100/1000 measured task dispatches; see M3_GATE_D.md. Per-Gate results are recorded only after actual checks pass.
