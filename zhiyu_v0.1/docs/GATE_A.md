# Gate A — PASS

Completed before Gate B implementation, 2026-09-13. ai.5 contract byte identity preserved.

- 112 non-Compose tests passed / 0 failed / 0 skipped; [JUnit](gate-a-tests.xml).
- Independent host Compose test: 1 passed; [output](gate-a-compose.txt), [JUnit](gate-a-compose.xml).
- All original 47 M1.1 tests are included in these two runs, with only schema/module inventory assertions advanced for the six new modules and two additive tables.
- Docker: all 37 acceptance checks passed; [runtime result](docker-runtime/zhiyu-smoke-2285f375fae9/result.json). Linux container suite also passed.
- Ruff and mypy (45 modules) passed. Two upstream warning classes remain: Starlette httpx test-client deprecation and AnyIO BlockingPortal alias deprecation.

Implemented: explicit registry, 12 synthetic Golden Mapping fixtures, timestamp/severity/identity/observable mapping, unknown EVE fallback, per-record errors, raw BYTEA retention and SHA256, per-delivery metrics data, savepoint isolation, Audit/Outbox atomicity, concurrent deduplication, migration roundtrip and old data preservation.

Finding repaired: receive-time clock assessment must not change source-event retransmission identity. Comparisons rehydrate old events so pre-upgrade stored hash values remain compatible. Immutable event contents and every delivery receipt remain retained.

REAL SENSOR RUNTIME = NOT_RUN. Format sources and limitations: [fixture provenance](../tests/fixtures/SENSOR_SOURCES.md).
