# v0.2.0 engineering plan (ai.5 remains frozen)

Scope: read / normalize / correlate / incident. Each Gate is tested before the next is implemented. The original M1.1 packages and migration remain historical baselines.

## Gate A

Explicit Suricata and Wazuh adapter registry, pure transformations into the existing NormalizedEvent. Authenticated transport supplies environment, collector and data origin; vendor validation labels are never authorization. Raw UTF-8 input is content-addressed within environment/collector/source and preserved in PostgreSQL. Every delivery has a result, including malformed records and retransmits. Per-record savepoints isolate mapping/identity conflicts; infrastructure failure rolls back the transaction.

Missing/naive/invalid timestamps are rejected, not replaced by ingest time. Future (>5 minutes) and delayed (>24 hours) source times are SKEWED; the source time is retained. Severity is a versioned lookup; source severity and a small allowlist of protocol/port/rule facts are OTHER observables. All other vendor fields remain raw. Flow ID alone is not an event identity. Suricata fallback identity hashes the whole parsed record; collectors can supply a stable capture cursor to distinguish byte-identical independent occurrences. Wazuh native ID is preferred. Provenance roots are configured in the authenticated principal, not accepted from event payload.

## Gate B (only after A passes)

Fixed UTC event-time windows with versioned configuration and explicit bounded lateness. Durable relational membership is authoritative for grouping; no event is deleted for matching a fingerprint. Grouping requires environment, source/actor, target, activity, outcome, validation context and nearby time. Missing identities are isolated. Closed/expired windows route later input to separate non-promotable groups. Per-environment row locks and unique membership enforce retry/concurrent-worker idempotence. Decisions explain matched and excluded candidates; confidence means dimension coverage, never probability.

## Gate C (only after B passes)

Versioned deterministic promotion, factor-based risk, bounded active-incident merge and evidence references. Only NEW → TRIAGED → INVESTIGATING is exposed. Group / decision / incident changes, Audit and Outbox are atomic. Environment-scoped stable paginated reads expose lineage and explanations. No action, planner, task, verification or AI runtime.

Acceptance: additive migrations with M1 data preservation and down/up tests; complete regression suite; Docker HTTP golden chain including restart/concurrency; 1k/10k synthetic benchmark; final report and a new complete ZIP. Synthetic fixtures never count as real sensor runtime.
