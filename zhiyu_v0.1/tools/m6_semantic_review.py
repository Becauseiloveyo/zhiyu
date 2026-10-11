"""Conservative review flags, never a semantic truth/accuracy classifier."""

import re

PATTERNS = {
    "causal_language": r"\b(caused?|causal|led to|resulted in|because|due to|therefore)\b",
    "deterministic_security_claim": r"\b(confirmed attack|definitely compromised|fully secure|attack prevented|remediation succeeded|incident resolved|incident closed|false positive confirmed)\b",
    "claimed_authority": r"\b(authorized|admin approved|permission granted|policy override)\b",
    "observation_inference_mixing": r"\b(proves?|guarantees?|certainly|undeniably|demonstrates compromise)\b",
    "intent_or_exoneration_claim": r"\b(benign|malicious|attacker|false.positive)\b",
    "availability_or_security_claim": r"\b(is|are|was|were)\s+(?:not\s+)?(?:reachable|unreachable|operational|healthy|secure|compromised)\b|\bindicat\w*\s+(?:a\s+)?security issue\b",
    "sensor_origin_claim": r"\breal sensor finding\b",
}


def review(value):
    flags = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, item in node.items():
                walk(item, path + "/" + key)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, path + "/" + str(index))
        elif isinstance(node, str):
            for name, pattern in PATTERNS.items():
                if re.search(pattern, node, re.I):
                    flags.append(
                        {
                            "rule": name,
                            "path": path,
                            "text": node,
                            "negation_or_uncertainty_present": bool(
                                re.search(
                                    r"\b(no|not|cannot|unproven|unknown|unverified|uncertain)\b", node, re.I
                                )
                            ),
                        }
                    )

    walk(value, "")
    return {
        "status": "SEMANTIC_REVIEW_REQUIRED",
        "flags": flags,
        "unsupported_claim_count": None,
        "semantics": "Flags can include negated/cautious language; absence of flags is not proof of truth",
        "rule_version": "semantic-review/1.1.0",
        "language_scope": "English risk markers; not general semantic inference or multilingual coverage",
    }
