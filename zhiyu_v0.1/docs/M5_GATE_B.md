# Gate B — PASS

> 本文件保留该 Gate 完成时的阶段快照；后续完整验收与当前版本结论见 [v0.5 Validation](VALIDATION_REPORT_v0.5.0.md)。

2026-09-16: **50 passed / 0 failed / 0 skipped** across Gate A (22) and Gate B (28),
real PostgreSQL and a real HTTP scripted endpoint, 75.65 seconds.
[JUnit evidence](m5-gate-ab-tests.xml). Scripted outputs are boundary tests, not AI quality evidence.

A separate **real local Qwen model call passed** through the same ModelGateway and
persisted ai.5 ModelRun, bounded input/context manifest, original safe output text,
normalized output, hashes, 3,897 input / 699 output tokens and separate provider/system
timings. [Runtime details and evidence](M5_MODEL_RUNTIME.md).

- Provider-independent adapter; operator-only endpoint/key configuration, no proxy or
  redirect following, private local/public TLS endpoint restrictions, bounded HTTP I/O.
- Closed schema, duplicate/non-finite JSON rejection, tool/refusal/truncated/oversized
  output rejection, timeout/500/429/UTF-8/connection failures and deterministic fallback.
- Offline/cloud and classification denial happens before network calls.
- Per-incident durable call/token/wall budgets; unknown usage remains conservatively
  reserved. Returned usage is retained even for rejected generation; cost is not guessed.
- Two workers cause only one call. Interrupted work becomes a terminal fallback without
  automatic resampling; persisted results replay after restart. Terminal requests,
  receipts and managed ModelRun cannot be silently overwritten.
- Secret canary absent from model requests, stored request/receipt and captured logs.

ModelRun.safety_status at this Gate describes transport/schema controls only. Its output
remains a proposal and must pass later grounding and plan-policy validators before any
ordinary Task graph is created. No authorization or execution shortcut exists.

Added fixed migration 0012_model_gateway, three internal tables, no ai.5 changes.
Gate C may now begin; overall v0.5 remains NOT PASS until Gates C–E pass.
