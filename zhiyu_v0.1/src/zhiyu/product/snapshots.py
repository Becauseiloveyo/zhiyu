"""Bounded, expiring, immutable DTO cache. It is never a source of canonical facts."""

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections import OrderedDict
from typing import Any

from fastapi import HTTPException

from zhiyu.product.contracts import Snapshot

_key = secrets.token_bytes(32)
_lock = threading.Lock()
_cache: OrderedDict[str, tuple[float, str, bytes]] = OrderedDict()
TTL = 300
MAX_BYTES = 1024 * 1024
MAX_CACHE_BYTES = 32 * MAX_BYTES


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
    ).hexdigest()


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(hmac.digest(_key, raw, "sha256") + raw).decode()


def decode_cursor(value: str, binding: str) -> dict[str, Any]:
    try:
        if len(value) > 4096:
            raise ValueError
        raw = base64.b64decode(value, altchars=b"-_", validate=True)
        signature, body = raw[:32], raw[32:]
        if not hmac.compare_digest(signature, hmac.digest(_key, body, "sha256")):
            raise ValueError
        data = json.loads(body)
        if data["binding"] != binding or data["expires"] < time.time():
            raise ValueError
        return data
    except (ValueError, KeyError, TypeError):
        raise HTTPException(422, "invalid_or_expired_cursor") from None


def put(snapshot: Snapshot, binding: str) -> None:
    body = snapshot.model_dump_json().encode()
    if len(body) > MAX_BYTES:
        raise HTTPException(413, "snapshot_budget_exceeded_narrow_query")
    with _lock:
        now = time.monotonic()
        for key in [key for key, entry in _cache.items() if entry[0] <= now]:
            del _cache[key]
        while _cache and sum(len(v[2]) for v in _cache.values()) + len(body) > MAX_CACHE_BYTES:
            _cache.popitem(last=False)
        _cache[snapshot.snapshot_id] = (now + TTL, binding, body)


def get(identifier: str, binding: str) -> Snapshot:
    with _lock:
        record = _cache.get(identifier)
        if record is None or record[0] <= time.monotonic():
            _cache.pop(identifier, None)
            raise HTTPException(410, "snapshot_expired_refresh_explicitly")
        if not hmac.compare_digest(record[1], binding):
            raise HTTPException(404, "snapshot_not_found")
        return Snapshot.model_validate_json(record[2])
