# v0.5 — AI Decision Brain / Context / Model Gateway

Status: v0.5 PASS within controlled local acceptance; see VALIDATION_REPORT_v0.5.0.md.

Baseline: v0.4 ZIP SHA256 `e4ff484d08f5f2caa9dba6abc73939ef3ee98657e76f07286eb2971a50409eb2`.
All 245 existing tests remain. ai.5 contracts and migrations 0001–0010 remain byte-identical.

1. Gate A: bounded read models over existing state/resources/sensors/evidence; immutable
   state snapshots and context bodies/manifests alongside frozen ContextBundle. Registry
   configuration is not sensor FACT. MODEL_HYPOTHESIS maps to frozen INFERENCE with
   explicit MODEL_INFERENCE provenance. Missing vulnerabilities/criticality remain unknown.
2. Gate B: provider-neutral structured gateway, durable reservations and terminal ModelRun,
   finite incident call/token/time budgets, fail-closed egress and deterministic fallback.
   Endpoint/credential configuration is operator-controlled, never model-controlled.
3. Gate C: analysis proposals with evidence-reference grounding; no claim of validating
   unrestricted natural-language truth; model confidence is uncalibrated self-report.
4. Gate D: bounded plan proposals validated against current context, registry, scope, DAG,
   health and aggregate risk. Accepted proposals become ordinary AIPlan/Task graph objects;
   all original authorization/dispatch checks still apply. SHADOW is an AI influence mode,
   not a replacement for frozen EnvironmentProfile.autonomy_mode.
5. Gate E: five real controlled closed-loop scenarios, unavailable-provider fallback,
   interrupted/replayed/concurrent requests, migration preservation, real model runtime,
   20–50 safety evaluation fixtures, performance and auditable package delivery.

Model messages use a fixed system template and JSON-encoded UNTRUSTED_EVIDENCE data.
Prompt delimiters are not the security boundary: output schemas, reference validation,
registry allowlists, existing risk gates and independent verification enforce the boundary.
Raw forensic evidence is not modified by model-input redaction. No tool/executor capability,
arbitrary shell, SSH, root credential or model-supplied endpoint is exposed to a provider.

Real local Qwen2.5-1.5B / llama.cpp runtime was accepted. Scripted providers remain separately labeled boundary-test fixtures; they are not model-quality evidence.
