"""Pure verdict aggregation is implemented now; probes are M2 adapters."""

from zhiyu.domain.contracts import Verdict, expected_verdict


def aggregate_three_check(security: Verdict, business: Verdict, observation: Verdict) -> Verdict:
    return expected_verdict(security, business, observation)
