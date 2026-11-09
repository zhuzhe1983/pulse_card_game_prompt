"""PCSV v1 container and an in-memory raw dual-slot card fault model."""
from __future__ import annotations

import hashlib
import struct
import uuid
import zlib
from .common import PCGError, MAX_PLAIN, MAX_INT, canonical, parse_json
from .player import validate_snapshot

HEADER_BYTES = 96
SLOT_BYTES = 4096


def encode_container(snapshot, profile=1, codec=0, generation=1, max_bytes=None, committed=True):
    validate_snapshot(snapshot)
    if profile not in (1, 2) or codec not in (0, 1):
        raise PCGError("CARD_PROFILE_OR_CODEC")
    if not 0 <= generation <= 0xFFFFFFFF:
        raise PCGError("CARD_GENERATION_EXHAUSTED")
    plain = canonical(snapshot)
    if len(plain) > MAX_PLAIN:
        raise PCGError("SAVE_TOO_LARGE")
    stored = plain if codec == 0 else zlib.compress(plain, level=6)
    total = HEADER_BYTES + len(stored)
    if max_bytes is not None and total > max_bytes:
        raise PCGError("CARD_CAPACITY", f"need={total}, available={max_bytes}")
    if snapshot["save_schema_version"] != 1:
        raise PCGError("SAVE_SCHEMA_UNSUPPORTED")
    header = bytearray(HEADER_BYTES)
    header[0:4] = b"PCSV"
    struct.pack_into("<BBBBHHIII", header, 4, 1, profile, codec, 0, HEADER_BYTES,
                     snapshot["save_schema_version"], len(stored), len(plain), generation)
    header[24:40] = uuid.UUID(snapshot["snapshot_id"]).bytes
    header[40:72] = hashlib.sha256(plain).digest()
    struct.pack_into("<QQ", header, 72, snapshot["modified_at_ms"], snapshot["save_seq"])
    struct.pack_into("<I", header, 88, zlib.crc32(header[:88]) & 0xFFFFFFFF)
    header[92:96] = b"DONE" if committed else bytes(4)
    return bytes(header) + stored


def decode_container(blob, expected_profile=None):
    if len(blob) < HEADER_BYTES or blob[:4] != b"PCSV":
        raise PCGError("CARD_MAGIC")
    version, profile, codec, flags = struct.unpack_from("<BBBB", blob, 4)
    header_len, schema = struct.unpack_from("<HH", blob, 8)
    stored_len, plain_len, generation = struct.unpack_from("<III", blob, 12)
    modified_at_ms, save_seq = struct.unpack_from("<QQ", blob, 72)
    if version != 1 or header_len != HEADER_BYTES or profile not in (1, 2) or codec not in (0, 1) or flags != 0:
        raise PCGError("CARD_HEADER_UNSUPPORTED")
    if expected_profile is not None and profile != expected_profile:
        raise PCGError("CARD_PROFILE_MISMATCH")
    if blob[92:96] != b"DONE":
        raise PCGError("CARD_NOT_COMMITTED")
    if struct.unpack_from("<I", blob, 88)[0] != (zlib.crc32(blob[:88]) & 0xFFFFFFFF):
        raise PCGError("CARD_HEADER_CRC")
    if plain_len > MAX_PLAIN or stored_len > len(blob) - HEADER_BYTES or modified_at_ms > MAX_INT or save_seq > MAX_INT:
        raise PCGError("CARD_LENGTH_OR_RANGE")
    stored = blob[HEADER_BYTES:HEADER_BYTES + stored_len]
    if codec == 0:
        plain = stored
    else:
        try:
            dec = zlib.decompressobj()
            plain = dec.decompress(stored, MAX_PLAIN + 1)
            if len(plain) > MAX_PLAIN or dec.unconsumed_tail or not dec.eof or dec.unused_data:
                raise PCGError("CARD_COMPRESSION_LIMIT")
        except zlib.error as exc:
            raise PCGError("CARD_COMPRESSION") from exc
    if len(plain) != plain_len or hashlib.sha256(plain).digest() != blob[40:72]:
        raise PCGError("CARD_PAYLOAD_HASH")
    value = parse_json(plain)
    if not isinstance(value, dict):
        raise PCGError("SAVE_INVALID")
    if canonical(value) != plain:
        raise PCGError("CARD_NONCANONICAL")
    if str(uuid.UUID(bytes=blob[24:40])) != value.get("snapshot_id") or modified_at_ms != value.get("modified_at_ms") or save_seq != value.get("save_seq") or schema != value.get("save_schema_version"):
        raise PCGError("CARD_HEADER_PAYLOAD_MISMATCH")
    if schema == 1:
        validate_snapshot(value)
    return {"snapshot": value, "profile": profile, "codec": codec, "generation": generation,
            "plain_len": plain_len, "stored_len": stored_len, "payload_sha256": blob[40:72].hex(),
            "read_only": schema != 1}


