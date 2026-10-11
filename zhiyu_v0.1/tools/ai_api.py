"""Optional API entry point: load provider key from a read-only secret mount, never log it."""

import os
from pathlib import Path

import uvicorn

path = os.environ.get("ZHIYU_MODEL_KEY_FILE")
if path:
    key = Path(path).read_text(encoding="utf-8").strip()
    if not key or len(key) > 4096 or "\n" in key or "\r" in key:
        raise RuntimeError("invalid mounted model credential")
    os.environ["ZHIYU_LOCAL_MODEL_KEY"] = key

if __name__ == "__main__":
    uvicorn.run("zhiyu.main:app", host="0.0.0.0", port=8000)
