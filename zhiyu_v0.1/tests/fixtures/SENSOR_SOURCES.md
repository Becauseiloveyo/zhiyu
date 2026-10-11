# Sensor fixtures — SYNTHETIC FIXTURE

All raw fixtures are hand-authored synthetic examples (reserved documentation IPs and domains, synthetic IDs). Expected JSON files are independently specified semantic projections; envelope, observables, identity and schema have additional test assertions. Fixture authoring does not execute adapters.

Format references inspected 2026-09-13:

- Suricata **8.0.2 EVE JSON**: https://docs.suricata.io/en/suricata-8.0.2/output/eve/eve-json-format.html
- Wazuh **4.x Alert JSON** (current documentation, not a pinned sensor deployment): https://documentation.wazuh.com/current/user-manual/manager/alert-management.html
- Wazuh Windows/Sysmon field shape and explicit MITRE fields: https://documentation.wazuh.com/current/user-manual/ruleset/mitre.html

These are format-derived synthetic inputs, not copied operational logs. REAL SENSOR RUNTIME = NOT_RUN.

Severity mapping sensor-map/1.0.0: Suricata 1→9, 2→6, 3→3, 4→1; Wazuh integer 0..15→round(level×10/15). Missing/out-of-range/noninteger/boolean→0. Original level stays vendor.severity, original alert/rule data stays raw.

Only curated metadata becomes OTHER: transport, source/target port, application protocol, rule/signature ID, vendor severity/category, HTTP method/status, DNS rcode, TLS version, flow state, host, Windows event ID, explicit MITRE/CVE. Unknown vendor blobs are not flattened. Validation tags in raw input cannot register a validation run. Forwarded sensors must share an operator-configured provenance root to avoid inflated independence.
