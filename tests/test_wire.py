"""PCG-F1/stream conformance tests. Standard library only; no hardware required.

Run from the project root:
    python -m unittest discover -s tests -p test_wire.py -v
or run this file directly from any working directory.

Published fixture bytes are the oracle. Tests never regenerate fixture files.
Authentication, radio drivers and the sender's retry scheduler are outside wire.py.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest
import zlib


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))

from reference.common import PCGError, canonical  # noqa: E402
from reference import wire  # noqa: E402


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def with_valid_crc(blob):
    """Repair CRC after a deliberate mutation so semantic checks are exercised."""
    out = bytearray(blob)
    crc = zlib.crc32(out[:20] + out[24:]) & 0xFFFFFFFF
    out[20:24] = crc.to_bytes(4, "big")
    return bytes(out)


class WireConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden = load_json("fixtures/wire_golden.json")
        cls.examples = load_json("examples/wire_examples.json")
        cls.documented = cls.examples["binary_frame_vector"]
        cls.raw = bytes.fromhex(cls.golden["canonical_utf8_hex"])
        cls.frames = [bytes.fromhex(x) for x in cls.golden["frames_hex"]]

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(PCGError) as raised:
            function(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)

    def new_receiver(self):
        return wire.Reassembler(self.golden["link_id"], self.golden["mtu"])

    def test_wire_golden_canonical_and_stream_bytes(self):
        g = self.golden
        self.assertEqual(canonical(g["envelope"]), self.raw)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), g["canonical_sha256"])
        self.assertEqual(wire.parse_envelope(self.raw), g["envelope"])
        expected_stream = bytes.fromhex(g["stream_hex"])
        self.assertEqual(wire.stream_encode(g["envelope"]), expected_stream)
        self.assertEqual(int.from_bytes(expected_stream[:4], "big"), len(self.raw))
        self.assertEqual(expected_stream[4:], self.raw)

    def test_wire_golden_frames_exact(self):
        g = self.golden
        self.assertEqual(
            wire.fragment(self.raw, g["link_id"], g["transfer_id"], g["mtu"]),
            self.frames,
        )
        payloads = []
        for index, blob in enumerate(self.frames):
            with self.subTest(index=index):
                frame = wire.decode_frame(blob, g["mtu"])
                self.assertEqual(frame["kind"], wire.DATA)
                self.assertEqual(frame["link_id"], g["link_id"])
                self.assertEqual(frame["transfer_id"], g["transfer_id"])
                self.assertEqual(frame["total_len"], len(self.raw))
                self.assertEqual(frame["frag_index"], index)
                self.assertEqual(frame["frag_count"], len(self.frames))
                self.assertEqual(wire.encode_frame(**frame, mtu=g["mtu"]), blob)
                self.assertEqual(
                    int.from_bytes(blob[20:24], "big"),
                    zlib.crc32(blob[:20] + blob[24:]) & 0xFFFFFFFF,
                )
                payloads.append(frame["payload"])
        self.assertEqual(b"".join(payloads), self.raw)
        self.assertEqual(zlib.crc32(b"123456789") & 0xFFFFFFFF, 0xCBF43926)

    def test_wire_golden_control_frames_exact(self):
        for name, kind in (("open_hex", wire.OPEN), ("accept_hex", wire.ACCEPT)):
            with self.subTest(kind=kind):
                blob = bytes.fromhex(self.golden[name])
                self.assertEqual(
                    wire.control_frame(kind, self.golden["link_id"], self.golden["mtu"], 1000),
                    blob,
                )
                frame = wire.decode_frame(blob, self.golden["mtu"])
                self.assertEqual(frame["kind"], kind)
                self.assertEqual(frame["transfer_id"], 0)
                self.assertEqual(frame["total_len"], 0)
                self.assertEqual(frame["frag_index"], 0)
                self.assertEqual(frame["frag_count"], 0)
                self.assertEqual(struct.unpack(">HHI", frame["payload"]), (128, 8192, 1000))

    def test_documented_frame_vector_exact(self):
        v = self.documented
        raw = canonical(v["envelope"])
        self.assertEqual(len(raw), v["canonical_byte_length"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), v["canonical_sha256"])
        self.assertEqual(
            [x.hex() for x in wire.fragment(raw, v["link_id"], v["transfer_id"], v["mtu"])],
            [x["hex"] for x in v["data_frames"]],
        )
        records = [v["open"], v["accept"], *v["data_frames"], v["complete_ack"]]
        for record in records:
            expected = record["decoded"]
            with self.subTest(kind=expected["kind"], index=expected["frag_index"]):
                blob = bytes.fromhex(record["hex"])
                self.assertEqual(len(blob), record["length"])
                decoded = wire.decode_frame(blob, v["mtu"])
                self.assertEqual(decoded["payload"].hex(), expected["payload_hex"])
                for field in ("kind", "link_id", "transfer_id", "total_len", "frag_index", "frag_count"):
                    self.assertEqual(decoded[field], expected[field])
                self.assertEqual(blob[:2], expected["magic"].encode("ascii"))
                self.assertEqual(blob[2], expected["frame_version"])
                self.assertEqual(len(decoded["payload"]), expected["payload_len"])
                self.assertEqual(int.from_bytes(blob[18:20], "big"), expected["flags"])
                self.assertEqual(int.from_bytes(blob[20:24], "big"), expected["crc32"])
                self.assertEqual(wire.encode_frame(**decoded, mtu=v["mtu"]), blob)
        self.assertEqual(wire.stream_encode(v["envelope"]).hex(), v["stream_message_hex"])
        self.assertEqual(len(raw).to_bytes(4, "big").hex(), v["stream_length_prefix_hex"])

    def test_documented_canonical_vectors(self):
        for index, vector in enumerate(self.examples["canonical_vectors"]):
            with self.subTest(index=index):
                raw = canonical(vector["value"])
                self.assertEqual(raw.decode("utf-8"), vector["canonical_utf8"])
                self.assertEqual(raw.hex(), vector["canonical_hex"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), vector["sha256"])

    def test_documented_canonical_rejections(self):
        vectors = [x for x in self.examples["negative_tests"] if "input_utf8" in x]
        self.assertTrue(vectors, "canonical rejection vectors must not disappear")
        for vector in vectors:
            with self.subTest(name=vector["name"]):
                self.assert_code(
                    vector["expected_error"], wire.parse_envelope,
                    vector["input_utf8"].encode("utf-8"),
                )

    def test_out_of_order_and_duplicate_deliver_exactly_once(self):
        receiver = self.new_receiver()
        order = list(reversed(range(len(self.frames))))
        order = [order[0], order[0], *order[1:], order[-1], order[0]]
        deliveries, seen = [], set()
        for now_ms, index in enumerate(order):
            was_duplicate = index in seen
            result = receiver.receive(self.frames[index], now_ms)
            self.assertEqual(result["duplicate"], was_duplicate)
            seen.add(index)
            ack = wire.decode_frame(result["ack"], self.golden["mtu"])
            expected_bitmap = sum(1 << i for i in seen).to_bytes(16, "little")
            self.assertEqual(ack["payload"], expected_bitmap)
            if result["envelope"] is not None:
                deliveries.append(result["envelope"])
        self.assertEqual(deliveries, [self.raw])

    def test_lost_final_ack_duplicate_returns_published_complete_ack(self):
        v = self.documented
        receiver = wire.Reassembler(v["link_id"], v["mtu"])
        frames = [bytes.fromhex(x["hex"]) for x in v["data_frames"]]
        deliveries = []
        for now_ms, index in enumerate(v["receive_order_for_out_of_order_test"]):
            result = receiver.receive(frames[index], now_ms)
            if result["envelope"] is not None:
                deliveries.append(result["envelope"])
        self.assertEqual(deliveries, [canonical(v["envelope"])])
        self.assertEqual(result["ack"].hex(), v["complete_ack"]["hex"])
        retry = receiver.receive(frames[-1], 100)
        self.assertIsNone(retry["envelope"])
        self.assertTrue(retry["duplicate"])
        self.assertEqual(retry["ack"].hex(), v["complete_ack"]["hex"])

    def test_bad_crc_does_not_allocate_reassembly(self):
        damaged = bytearray(self.frames[0])
        damaged[-1] ^= 1
        receiver = self.new_receiver()
        self.assert_code("FRAME_CRC", receiver.receive, bytes(damaged), 0)
        self.assertIsNone(receiver.active)
        self.assertEqual(receiver.next_id, 1)

    def test_active_duplicate_payload_conflict(self):
        receiver = self.new_receiver()
        receiver.receive(self.frames[0], 0)
        changed = bytearray(self.frames[0])
        changed[-1] ^= 1
        changed = with_valid_crc(changed)
        wire.decode_frame(changed, self.golden["mtu"])
        self.assert_code("FRAGMENT_CONFLICT", receiver.receive, changed, 1)

    def test_active_transfer_metadata_conflict(self):
        receiver = self.new_receiver()
        receiver.receive(self.frames[0], 0)
        changed = bytearray(self.frames[1])
        struct.pack_into(">H", changed, 12, len(self.raw) + 1)
        changed = with_valid_crc(changed)
        wire.decode_frame(changed, self.golden["mtu"])
        self.assert_code("FRAGMENT_CONFLICT", receiver.receive, changed, 1)

    def test_completed_duplicate_payload_conflict(self):
        receiver = self.new_receiver()
        for now_ms, frame in enumerate(self.frames):
            receiver.receive(frame, now_ms)
        changed = bytearray(self.frames[-1])
        changed[-1] ^= 1
        self.assert_code("FRAGMENT_CONFLICT", receiver.receive, with_valid_crc(changed), 100)

    def test_maximum_envelope_uses_79_or_47_fragments(self):
        raw = b"x" * 8192
        for mtu, expected_count, last_payload_length in ((128, 79, 80), (200, 47, 96)):
            with self.subTest(mtu=mtu):
                frames = wire.fragment(raw, 7, 1, mtu)
                self.assertEqual(len(frames), expected_count)
                self.assertEqual(len(frames[-1]), 24 + last_payload_length)
                self.assertTrue(all(len(frame) == mtu for frame in frames[:-1]))
                receiver = wire.Reassembler(7, mtu)
                deliveries = []
                for now_ms, blob in enumerate(reversed(frames)):
                    result = receiver.receive(blob, now_ms)
                    if result["envelope"] is not None:
                        deliveries.append(result["envelope"])
                self.assertEqual(deliveries, [raw])

    def test_envelope_length_and_fragment_boundary_limits(self):
        for size in (0, 8193):
            with self.subTest(size=size):
                self.assert_code("ENVELOPE_LENGTH", wire.fragment, b"x" * size, 7, 1)
        for mtu, capacity in ((128, 104), (200, 176)):
            for size, count in ((1, 1), (capacity, 1), (capacity + 1, 2)):
                with self.subTest(mtu=mtu, size=size):
                    frames = wire.fragment(b"x" * size, 7, 1, mtu)
                    self.assertEqual(len(frames), count)
                    self.assertEqual(b"".join(wire.decode_frame(f, mtu)["payload"] for f in frames), b"x" * size)

    def test_invalid_mtu_is_rejected_before_fragment_arithmetic(self):
        for mtu in (0, 16, 23, 24, 25, 127, 129, 201):
            with self.subTest(mtu=mtu):
                self.assert_code("FRAME_MTU", wire.fragment, b"a", 7, 1, mtu)

    def test_ack_spare_bits_rejected_even_with_correct_crc(self):
        v = self.documented
        good = bytes.fromhex(v["complete_ack"]["hex"])
        self.assertEqual(wire.decode_frame(good, v["mtu"])["frag_count"], 2)
        for byte_offset, bit in ((24, 0x04), (39, 0x80)):
            with self.subTest(byte_offset=byte_offset, bit=bit):
                bad = bytearray(good)
                bad[byte_offset] |= bit
                self.assert_code("FRAME_ACK", wire.decode_frame, with_valid_crc(bad), v["mtu"])

    def test_ack_bitmap_bit_order_and_index_bounds(self):
        expected = bytes([0x81, 0x01] + [0] * 7 + [0x40] + [0] * 5 + [0x80])
        self.assertEqual(wire.bitmap([0, 7, 8, 78, 127]), expected)
        for index in (-1, 128):
            with self.subTest(index=index):
                self.assert_code("BITMAP_INDEX", wire.bitmap, [index])

    def test_stream_one_byte_reads_of_concatenated_messages(self):
        streams = [bytes.fromhex(self.golden["stream_hex"]), bytes.fromhex(self.documented["stream_message_hex"])]
        decoder = wire.StreamDecoder()
        self.assertEqual(decoder.feed(b""), [])
        messages = []
        for byte in b"".join(streams):
            messages.extend(decoder.feed(bytes([byte])))
        self.assertEqual(messages, [self.raw, canonical(self.documented["envelope"])])
        self.assertEqual(decoder.buffer, bytearray())
        self.assertIsNone(decoder.length)

    def test_stream_batch_limit_is_per_message(self):
        decoder = wire.StreamDecoder()
        batch = bytes.fromhex(self.golden["stream_hex"]) * 40
        self.assertGreater(len(batch), 8192)
        self.assertEqual(decoder.feed(batch), [self.raw] * 40)

    def test_stream_rejects_zero_and_oversized_length_headers(self):
        for length in (0, 8193, 0xFFFFFFFF):
            with self.subTest(length=length):
                prefix = length.to_bytes(4, "big")
                decoder = wire.StreamDecoder()
                self.assertEqual(decoder.feed(prefix[:1]), [])
                self.assert_code("ENVELOPE_LENGTH", decoder.feed, prefix[1:])

    def test_idle_timeout_is_extended_by_new_fragments_only(self):
        receiver = self.new_receiver()
        receiver.receive(self.frames[0], 0)
        receiver.receive(self.frames[1], 5000)
        self.assertTrue(receiver.receive(self.frames[1], 10000)["duplicate"])
        receiver.expire(11000)  # Exactly 6RTO is allowed; "exceeds" is strict.
        self.assert_code("TRANSFER_TIMEOUT", receiver.expire, 11001)
        self.assertIsNone(receiver.active)

    def test_hard_deadline_rejects_regular_slow_progress(self):
        frames = wire.fragment(b"x" * 8192, 7, 1, 128)
        receiver = wire.Reassembler(7, 128, 1000)
        # 73 new fragments arrive less than 6RTO apart, but not all 79 finish.
        # The hard deadline is (79 + 6) * 5 * 1000 = 425000ms.
        for index in range(73):
            receiver.receive(frames[index], index * 5900)
        self.assert_code("TRANSFER_TIMEOUT", receiver.receive, frames[73], 73 * 5900)

    def test_transfer_id_gap_before_and_during_reassembly(self):
        ahead = wire.fragment(self.raw, self.golden["link_id"], 2, self.golden["mtu"])[0]
        self.assert_code("TRANSFER_ID_GAP", self.new_receiver().receive, ahead, 0)
        receiver = self.new_receiver()
        receiver.receive(self.frames[0], 0)
        self.assert_code("TRANSFER_ID_GAP", receiver.receive, ahead, 1)

    def test_wrong_link_is_rejected(self):
        wrong_link = wire.fragment(self.raw, self.golden["link_id"] + 1, 1, self.golden["mtu"])[0]
        self.assert_code("FRAME_LINK_OR_KIND", self.new_receiver().receive, wrong_link, 0)

    def test_completed_cache_capacity_and_ttl(self):
        receiver = wire.Reassembler(7)
        frames = {tid: wire.fragment(b"x", 7, tid)[0] for tid in range(1, 10)}
        for tid in range(1, 10):
            self.assertEqual(receiver.receive(frames[tid], tid)["envelope"], b"x")
        # Capacity wins over TTL: the ninth completion evicts the oldest.
        self.assertEqual(receiver.receive(frames[1], 10), {"envelope": None, "ack": None, "duplicate": True})
        self.assertIsNotNone(receiver.receive(frames[2], 11)["ack"])
        self.assertIsNotNone(receiver.receive(frames[9], 60009)["ack"])
        self.assertEqual(receiver.receive(frames[9], 60010), {"envelope": None, "ack": None, "duplicate": True})


if __name__ == "__main__":
    unittest.main(verbosity=2)
