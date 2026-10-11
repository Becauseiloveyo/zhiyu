"""Select direct wheel URLs offline from the unchanged, hashed dependency locks.

Uses packaging already vendored in the bootstrap pip; it adds no dependency.
Unsupported platforms or disagreeing identities fail before network access.
"""

import argparse
import json
import re
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.tags import sys_tags
from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename

ROOT = Path(__file__).resolve().parents[1]
LOCKS = ("requirements-runtime.lock", "requirements-build.lock", "requirements-operator.lock")


def selected(root=ROOT, tags=None, marker_environment=None):
    ranks = {tag: rank for rank, tag in enumerate(sys_tags() if tags is None else tags)}
    packages = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))["package"]
    packages.append(json.loads((root / "config/reference-build-wheel.json").read_text(encoding="utf-8")))
    locked = {}
    for name in LOCKS:
        content = (root / name).read_text(encoding="utf-8").replace("\\\n", " ")
        for line in content.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            hashes = set(re.findall(r"--hash=sha256:([a-f0-9]{64})", line))
            requirement = Requirement(re.sub(r"--hash=sha256:[a-f0-9]{64}", "", line).strip())
            if requirement.marker and not requirement.marker.evaluate(marker_environment):
                continue
            if requirement.url or len(requirement.specifier) != 1 or not hashes:
                raise RuntimeError("reference_lock_not_exact_or_hashed")
            pin = next(iter(requirement.specifier))
            if pin.operator != "==" or "*" in pin.version:
                raise RuntimeError("reference_lock_not_exact_or_hashed")
            key = canonicalize_name(requirement.name)
            if key in locked and locked[key] != (pin.version, hashes):
                raise RuntimeError("reference_duplicate_lock_disagrees")
            locked[key] = (pin.version, hashes)
    result = []
    for name, (version, hashes) in sorted(locked.items()):
        candidates = []
        for package in packages:
            if canonicalize_name(package["name"]) != name or package["version"] != version:
                continue
            for wheel in package.get("wheels", []):
                url = urlsplit(wheel["url"])
                if url.scheme != "https" or url.hostname != "files.pythonhosted.org" or url.query or url.fragment:
                    raise RuntimeError("reference_wheel_source_invalid")
                wheel_name, wheel_version, _, wheel_tags = parse_wheel_filename(Path(url.path).name)
                if canonicalize_name(wheel_name) != name or str(wheel_version) != version:
                    raise RuntimeError("reference_wheel_identity_invalid")
                if not wheel["hash"].startswith("sha256:") or wheel["hash"][7:] not in hashes:
                    raise RuntimeError("reference_wheel_hash_not_in_lock")
                compatible = wheel_tags.intersection(ranks)
                if compatible:
                    candidates.append((min(ranks[tag] for tag in compatible), wheel["url"], wheel["hash"]))
        if not candidates:
            raise RuntimeError("reference_compatible_wheel_missing:" + name)
        _, url, digest = min(candidates)
        result.append(f"{name} @ {url} --hash={digest}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    lines = selected()
    args.output.write_text("# Derived offline from frozen locks; no index resolution.\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"selected_wheels": len(lines), "source": "FROZEN_LOCK_URLS", "hashes": "REQUIRED"}))


if __name__ == "__main__":
    main()
