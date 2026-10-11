"""Verify raw source bytes in tested images and bind the production Web build to its inputs."""

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts/v0.9/source-correspondence.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(folder, suffix=None):
    return {
        path.relative_to(ROOT).as_posix(): sha(path)
        for path in sorted((ROOT / folder).rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and (suffix is None or path.suffix == suffix)
    }


def digest(mapping):
    return hashlib.sha256(json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def docker(*arguments):
    run = subprocess.run(
        ["docker", *arguments], capture_output=True, text=True, encoding="utf-8", timeout=120
    )
    if run.returncode:
        raise RuntimeError("image_correspondence_command_failed")
    return json.loads(run.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", action="append", required=True)
    args = parser.parse_args()
    source = files("src", ".py")
    tests = files("tests")
    locks = {
        name: sha(ROOT / name) for name in ("uv.lock", "requirements-runtime.lock", "requirements-build.lock")
    }
    tools = files("tools", ".py")
    result = {"status": "IN_PROGRESS", "as_of": datetime.now(UTC).isoformat(), "images": {}}
    script = """
import hashlib,json,pathlib,zhiyu
p=pathlib.Path(zhiyu.__file__).parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
print(json.dumps({
 'source': {'src/'+x.relative_to(p.parent).as_posix():sha(x) for x in p.rglob('*.py')},
 'tools': {'tools/'+x.relative_to(pathlib.Path('/app/tools')).as_posix():sha(x) for x in pathlib.Path('/app/tools').rglob('*.py')},
 'tests': {'tests/'+x.relative_to(pathlib.Path('/app/tests')).as_posix():sha(x) for x in pathlib.Path('/app/tests').rglob('*') if x.is_file() and '__pycache__' not in x.parts},
 'locks': {x:sha(pathlib.Path('/app')/x) for x in ['uv.lock','requirements-runtime.lock','requirements-build.lock']},
 'version':zhiyu.__version__
}))
"""
    for tag in args.image:
        meta = docker("image", "inspect", tag)[0]
        actual = docker("run", "--rm", "--network=none", "--entrypoint", "python", meta["Id"], "-c", script)
        assert actual["source"] == source, "installed_source_bytes_differ"
        assert actual["tools"] == tools, "baked_tool_bytes_differ"
        assert actual["locks"] == locks, "backend_locks_differ"
        assert all(tests.get(name) == value for name, value in actual["tests"].items()), "baked_tests_differ"
        if "tests/test_product_demo.py" in actual["tests"]:
            assert actual["tests"] == tests, "test_image_inventory_differ"
        assert actual["version"] == "0.9.0"
        result["images"][tag] = {
            "id": meta["Id"],
            "source": actual["source"],
            "tools": actual["tools"],
            "locks": actual["locks"],
            "tests": actual["tests"],
        }
    frontend = files("frontend/src") | files("frontend/public")
    frontend |= {
        "frontend/" + name: sha(ROOT / "frontend" / name)
        for name in (
            "package.json",
            "package-lock.json",
            "index.html",
            "vite.config.js",
            "vitest.config.js",
            "tsconfig.json",
            "eslint.config.js",
        )
    }
    built = files("frontend/dist")
    assert "frontend/dist/index.html" in built and len(built) > 2
    rc = json.loads((ROOT / "RC_STATE_v0.6.0.json").read_text())
    original = json.loads((ROOT / "artifacts/v0.9/original-test-inventory.json").read_text())
    assert all(sha(ROOT / name) == value for name, value in original.items())
    assert all(sha(ROOT / name) == value for name, value in rc["frozen_files"].items())
    result.update(
        status="PASS_RAW_BYTES",
        source_digest=digest(source),
        source=source,
        backend_locks=locks,
        frontend_inputs=frontend,
        frontend_input_digest=digest(frontend),
        frontend_build=built,
        frontend_build_digest=digest(built),
        frontend_lock_digest=frontend["frontend/package-lock.json"],
        original_test_files_unchanged=len(original),
        frozen_files_unchanged=len(rc["frozen_files"]),
        digest_algorithm="SHA256 of sorted compact JSON path-to-raw-byte-SHA256 map",
        limitation="Build execution and test results are separate evidence; this checks their byte correspondence.",
    )
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "images": {k: v["id"] for k, v in result["images"].items()},
                "source_digest": result["source_digest"],
                "frontend_build_digest": result["frontend_build_digest"],
            }
        )
    )


if __name__ == "__main__":
    main()
