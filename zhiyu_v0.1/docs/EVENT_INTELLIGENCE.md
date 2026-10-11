# Deterministic Event Intelligence — v0.2.0

Scope: Read / Normalize / Correlate / Incident. ai.5, the original migration and the original 0001 DDL are unchanged. The new tables are storage metadata and relations, not replacement Event or Incident contracts.

## Raw ingestion

`POST /v1/events/raw-batches` accepts environment_id, collector_id, source_type (`suricata` or `wazuh`), data_origin and 1–1000 records. Each record contains the original JSON **string** and optional origin_event_id. Batch body limit is 4 MiB; each raw record is at most 256 KiB. Auth checks run before storage. Synthetic ingestion additionally requires `events:synthetic`.

The raw input is stored as BYTEA with SHA256. Each delivery receives an immutable result, raw reference, disposition, normalization duration and an Audit entry. Malformed JSON, duplicate JSON keys, invalid Unicode, malformed/naive timestamp, invalid IP/protocol, missing identity and mapping errors are isolated. PostgreSQL infrastructure failure rolls the outer transaction back. A normal bad record uses a savepoint so its valid neighbors survive.

Wazuh native ID or a collector-provided origin cursor identifies a record. Suricata without a cursor uses the canonical complete JSON hash, never flow_id alone. Therefore byte-identical independent occurrences without an origin cursor cannot be distinguished; collectors should provide a durable file offset/capture cursor. Receipts preserve retransmission raw references. Source timestamp is retained in UTC; receive-time clock assessment is excluded from replay content comparison.

Naive or unparseable source timestamps are rejected. Clock status is SKEWED for >5 minutes into the future or >24 hours delayed; timestamps are never invented. Explicit severity maps, source levels, fact allowlist and synthetic fixture provenance are documented in [SENSOR_SOURCES.md](../tests/fixtures/SENSOR_SOURCES.md). HTTP `allowed` never becomes attack success. Only explicit MITRE/CVE facts are copied. Vendor blobs are retained in raw rather than flattened.

`ServicePrincipal.provenance_roots` maps `collector/source` to an operator-controlled origin root. Forwarders of the same sensor should share a root. Unconfigured roots default to collector/source. Different collector names alone do not prove independent sensors; the deployment operator must configure forwarding lineage. Raw payload labels cannot assign environment, provenance, resources or validation_run_id. Network resources are bound only by an unambiguous address/port/protocol match; host bindings require an unambiguous address.

## Correlation

`POST /v1/intelligence/process` requires `intelligence:write`, an environment_id and optional limit (1–1000). It first commits one correlation batch, then evaluates pending group versions for Incident promotion. The database is the durable work queue: ungrouped events and unevaluated group versions remain visible after failure/restart. Calling it until correlation.pending is zero drains the input. If promotion failed after correlation committed, repeating the request resumes promotion. There is no Task Scheduler, active executor or autonomous background loop.

`IntelligenceConfig` centralizes versioned window values. Defaults: auth 300s, network alert 60s, web 120s, generic 60s; lateness grace 120s. Changes to configuration participate in the correlation key and are stored alongside each group.

Keys compare environment, source IP/resource, explicit actor, user, target IP/resource, target port, transport, activity, action, outcome, data origin, registered validation context and fixed UTC window. Missing source/target causes isolation. Known and unknown user identities are different keys. Authentication supports cross-vendor joins; other categories additionally require matching vendor/rule identity. Correlation does not establish that an attack happened.

Timely out-of-order events can join OPEN windows. Reception beyond window end + grace is LATE; >24h delayed is EXPIRED; >5m future is FUTURE. Each of these gets an isolated non-promotable group. CLOSED windows never reopen. Closure waits for the current environment backlog to drain, avoiding a split merely because a large arrival batch needs multiple worker calls. Processing can close expired windows even without new events. Source events are never deleted because their fingerprints match.

`event_group_members` is the durable per-event processing checkpoint; a unique environment/event key prevents duplicate membership. Contract member arrays are synchronized snapshots. Each processed group revision creates a CorrelationDecision with the new inputs, rule/config/algorithm versions, source diversity, matched dimensions and a bounded earliest-100 same-window exclusion sample. The sample is explicitly not an exhaustive search over history. Confidence is source/target/user/activity dimension coverage, not probability. Relations support lineage and pagination independently of the contract arrays.

