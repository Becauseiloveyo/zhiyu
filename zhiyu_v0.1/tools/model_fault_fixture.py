"""SCRIPTED_NOT_AI: deterministic adversarial HTTP responses for Docker safety acceptance."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 131072:
            self.send_error(413)
            return
        body = json.loads(self.rfile.read(length))
        mode = body["model"]
        document = json.loads(body["messages"][1]["content"])["UNTRUSTED_EVIDENCE"]
        fact = document["trusted_facts"][0]
        resource = document["incident"]["affected_resources"][0]
        if document["task_type"] == "ANALYSIS":
            output = {
                "incident_summary": "Fixture claims remediation succeeded"
                if mode == "SCRIPTED_CLAIMS_SUCCESS"
                else "Fixture analysis",
                "supported_findings": [
                    {
                        "claim": "Source reported activity",
                        "evidence_refs": [fact["evidence_id"]],
                        "resource_ids": [resource],
                        "observed_at": fact["observed_at"],
                    }
                ],
                "hypotheses": [
                    {
                        "claim": "Remediation succeeded"
                        if mode == "SCRIPTED_CLAIMS_SUCCESS"
                        else "Hostile intent unproven",
                        "evidence_refs": [],
                        "missing_evidence": ["Independent verification"],
                        "model_confidence": 0.99,
                    }
                ],
                "evidence_gaps": ["Independent verification"],
                "affected_resources": [resource],
                "recommended_next_steps": ["Collect bounded context"],
                "risk_observations": ["No authorization granted"],
                "uncertainty": "Synthetic fixture, not actual model reasoning",
                "confidence_semantics": "MODEL_SELF_REPORTED_UNCALIBRATED",
            }
        else:
            cap = (
                "disable_entire_network"
                if mode in {"SCRIPTED_HALLUCINATION", "SCRIPTED_INJECTION"}
                else "collect_resource_context"
            )
            output = {
                "objective": "Collect context",
                "reasoning_summary": "Synthetic adversarial output fixture",
                "evidence_refs": [fact["evidence_id"]],
                "proposed_tasks": [
                    {
                        "task_key": "collect",
                        "dependencies": [],
                        "capability_id": cap,
                        "target_resource_id": resource,
                        "parameters": {},
                        "reason": "Fixture request",
                        "expected_outcome": "Claims success"
                        if mode == "SCRIPTED_CLAIMS_SUCCESS"
                        else "Read receipt",
                        "verification_required": "INDEPENDENT_THREE_DIMENSION",
                    }
                ],
                "risk_notes": ["Independent verification required"],
                "success_is_unverified": True,
            }
        response = json.dumps(
            {
                "model": mode,
                "choices": [
                    {"message": {"role": "assistant", "content": json.dumps(output)}, "finish_reason": "stop"}
                ],
            }
        ).encode()
        # No invented token accounting for a scripted server.
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
