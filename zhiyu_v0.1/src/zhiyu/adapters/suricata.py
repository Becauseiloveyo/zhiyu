import base64
import binascii
from typing import Any

from zhiyu.adapters.base import (
    MAPPING_VERSION,
    SURICATA_SEVERITY,
    AdapterContext,
    AdapterError,
    Facts,
    build_event,
    object_field,
    severity,
)
from zhiyu.domain.contracts import NormalizedEvent


def observed_basic_username(value: Any) -> str | None:
    """Extract only the claimed user. HTTP authentication is not authorization."""
    if not isinstance(value, str) or len(value) > 8192:
        raise AdapterError("mapping_error", "http.authorization")
    scheme, _, encoded = value.partition(" ")
    if scheme.lower() != "basic":
        return None
    try:
        credential = base64.b64decode(encoded, validate=True)
        user, separator, _ = credential.partition(b":")
        username = user.decode("utf-8")
    except (ValueError, UnicodeError, binascii.Error):
        raise AdapterError("mapping_error", "http.authorization") from None
    if not separator or not 1 <= len(username) <= 256 or any(ord(c) < 32 or ord(c) == 127 for c in username):
        raise AdapterError("mapping_error", "http.authorization")
    return username


def authorization_header(http: dict[str, Any]) -> str | None:
    headers = http.get("request_headers", [])
    if not isinstance(headers, list) or any(not isinstance(item, dict) for item in headers):
        raise AdapterError("mapping_error", "http.request_headers")
    values = [http["authorization"]] if "authorization" in http else []
    values.extend(
        item.get("value") for item in headers if str(item.get("name", "")).lower() == "authorization"
    )
    if len(values) > 1 or (values and not isinstance(values[0], str)):
        raise AdapterError("mapping_error", "http.authorization")
    return values[0] if values else None


class SuricataAdapter:
    def normalize(self, raw: dict[str, Any], ctx: AdapterContext) -> NormalizedEvent:
        kind = raw.get("event_type")
        if not isinstance(kind, str) or not kind.strip():
            raise AdapterError("missing_required_identity", "event_type")
        facts = Facts()
        facts.network(raw)
        category, action, outcome, level = "network", kind, "UNKNOWN", 0
        alert = object_field(raw, "alert")
        if kind == "alert":
            if "signature_id" not in alert:
                raise AdapterError("missing_required_identity", "alert.signature_id")
            category, action = "network_alert", "signature_match"
            # 'allowed' means IDS allowed traffic; it does NOT establish attack success.
            outcome = "DENIED" if alert.get("action") == "blocked" else "UNKNOWN"
            level = severity(alert.get("severity"), SURICATA_SEVERITY)
            for key in ("signature_id", "category", "severity"):
                facts.meta("vendor." + key, alert.get(key))
            metadata = object_field(alert, "metadata")
            for key in ("mitre_tactic_id", "mitre_technique_id", "cve"):
                values = metadata.get(key, [])
                if isinstance(values, str):
                    values = [values]
                if not isinstance(values, list):
                    raise AdapterError("mapping_error", "alert.metadata." + key)
                for value in values:
                    facts.meta(key, value)
        http = object_field(raw, "http")
        mapping = MAPPING_VERSION
        if http:
            authorization = authorization_header(http)
            if authorization is not None:
                mapping = "sensor-map/suricata-http-basic/1.0.0"
                facts.add("USER", observed_basic_username(authorization), "SOURCE")
                facts.meta("http.identity_semantics", "OBSERVED_CLAIM_NOT_AUTHORIZATION")
            facts.add("DOMAIN", http.get("hostname"), "TARGET")
            facts.add("URL", http.get("url"), "TARGET")
            facts.meta("http.method", http.get("http_method"))
            facts.meta("http.status", http.get("status"))
            if kind == "http":
                category, action = "web", "http_request"
            # Only an explicit HTTP authentication challenge carries this fact.
            if http.get("status") == 401:
                category, action, outcome = "authentication", "authenticate", "DENIED"
            elif kind == "http" and isinstance(http.get("status"), int):
                status = http["status"]
                outcome = "SUCCESS" if 200 <= status < 400 else "FAILURE" if status >= 400 else "UNKNOWN"
        dns = object_field(raw, "dns")
        if kind == "dns":
            category, action = "dns", str(dns.get("type", "query"))
            facts.add("DOMAIN", dns.get("rrname"), "TARGET")
            for query in dns.get("queries", []):
                if not isinstance(query, dict):
                    raise AdapterError("mapping_error", "dns.queries")
                facts.add("DOMAIN", query.get("rrname"), "TARGET")
            facts.meta("dns.rcode", dns.get("rcode"))
        if kind == "tls":
            tls = object_field(raw, "tls")
            category, action = "tls", "handshake"
            facts.add("DOMAIN", tls.get("sni"), "TARGET")
            facts.add("HASH", tls.get("fingerprint"))
            facts.meta("tls.version", tls.get("version"))
        if kind == "flow":
            facts.meta("flow.state", object_field(raw, "flow").get("state"))
        return build_event(
            raw,
            ctx,
            facts,
            event_type="suricata." + kind,
            category=category,
            action=action,
            outcome=outcome,
            level=level,
            mapping_version=mapping,
        )