Every environment is serialized with a PostgreSQL row lock, shared by ingest, correlation, promotion and transitions. Group, decision, membership, Audit and Outbox writes share a transaction. Natural unique keys and persisted checkpoints make retry safe. Lock/statement failures propagate as storage failures; callers can retry. This is a correctness-first implementation with measured development throughput, not a horizontal scalability claim.

## Incident promotion and risk

`IncidentConfig` versions promotion, risk and merging. Default risk components are: max severity ×4; additional independent sources capped at 3 ×10; governed asset criticality ×4 (default 1, range 0–5); repeated events capped at 10 ×2; activity contribution; verified-raw fraction ×10; registered validation reduction 60. Scores are clamped 0–100. Priority thresholds: P0≥85, P1≥65, P2≥45, P3≥20, otherwise P4. Every assessment records components and input counts.

Default promotion requires score≥55, a bound target, a supported security activity and a meaningful pattern (severity≥9, or ≥3 events from ≥2 independent origins, or ≥5 events with severity≥5). Non-timely/expired/future groups, registered validation traffic and synthetic observations in PRODUCTION are not promoted. OT/MIXED profiles require corroboration. This produces a triage Incident, never an active response.

Merging requires the same environment, actor/user/source, target, service/transport, activity/outcome, validation context and policy version; only NEW, TRIAGED and INVESTIGATING incidents are eligible. The original first-observation horizon is bounded to 900s, preventing indefinite extension. CLOSED/later-runtime states are not automatically reopened or updated. A changed promotion policy does not silently rewrite an existing Incident under its old policy metadata.

Incident→Group and Incident→Event→Evidence use relations with environment-scoped FKs; Evidence ownership is constrained to the same Incident. Evidence references raw bytes when an immutable raw-delivery result proves this exact mapping, otherwise it references the immutable NormalizedEvent and stays UNVERIFIED_ORIGIN. Possessing a raw_ref alone is insufficient to claim verified origin. VERIFIED_ORIGIN here means authenticated collection plus stored-byte integrity, not a sensor signature or proof of hostile intent.

Lifecycle API exposes only NEW→TRIAGED→INVESTIGATING and requires expected_version. Triage validates schema, raw-ingest origin and fresh Evidence; investigation additionally checks passive evidence/resource scope membership. The latter does not authorize active operations or reuse expired active-operation permissions. Unsupported transitions and stale versions fail. An immediate retry of the same completed transition returns the existing version without another Audit/Outbox event.

## Read API

- `GET /v1/incidents?environment_id=...&status=NEW&min_risk=55&max_risk=100`
- `GET /v1/incidents/{id}` retains the frozen SecurityIncident response.
- `GET /v1/incidents/{id}/assessment` exposes deterministic score, factors and configuration.
- `GET /v1/incidents/{id}/events`, `/correlations`, `/evidence` expose paginated lineage.
- `POST /v1/incidents/{id}/transitions` accepts environment_id, target and expected_version.
- `GET /v1/intelligence/metrics?environment_id=...` reads persisted counts, compression, group-size/diversity distributions and correlation/promotion latency samples.

Reads require `incidents:read`; transitions additionally require `incidents:write`. Unauthorized Incident IDs have the same 404 response as missing IDs. Lists/lineage use stable timestamp+ID ordering and keyset cursors, with limit≤200. Internal db:// raw references are database evidence identifiers, never URLs fetched from a vendor payload.

## Validation boundaries

The fixed [Golden Chain](../tests/fixtures/golden_chain_m2.json) is synthetic. Its Wazuh entries model a custom application authentication rule; the dedicated SSH and Windows fixtures separately cover those formats. Docker replay gives the synthetic records an actual current timestamp and records the effective inputs, avoiding historical samples being misclassified as current traffic. Expected result: 4 raw → 4 normalized → 2 groups → 2 decisions → 1 Incident, 3 Evidence, score 62/P2; the unrelated user remains outside the Incident.

Benchmark sizes are 1k/10k, 100 events per modeled actor. The benchmark explicitly uses a one-hour auth window so long ingestion runs stay in the modeled interval. Timings measure real Linux service calls, PostgreSQL transactions and audit/outbox work; HTTP serialization is excluded. Reported compression is events/groups, not evidence deletion. REAL SENSOR RUNTIME = NOT_RUN. No Task/Risk Gate/Action/Verification/AI runtime is implemented.
