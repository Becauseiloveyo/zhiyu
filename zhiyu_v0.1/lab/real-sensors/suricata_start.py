"""Keep EVE files separated by actual sensor container identity."""

import os
import socket
from pathlib import Path

directory = Path("/var/log/suricata") / socket.gethostname()
directory.mkdir(parents=True, exist_ok=True)
os.execvp(
    "suricata",
    [
        "suricata",
        "-i",
        "eth0",
        "-k",
        "none",
        "--runmode",
        "single",
        "-S",
        "/lab.rules",
        "-l",
        str(directory),
        "--set",
        "stats.interval=5",
        "--set",
        "default-packet-size=65535",
        "--set",
        "max-pending-packets=1024",
        "--set",
        "app-layer.protocols.http2.enabled=no",
        "--set",
        "app-layer.protocols.smtp.enabled=no",
        "--set",
        "app-layer.protocols.smtp.mime.decode-quoted-printable=no",
    ],
)
