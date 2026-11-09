"""PCG-F1 binary codec, bounded stream framing and in-memory reassembly oracle.

This is not a radio driver, authentication layer, full session manager or scheduler.
The embedding adapter must perform authentication, ACK transmission and retry timers.
"""
from __future__ import annotations

import hashlib
import math
import struct
import zlib
from .common import PCGError, canonical, parse_canonical

MAX_ENVELOPE = 8192
HEADER = 24
DATA, ACK, OPEN, ACCEPT = 1, 2, 16, 17


def encode_frame(kind, link_id, transfer_id, total_len, frag_index, frag_count, payload, mtu=128):
    if mtu not in (128, 200):
        raise PCGError("FRAME_MTU")
    if not isinstance(payload, bytes):
        raise PCGError("FRAME_PAYLOAD")
    try:
        prefix = struct.pack(">2sBBIIHBBHH", b"PC", 1, kind, link_id, transfer_id,
                             total_len, frag_index, frag_count, len(payload), 0)
    except struct.error as exc:
        raise PCGError("FRAME_RANGE") from exc
    blob = prefix + struct.pack(">I", zlib.crc32(prefix + payload) & 0xFFFFFFFF) + payload
    decode_frame(blob, mtu)
    return blob


def decode_frame(blob, mtu=128):
    if mtu not in (128, 200) or not HEADER <= len(blob) <= mtu:
        raise PCGError("FRAME_LENGTH")
    magic, version, kind, link_id, transfer_id, total_len, index, count, length, flags = struct.unpack(">2sBBIIHBBHH", blob[:20])
    if magic != b"PC" or version != 1 or flags != 0 or kind not in (DATA, ACK, OPEN, ACCEPT) or link_id == 0:
        raise PCGError("FRAME_HEADER")
    if len(blob) != HEADER + length:
        raise PCGError("FRAME_LENGTH")
    payload = blob[HEADER:]
    if struct.unpack(">I", blob[20:24])[0] != (zlib.crc32(blob[:20] + payload) & 0xFFFFFFFF):
        raise PCGError("FRAME_CRC")
    if kind in (OPEN, ACCEPT):
        if any((transfer_id, total_len, index, count)) or length != 8:
            raise PCGError("FRAME_CONTROL")
        advertised_mtu, envelope_limit, rto = struct.unpack(">HHI", payload)
        if advertised_mtu not in (128, 200) or envelope_limit != 8192 or not 1000 <= rto <= 60000:
            raise PCGError("FRAME_CONTROL")
    else:
        expected_count = math.ceil(total_len / (mtu - HEADER))
        if not 1 <= transfer_id <= 0xFFFFFFFF or not 1 <= total_len <= MAX_ENVELOPE or not 1 <= count <= 128 or count != expected_count:
            raise PCGError("FRAME_FRAGMENT")
        if kind == DATA:
            expected_length = min(mtu - HEADER, total_len - index * (mtu - HEADER))
            if not 0 <= index < count or length != expected_length:
                raise PCGError("FRAME_FRAGMENT")
        elif index != 0 or length != 16 or any(payload[i // 8] & (1 << (i % 8)) for i in range(count, 128)):
            raise PCGError("FRAME_ACK")
    return {"kind": kind, "link_id": link_id, "transfer_id": transfer_id, "total_len": total_len,
            "frag_index": index, "frag_count": count, "payload": payload}


def fragment(envelope_bytes, link_id, transfer_id, mtu=128):
    if mtu not in (128, 200):
        raise PCGError("FRAME_MTU")
    if not 1 <= len(envelope_bytes) <= MAX_ENVELOPE:
        raise PCGError("ENVELOPE_LENGTH")
    capacity = mtu - HEADER
    count = math.ceil(len(envelope_bytes) / capacity)
    return [encode_frame(DATA, link_id, transfer_id, len(envelope_bytes), i, count,
                         envelope_bytes[i * capacity:(i + 1) * capacity], mtu) for i in range(count)]


def bitmap(indices):
    out = bytearray(16)
    for i in indices:
        if not 0 <= i < 128:
            raise PCGError("BITMAP_INDEX")
        out[i // 8] |= 1 << (i % 8)
    return bytes(out)


def control_frame(kind, link_id, frame_mtu=128, rto_ms=1000):
    return encode_frame(kind, link_id, 0, 0, 0, 0, struct.pack(">HHI", frame_mtu, MAX_ENVELOPE, rto_ms), 128)


def stream_encode(value):
    raw = canonical(value)
    if not 1 <= len(raw) <= MAX_ENVELOPE:
        raise PCGError("ENVELOPE_LENGTH")
    return struct.pack(">I", len(raw)) + raw


class StreamDecoder:
    def __init__(self):
        self.buffer = bytearray()
        self.length = None

    def feed(self, data):
        # Consume incrementally, including arbitrarily large batches of small messages.
        out, offset = [], 0
        while offset < len(data):
            needed = (4 if self.length is None else self.length) - len(self.buffer)
            take = min(needed, len(data) - offset)
            self.buffer.extend(data[offset:offset + take])
            offset += take
            if self.length is None and len(self.buffer) == 4:
                self.length = int.from_bytes(self.buffer, "big")
                self.buffer.clear()
                if not 1 <= self.length <= MAX_ENVELOPE:
                    raise PCGError("ENVELOPE_LENGTH")
            elif self.length is not None and len(self.buffer) == self.length:
                out.append(bytes(self.buffer))
                self.buffer.clear()
                self.length = None
        return out


class Reassembler:
    def __init__(self, link_id, mtu=128, rto_ms=1000):
        if not 1 <= link_id <= 0xFFFFFFFF or mtu not in (128, 200) or not 1000 <= rto_ms <= 60000:
            raise PCGError("LINK_PARAMETERS")
        self.link_id, self.mtu, self.rto_ms = link_id, mtu, rto_ms
        self.next_id, self.active, self.completed = 1, None, {}

    def expire(self, now_ms):
        retention = max(60000, 6 * self.rto_ms)
        self.completed = {k: v for k, v in self.completed.items() if now_ms - v["completed_at"] <= retention}
        if self.active is not None:
            a = self.active
            if now_ms - a["last_new"] > 6 * self.rto_ms or now_ms - a["started"] > (a["count"] + 6) * 5 * self.rto_ms:
                self.active = None
                raise PCGError("TRANSFER_TIMEOUT")

    def receive(self, blob, now_ms=0):
        self.expire(now_ms)
        f = decode_frame(blob, self.mtu)
        if f["kind"] != DATA or f["link_id"] != self.link_id:
            raise PCGError("FRAME_LINK_OR_KIND")
        tid, index = f["transfer_id"], f["frag_index"]
        if tid < self.next_id:
            old = self.completed.get(tid)
            if old is None:
                return {"envelope": None, "ack": None, "duplicate": True}
            if old["total"] != f["total_len"] or old["count"] != f["frag_count"] or old["hashes"][index] != hashlib.sha256(f["payload"]).digest():
                raise PCGError("FRAGMENT_CONFLICT")
            ack = encode_frame(ACK, self.link_id, tid, old["total"], 0, old["count"], bitmap(range(old["count"])), self.mtu)
            return {"envelope": None, "ack": ack, "duplicate": True}
        if tid != self.next_id:
            raise PCGError("TRANSFER_ID_GAP")
        if self.active is None:
            self.active = {"total": f["total_len"], "count": f["frag_count"], "parts": {}, "started": now_ms, "last_new": now_ms}
        a = self.active
        if a["total"] != f["total_len"] or a["count"] != f["frag_count"]:
            raise PCGError("FRAGMENT_CONFLICT")
        duplicate = index in a["parts"]
        if duplicate and a["parts"][index] != f["payload"]:
            raise PCGError("FRAGMENT_CONFLICT")
        if not duplicate:
            a["parts"][index] = f["payload"]
            a["last_new"] = now_ms
        ack = encode_frame(ACK, self.link_id, tid, a["total"], 0, a["count"], bitmap(a["parts"]), self.mtu)
        envelope = None
        if len(a["parts"]) == a["count"]:
            envelope = b"".join(a["parts"][i] for i in range(a["count"]))
            self.completed[tid] = {"total": a["total"], "count": a["count"],
                "hashes": [hashlib.sha256(a["parts"][i]).digest() for i in range(a["count"])], "completed_at": now_ms}
            while len(self.completed) > 8:
                del self.completed[min(self.completed)]
            self.next_id += 1
            self.active = None
        return {"envelope": envelope, "ack": ack, "duplicate": duplicate}


def parse_envelope(raw):
    """Canonical parse only. Caller also applies envelope JSON Schema and session ACL."""
    return parse_canonical(raw, MAX_ENVELOPE)
