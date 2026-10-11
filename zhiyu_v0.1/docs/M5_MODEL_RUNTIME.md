# Local model runtime — pinned runtime and development evidence

This is a real local model, not the scripted HTTP provider used in boundary tests.
The preflight files below are development-stage evidence. Overall acceptance and final
test counts are reported separately in the v0.5 Validation Report after Gate E completes.

Final controlled acceptance: **343 tests / 190 Docker checks PASS**, including a real
AI-assisted Action/independent Verification chain and 24 evaluated Context cases (28 real
model calls). [Validation](VALIDATION_REPORT_v0.5.0.md) / [AI Evaluation](AI_EVALUATION_REPORT_v0.5.0.md).
The quality review found unsupported semantic claims despite valid references; acceptance
of execution boundaries does not establish reliable model reasoning.

- Provider: local-llama-cpp; local CPU inference in an isolated Docker container.
- Model: Qwen/Qwen2.5-1.5B-Instruct-GGUF, Q4_K_M, 1,117,320,736 bytes.
- Model repository revision: `91cad51170dc346986eccefdc2dd33a9da36ead9`.
- Model SHA256: `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.
- Runtime image: `ghcr.io/ggml-org/llama.cpp@sha256:b15cd87030b2eb8a284d398c095e03c6ba8baf386b68e1b83ab8b46e9555ffe8`.
- 6 CPU threads, 4 GiB container limit, 8,192-token model window, one inference slot.
- Preflight used a loopback host binding; final Docker acceptance publishes no model host
  port. API key supplied through a private read-only file; no key in
  project/image/fixtures/reports. No web UI, agent/tools, privileged capabilities or root.
- Structured request uses `response_format: json_object + schema`, then independent
  JSON/schema validation. Runtime outputs never authorize an executor.

[Successful actual request/context/result/token timing](m5-real-gateway-preflight.json).
The first successful call used 3,897 input and 699 output tokens; provider time 41,265 ms,
gateway overhead 53.823 ms, schema validation 0.776 ms. Cost is unavailable (`null`).
These are single-call development measurements, not an SLA or AI accuracy measurement.

[Later real Brain preflight](m5-real-brain-preflight.json) also passed reference grounding
and Lab proposal validation through ordinary cycle activation. It did not execute an
Action; final Action/Verification evidence must come from Gate E. The small model showed
semantic uncertainty about synthetic source provenance despite valid references; this
is a quality limitation, not a proof that source evidence is false.

The 1.04 GiB GGUF and private credential are deliberately outside the source archive.
Download the exact file linked below, verify the SHA256 above, and supply private absolute
paths using `ZHIYU_MODEL_PATH` / `ZHIYU_MODEL_KEY_FILE`. See [operation instructions](AI_DECISION_BRAIN.md).

Official provenance: [Qwen model file and checksum](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/blob/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q4_k_m.gguf),
[llama.cpp Docker documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md),
[server protocol](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

## Findings during setup

1. Windows CRLF in the API-key file caused the server to reject authentication. The
   private runtime helper now writes LF bytes explicitly. Gateway persisted failure
   without a Plan, preserving [failure evidence](m5-real-gateway-preflight-auth-failure.json).
2. An unconcise model response reached the 1,200-token output cap and was correctly
   rejected as INCOMPLETE_RESPONSE. [Evidence](m5-real-gateway-preflight-truncated.json).
   The fixed server task instructions now request one finding/hypothesis/task and short
   narratives. Limits were not relaxed to accept truncated JSON.
3. Review found that rejected generation could lose provider usage/timing. Failure
   receipts now preserve known token counts and provider latency, keeping unknown usage
   conservatively reserved. No raw rejected output or exception text is stored.
4. A generic credential-key redactor initially treated a controlled authorization flag
   as a secret. Input checks now inspect already allowlisted scalars; untrusted source
   projection still redacts credential-bearing keys. Original forensic data is unchanged.
