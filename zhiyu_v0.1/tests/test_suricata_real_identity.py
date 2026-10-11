import base64
import json

import pytest
from test_adapters import context, normalize, raw

from zhiyu.adapters.base import AdapterError
from zhiyu.core.intelligence_config import IntelligenceConfig
from zhiyu.services.correlation_keys import CorrelationKeyBuilder


def basic(user="lab-user", password="ZHIYU_TEST_SECRET_DO_NOT_EXPOSE"):
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def test_real_http_auth_claim_correlates_without_password_or_authorization():
    network = raw("suricata", "authentication")
    network["http"]["authorization"] = basic()
    host = raw("wazuh", "authentication")
    host["rule"]["groups"] = ["authentication_failed"]
    host["data"].update(srcip=network["src_ip"], dstip=network["dest_ip"], dstport="8080", protocol="TCP")
    host["data"]["srcuser"] = "lab-user"
    first = normalize(network)
    second = normalize(host, context("wazuh"))
    assert first.outcome == "DENIED"
    assert any(item.observable_type == "USER" and item.value == "lab-user" for item in first.observables)
    serialized = first.model_dump_json()
    assert (
        "ZHIYU_TEST_SECRET_DO_NOT_EXPOSE" not in serialized
        and network["http"]["authorization"] not in serialized
    )
    assert first.mapping_version == "sensor-map/suricata-http-basic/1.0.0"
    assert "OBSERVED_CLAIM_NOT_AUTHORIZATION" in serialized
    keys = CorrelationKeyBuilder(IntelligenceConfig())
    assert keys.build(first).digest == keys.build(second).digest
    host["data"]["srcuser"] = "different-user"
    assert keys.build(first).digest != keys.build(normalize(host, context("wazuh"))).digest


@pytest.mark.parametrize(
    "header",
    [
        "Basic !!!",
        "Basic " + base64.b64encode(b"no-colon").decode(),
        basic("bad\nuser"),
        basic(""),
        basic("a" * 257),
        42,
    ],
)
def test_malformed_authentication_identity_is_rejected_without_secret_in_error(header):
    value = raw("suricata", "authentication")
    value["http"]["authorization"] = header
    with pytest.raises(AdapterError, match="mapping_error: http.authorization") as caught:
        normalize(value)
    assert "ZHIYU_TEST_SECRET_DO_NOT_EXPOSE" not in str(caught.value)


def test_bearer_is_not_decoded_as_user_or_exposed():
    value = raw("suricata", "authentication")
    value["http"]["authorization"] = "Bearer ZHIYU_TEST_SECRET_DO_NOT_EXPOSE"
    before = json.dumps(value)
    result = normalize(value)
    assert not any(item.observable_type == "USER" for item in result.observables)
    assert "ZHIYU_TEST_SECRET_DO_NOT_EXPOSE" not in result.model_dump_json()
    assert json.dumps(value) == before


def test_real_suricata_7_request_headers_shape_and_ambiguous_headers():
    value = raw("suricata", "authentication")
    value["http"]["request_headers"] = [{"name": "Authorization", "value": basic()}]
    event = normalize(value)
    assert any(item.observable_type == "USER" and item.value == "lab-user" for item in event.observables)
    assert "ZHIYU_TEST_SECRET_DO_NOT_EXPOSE" not in event.model_dump_json()
    value["http"]["request_headers"].append({"name": "authorization", "value": basic("different-user")})
    with pytest.raises(AdapterError, match="http.authorization"):
        normalize(value)
