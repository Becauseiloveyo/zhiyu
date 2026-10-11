from typing import Any

from zhiyu.adapters.base import (
    WAZUH_SEVERITY,
    AdapterContext,
    AdapterError,
    Facts,
    build_event,
    object_field,
    severity,
)
from zhiyu.domain.contracts import NormalizedEvent


class WazuhAdapter:
    def normalize(self, raw: dict[str, Any], ctx: AdapterContext) -> NormalizedEvent:
        rule, data, agent = (object_field(raw, key) for key in ("rule", "data", "agent"))
        if not rule.get("id"):
            raise AdapterError("missing_required_identity", "rule.id")
        facts = Facts()
        facts.meta("vendor.rule_id", rule["id"])
        facts.meta("vendor.severity", rule.get("level"))
        facts.meta("host", agent.get("name"), "TARGET")
        facts.network(
            {
                "src_ip": data.get("srcip"),
                "dest_ip": data.get("dstip", agent.get("ip")),
                "src_port": data.get("srcport"),
                "dest_port": data.get("dstport"),
                "proto": data.get("protocol"),
            }
        )
        facts.add("USER", data.get("srcuser", data.get("dstuser", data.get("user"))), "SOURCE")
        facts.add("URL", data.get("url"), "TARGET")
        groups = rule.get("groups", [])
        if not isinstance(groups, list) or any(not isinstance(x, str) for x in groups):
            raise AdapterError("mapping_error", "rule.groups")
        category, action, outcome = "security_alert", "rule_match", "UNKNOWN"
        if "authentication_failed" in groups or "authentication_failures" in groups:
            category, action, outcome = "authentication", "authenticate", "DENIED"
        elif "authentication_success" in groups:
            category, action, outcome = "authentication", "authenticate", "SUCCESS"
        elif set(groups) & {"web", "web_accesslog", "apache", "nginx"}:
            category, action = "web", "http_request"
        mitre = object_field(rule, "mitre")
        for key in ("id", "tactic", "technique"):
            entries = mitre.get(key, [])
            if not isinstance(entries, list):
                raise AdapterError("mapping_error", "rule.mitre." + key)
            for value in entries:
                facts.meta("mitre." + key, value)
        for key in ("cve",):
            facts.meta(key, data.get(key))
        win = object_field(data, "win")
        if win:
            system, event = object_field(win, "system"), object_field(win, "eventdata")
            facts.meta("windows.event_id", system.get("eventID"))
            facts.meta("host", system.get("computer"), "TARGET")
            facts.add("USER", event.get("user", event.get("targetUserName")), "SOURCE")
            facts.add("PROCESS", event.get("image"), "SOURCE")
            facts.add("FILE", event.get("targetFilename"), "TARGET")
            facts.add("HASH", event.get("hashes"))
            facts.add("IP", event.get("ipAddress", event.get("sourceIp")), "SOURCE")
            facts.add("IP", event.get("destinationIp"), "TARGET")
            if str(system.get("eventID")) in {"4624", "4625"}:
                category, action = "authentication", "authenticate"
                outcome = "SUCCESS" if str(system["eventID"]) == "4624" else "DENIED"
            elif "sysmon" in str(system.get("providerName", "")).lower():
                category, action = "process", "windows_event"
        return build_event(
            raw,
            ctx,
            facts,
            event_type="wazuh.alert",
            category=category,
            action=action,
            outcome=outcome,
            level=severity(rule.get("level"), WAZUH_SEVERITY),
        )