def read_raw_dual(card_bytes):
    if len(card_bytes) != SLOT_BYTES * 2:
        raise PCGError("RAW_CARD_CAPACITY")
    valid = []
    for index in range(2):
        slot = card_bytes[index * SLOT_BYTES:(index + 1) * SLOT_BYTES]
        # A recognisable committed future format is not an ordinary damaged slot.
        # Refusing the whole read/write path preserves future data for a newer client.
        if (slot[:4] == b"PCSV" and slot[92:96] == b"DONE"
                and struct.unpack_from("<I", slot, 88)[0] == (zlib.crc32(slot[:88]) & 0xFFFFFFFF)):
            version, profile, codec, flags = struct.unpack_from("<BBBB", slot, 4)
            hlen, schema = struct.unpack_from("<HH", slot, 8)
            if version != 1 or profile != 2 or codec not in (0, 1) or flags != 0 or hlen != 96 or schema != 1:
                raise PCGError("FUTURE_CARD_READ_ONLY")
        try:
            parsed = decode_container(slot, 2)
            valid.append((index, parsed))
        except (PCGError, ValueError, KeyError, TypeError):
            pass
    if not valid:
        raise PCGError("RAW_NO_VALID_SLOT")
    if len(valid) == 2 and valid[0][1]["snapshot"]["player_id"] != valid[1][1]["snapshot"]["player_id"]:
        raise PCGError("RAW_PLAYER_CONFLICT")
    if (len(valid) == 2 and valid[0][1]["snapshot"]["snapshot_id"] == valid[1][1]["snapshot"]["snapshot_id"]
            and valid[0][1]["payload_sha256"] != valid[1][1]["payload_sha256"]):
        raise PCGError("RAW_SNAPSHOT_ID_CONFLICT")
    if len(valid) == 2 and valid[0][1]["generation"] == valid[1][1]["generation"]:
        if valid[0][1]["payload_sha256"] != valid[1][1]["payload_sha256"]:
            raise PCGError("RAW_EQUAL_GENERATION_CONFLICT")
    index, chosen = max(valid, key=lambda item: (item[1]["generation"], -item[0]))
    return {**chosen, "slot_index": index}


def raw_write_plan(card_bytes, snapshot, codec=1):
    """Operation ordering is normative; adapter write granularity may split writes."""
    if len(card_bytes) != SLOT_BYTES * 2:
        raise PCGError("RAW_CARD_CAPACITY")
    try:
        current = read_raw_dual(card_bytes)
        if current["read_only"]:
            raise PCGError("FUTURE_CARD_READ_ONLY")
        if current["snapshot"]["player_id"] != snapshot["player_id"]:
            raise PCGError("CARD_PLAYER_MISMATCH")
        target = 1 - current["slot_index"]
        generation = current["generation"] + 1
    except PCGError as exc:
        if exc.code != "RAW_NO_VALID_SLOT" or any(card_bytes):
            raise
        target, generation = 0, 1
    payload = encode_container(snapshot, 2, codec, generation, SLOT_BYTES)
    start = target * SLOT_BYTES
    return [
        {"offset": start + 92, "data": bytes(4), "verify_after": True, "stage": "invalidate"},
        {"offset": start + HEADER_BYTES, "data": payload[HEADER_BYTES:], "verify_after": True, "stage": "payload"},
        {"offset": start, "data": payload[:92], "verify_after": True, "stage": "header"},
        {"offset": start + 92, "data": b"DONE", "verify_after": True, "stage": "commit"},
    ]


def apply_raw_plan(card_bytes, operations, byte_budget=None):
    """Fault injection: stop after N written bytes. This is NOT a hardware driver."""
    out = bytearray(card_bytes)
    remaining = byte_budget
    for op in operations:
        count = len(op["data"]) if remaining is None else min(len(op["data"]), max(0, remaining))
        out[op["offset"]:op["offset"] + count] = op["data"][:count]
        if remaining is not None:
            remaining -= count
            if count < len(op["data"]) or remaining == 0:
                break
    return bytes(out)


def encode_ndef_single(container):
    """One long-form MIME NDEF record: MB=ME=1, SR=IL=0, TNF=0x02."""
    mime = b"application/vnd.pulsecard.save"
    return bytes([0xC2, len(mime)]) + struct.pack(">I", len(container)) + mime + container


def decode_ndef_single(message):
    mime = b"application/vnd.pulsecard.save"
    if len(message) < 6 or message[0] != 0xC2:
        raise PCGError("NDEF_PROFILE")
    type_len = message[1]
    payload_len = struct.unpack_from(">I", message, 2)[0]
    if message[6:6 + type_len] != mime or len(message) != 6 + type_len + payload_len:
        raise PCGError("NDEF_LENGTH_OR_TYPE")
    blob = message[6 + type_len:]
    parsed = decode_container(blob, expected_profile=1)
    if len(blob) != HEADER_BYTES + parsed["stored_len"]:
        raise PCGError("NDEF_LENGTH_OR_TYPE")
    return parsed
