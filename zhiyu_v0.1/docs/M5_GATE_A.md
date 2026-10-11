# Gate A — PASS

> 本文件保留该 Gate 完成时的阶段快照；后续完整验收与当前版本结论见 [v0.5 Validation](VALIDATION_REPORT_v0.5.0.md)。

2026-09-16: **22 passed / 0 failed / 0 skipped**, real PostgreSQL, 26.04 seconds.
[JUnit evidence](m5-gate-a-tests.xml).

- Frozen ContextBundle reused; two internal immutable tables added in 0011_ai_context.
- Registered configuration, operational telemetry, evidence-supported observations,
  rule inference and MODEL_HYPOTHESIS remain distinct. No AI FACT writer exists.
- Source/evidence/time/quality/freshness manifest, environment isolation, deterministic
  compression and hard character/conservative token bounds pass.
- Eight malicious evidence forms remain in a JSON data message under a fixed system
  prompt. This proves request isolation; later Gates must prove output rejection as well.
- Canary exclusion preserves original evidence. Immutable context/state snapshots,
  read-after-restart, idempotency and simultaneous builders pass.

Schema validators and query integration were corrected during implementation. The
canary source-preservation test now reads its exact Evidence ID rather than relying on
unspecified SQL row order. No frozen contract or old migration changed.

Gate B may now begin. Overall v0.5 remains NOT PASS pending Gates B–E and real runtime.
