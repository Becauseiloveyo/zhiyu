from zhiyu.domain.contracts import ResourceRef, Verdict, expected_verdict


def test_cross_platform_resource_ref_network():
    ref = ResourceRef(
        resource_id="target-a",
        environment_id="lab",
        resource_type="NETWORK_ENDPOINT",
        binding_version=1,
        locator={"address": "10.0.0.2", "port": 8080, "protocol": "TCP"},
    )
    assert ref.locator["port"] == 8080


def test_three_check_never_false_pass():
    assert expected_verdict(Verdict.PASS, Verdict.PASS, Verdict.INCONCLUSIVE) == Verdict.INCONCLUSIVE
    assert expected_verdict(Verdict.PASS, Verdict.FAIL, Verdict.PASS) == Verdict.FAIL
