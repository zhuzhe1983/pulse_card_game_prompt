"""PCG-C14N-1, bounded JSON and shared errors. Python 3.10+; stdlib only."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

MAX_INT = 9007199254740991
MAX_PLAIN = 65536


class PCGError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}" if detail else code)


def validate_json(value: Any, depth: int = 0) -> None:
    if depth > 32:
        raise PCGError("JSON_DEPTH", "maximum nesting is 32")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not -MAX_INT <= value <= MAX_INT:
            raise PCGError("JSON_INTEGER_RANGE")
        return
    if isinstance(value, str):
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise PCGError("JSON_INVALID_UNICODE")
        return
    if isinstance(value, list):
        for item in value:
            validate_json(item, depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key or any(not 0x20 <= ord(c) <= 0x7E for c in key):
                raise PCGError("JSON_KEY", "nonempty printable ASCII object keys required")
            validate_json(item, depth + 1)
        return
    raise PCGError("JSON_TYPE", "floats and non-JSON objects are forbidden")


def canonical(value: Any) -> bytes:
    validate_json(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise PCGError("JSON_DUPLICATE_KEY", key)
        out[key] = value
    return out


def _no_float(_):
    raise PCGError("JSON_FLOAT")


def parse_json(data: bytes | str, max_bytes: int = MAX_PLAIN) -> Any:
    raw = data.encode("utf-8") if isinstance(data, str) else data
    if len(raw) > max_bytes:
        raise PCGError("JSON_TOO_LARGE")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_float=_no_float, parse_constant=_no_float)
    except PCGError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise PCGError("JSON_INVALID", str(exc)) from exc
    validate_json(value)
    return value


def parse_canonical(data: bytes, max_bytes: int = MAX_PLAIN) -> Any:
    value = parse_json(data, max_bytes)
    if canonical(value) != data:
        raise PCGError("NON_CANONICAL_JSON")
    return value


def hero_id_from_uid(technology: str, uid_hex: str) -> str:
    """UID bytes in RF/protocol order, never a reversed/integer-converted UID."""
    if technology not in ("nfc-a", "nfc-b", "nfc-f", "nfc-v"):
        raise PCGError("TAG_TECHNOLOGY")
    if not re.fullmatch(r"(?:[0-9A-Fa-f]{2}){1,16}", uid_hex):
        raise PCGError("TAG_UID")
    source = "pcg.hero.uid.v1\n" + technology + "\n" + uid_hex.upper()
    return "uid:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
