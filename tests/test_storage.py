"""Storage/claim interoperability and recovery checks; stdlib only.

These tests exercise the reference byte-interruption model. They do not certify
physical NFC write granularity, RF power-loss behavior, or an OS reader driver.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
import unittest
import uuid
import zlib

from reference.common import PCGError, canonical, digest
from reference.nfc_storage import (
    HEADER_BYTES,
    SLOT_BYTES,
    apply_raw_plan,
    decode_container,
    decode_ndef_single,
    encode_container,
    encode_ndef_single,
    raw_write_plan,
    read_raw_dual,
)
from reference.player import (
    bump_snapshot,
    claim_hero,
    redeem_ink_skin,
    select_login_snapshot,
    validate_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]


def read_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def snapshot_uuid(number):
    return f"60000000-0000-4000-8000-{number:012x}"


def pad_slot(container):
    if len(container) > SLOT_BYTES:
        raise AssertionError("test setup would overflow a raw slot")
    return container + bytes(SLOT_BYTES - len(container))


def patch_header(container, offset, replacement):
    """Make an intentionally changed, CRC-valid header for a negative test."""
    result = bytearray(container)
    result[offset:offset + len(replacement)] = replacement
    struct.pack_into("<I", result, 88, zlib.crc32(result[:88]) & 0xFFFFFFFF)
    return bytes(result)


def replace_plain_payload(container, value):
    """Bypass the encoder's input gate to model a bad/unknown external card.

    The payload remains canonical and hash-valid, so the parser must check the
    schema/root instead of relying only on CRC or SHA-256.
    """
    plain = canonical(value)
    header = bytearray(container[:HEADER_BYTES])
    header[6] = 0
    struct.pack_into("<II", header, 12, len(plain), len(plain))
    header[40:72] = hashlib.sha256(plain).digest()
    if isinstance(value, dict):
        if "save_schema_version" in value:
            struct.pack_into("<H", header, 10, value["save_schema_version"])
        if "snapshot_id" in value:
            header[24:40] = uuid.UUID(value["snapshot_id"]).bytes
        if "modified_at_ms" in value and "save_seq" in value:
            struct.pack_into("<QQ", header, 72, value["modified_at_ms"], value["save_seq"])
    struct.pack_into("<I", header, 88, zlib.crc32(header[:88]) & 0xFFFFFFFF)
    return bytes(header) + plain


class StorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = read_json("fixtures/storage_vectors.json")
        cls.draw = read_json("fixtures/draw_vectors.json")
        cls.initial = read_json("examples/player_initial.json")
        cls.saved = cls.storage["snapshot"]
        cls.pack = read_json("content/core_pack.json")

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(PCGError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def child(self, original, number):
        changed = deepcopy(original)
        changed["nickname"] = f"revision {number}"
        return bump_snapshot(
            original, changed, self.draw["device_id"], snapshot_uuid(number),
            original["modified_at_ms"] + 1,
        )

    def two_slot_card(self, first, second, first_generation=1, second_generation=2):
        return (
            pad_slot(encode_container(first, profile=2, codec=0, generation=first_generation))
            + pad_slot(encode_container(second, profile=2, codec=0, generation=second_generation))
        )

    def test_codec0_matches_frozen_hex_hash_and_binary(self):
        expected = bytes.fromhex(self.storage["codec0_container_hex"])
        encoded = encode_container(
            self.saved, profile=1, codec=0,
            generation=self.storage["codec0_generation"],
        )
        self.assertEqual(encoded, expected)
        self.assertEqual(encoded, (ROOT / "fixtures/player_card_codec0.bin").read_bytes())
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), self.storage["codec0_container_sha256"])
        parsed = decode_container(expected, expected_profile=1)
        self.assertEqual(parsed["snapshot"], self.saved)
        self.assertEqual(parsed["payload_sha256"], self.storage["snapshot_hash"])

    def test_ndef_matches_frozen_vector_and_binary(self):
        container = bytes.fromhex(self.storage["codec0_container_hex"])
        expected = bytes.fromhex(self.storage["ndef_message_hex"])
        self.assertEqual(encode_ndef_single(container), expected)
        self.assertEqual(expected, (ROOT / "fixtures/player_card_ndef.bin").read_bytes())
        self.assertEqual(decode_ndef_single(expected)["snapshot"], self.saved)

    def test_zlib_and_ndef_round_trip(self):
        for snapshot in (self.initial, self.saved):
            for codec in (0, 1):
                with self.subTest(snapshot=snapshot["snapshot_id"], codec=codec):
                    original = deepcopy(snapshot)
                    container = encode_container(snapshot, profile=1, codec=codec, generation=7)
                    parsed = decode_ndef_single(encode_ndef_single(container))
                    self.assertEqual(parsed["snapshot"], original)
                    self.assertEqual(parsed["payload_sha256"], digest(original))
                    self.assertEqual(parsed["generation"], 7)
                    self.assertEqual(parsed["codec"], codec)
                    self.assertEqual(snapshot, original)

    def test_header_offsets_crc_and_ndef_overhead(self):
        blob = bytes.fromhex(self.storage["codec0_container_hex"])
        plain = canonical(self.saved)
        self.assertEqual(HEADER_BYTES, 96)
        self.assertEqual(blob[:4], b"PCSV")
        self.assertEqual(blob[4:8], bytes((1, 1, 0, 0)))
        self.assertEqual(struct.unpack_from("<HH", blob, 8), (96, 1))
        self.assertEqual(struct.unpack_from("<II", blob, 12), (len(plain), len(plain)))
        self.assertEqual(blob[24:40], uuid.UUID(self.saved["snapshot_id"]).bytes)
        self.assertEqual(blob[40:72], hashlib.sha256(plain).digest())
        self.assertEqual(
            struct.unpack_from("<QQ", blob, 72),
            (self.saved["modified_at_ms"], self.saved["save_seq"]),
        )
        self.assertEqual(struct.unpack_from("<I", blob, 88)[0], zlib.crc32(blob[:88]) & 0xFFFFFFFF)
        self.assertEqual(blob[92:96], b"DONE")
        self.assertEqual(blob[96:], plain)
        ndef = encode_ndef_single(blob)
        self.assertEqual(ndef[:2], bytes((0xC2, 30)))
        self.assertEqual(len(ndef) - len(plain), 132)
        self.assertEqual(self.storage["header_size"], 96)
        self.assertEqual(self.storage["ndef_overhead"], 132)

    def test_corrupted_header_crc_and_uncommitted_marker_are_rejected(self):
        blob = bytearray(bytes.fromhex(self.storage["codec0_container_hex"]))
        blob[20] ^= 1
        self.assert_code("CARD_HEADER_CRC", decode_container, bytes(blob))
        blob = bytearray(bytes.fromhex(self.storage["codec0_container_hex"]))
        blob[92:96] = bytes(4)
        self.assert_code("CARD_NOT_COMMITTED", decode_container, bytes(blob))

    def test_container_capacity_exact_fit_and_one_byte_short(self):
        for codec in (0, 1):
            with self.subTest(codec=codec):
                blob = encode_container(self.saved, codec=codec)
                self.assertEqual(encode_container(self.saved, codec=codec, max_bytes=len(blob)), blob)
                self.assert_code(
                    "CARD_CAPACITY", encode_container, self.saved,
                    codec=codec, max_bytes=len(blob) - 1,
                )

    def test_oversized_raw_save_refuses_without_changing_card_or_snapshot(self):
        card = self.two_slot_card(self.initial, self.saved)
        large = self.child(self.saved, 20)
        large["extensions"]["capacity_probe"] = "x" * 4096
        before = deepcopy(large)
        self.assert_code("CARD_CAPACITY", raw_write_plan, card, large, codec=0)
        self.assertEqual(large, before)
        self.assertEqual(read_raw_dual(card)["snapshot"], self.saved)

    def test_raw_fixture_selects_frozen_slot_and_generation(self):
        card = (ROOT / "fixtures/player_card_raw_dual.bin").read_bytes()
        self.assertEqual(len(card), 8192)
        self.assertEqual(SLOT_BYTES, 4096)
        parsed = read_raw_dual(card)
        self.assertEqual(parsed["generation"], self.storage["raw_dual_generation"])
        self.assertEqual(parsed["slot_index"], self.storage["raw_dual_selected_slot"])
        self.assertEqual(parsed["snapshot"], self.saved)

    def test_every_raw_rewrite_byte_cut_preserves_old_or_complete_new(self):
        second = self.child(self.saved, 21)
        third = self.child(second, 22)
        cases = [
            (self.two_slot_card(self.initial, self.saved), self.saved, second, 1, 3),
            (self.two_slot_card(second, self.saved, 3, 2), second, third, 0, 4),
        ]
        for codec in (0, 1):
            for card, old, new, active_slot, expected_generation in cases:
                plan = raw_write_plan(card, new, codec=codec)
                total = sum(len(op["data"]) for op in plan)
                active_start = active_slot * SLOT_BYTES
                active_bytes = card[active_start:active_start + SLOT_BYTES]
                for budget in range(total + 1):
                    with self.subTest(codec=codec, active_slot=active_slot, written_bytes=budget):
                        interrupted = apply_raw_plan(card, plan, byte_budget=budget)
                        self.assertEqual(interrupted[active_start:active_start + SLOT_BYTES], active_bytes)
                        parsed = read_raw_dual(interrupted)
                        self.assertIn(digest(parsed["snapshot"]), (digest(old), digest(new)))
                        if budget < total:
                            self.assertEqual(parsed["snapshot"], old)
                        else:
                            self.assertEqual(parsed["snapshot"], new)
                            self.assertEqual(parsed["generation"], expected_generation)
                self.assertEqual(read_raw_dual(apply_raw_plan(card, plan))["snapshot"], new)

    def test_first_raw_write_is_unreadable_until_complete_commit(self):
        empty = bytes(8192)
        plan = raw_write_plan(empty, self.initial, codec=1)
        total = sum(len(op["data"]) for op in plan)
        for budget in range(total):
            with self.subTest(written_bytes=budget):
                partial = apply_raw_plan(empty, plan, byte_budget=budget)
                self.assert_code("RAW_NO_VALID_SLOT", read_raw_dual, partial)
        finished = read_raw_dual(apply_raw_plan(empty, plan, byte_budget=total))
        self.assertEqual(finished["snapshot"], self.initial)
        self.assertEqual((finished["slot_index"], finished["generation"]), (0, 1))

    def test_bad_new_payload_falls_back_to_old_valid_slot(self):
        old = pad_slot(encode_container(self.initial, profile=2, generation=1))
        new = encode_container(self.saved, profile=2, generation=2)
        for position in (96, 96 + (len(new) - 96) // 2, len(new) - 1):
            with self.subTest(corrupted_byte=position):
                bad = bytearray(new)
                bad[position] ^= 1
                parsed = read_raw_dual(old + pad_slot(bytes(bad)))
                self.assertEqual(parsed["snapshot"], self.initial)
                self.assertEqual(parsed["slot_index"], 0)

    def test_crc_valid_future_headers_block_read_and_overwrite(self):
        old = pad_slot(encode_container(self.initial, profile=2, generation=1))
        new = encode_container(self.saved, profile=2, generation=2)
        changes = {
            "container_version": (4, b"\x02"),
            "storage_profile": (5, b"\x03"),
            "codec": (6, b"\x02"),
            "flags": (7, b"\x01"),
            "header_size": (8, struct.pack("<H", 100)),
            "schema": (10, struct.pack("<H", 2)),
        }
        for name, (offset, value) in changes.items():
            with self.subTest(future_field=name):
                card = old + pad_slot(patch_header(new, offset, value))
                self.assert_code("FUTURE_CARD_READ_ONLY", read_raw_dual, card)
                self.assert_code("FUTURE_CARD_READ_ONLY", raw_write_plan, card, self.saved)

    def test_corrupted_or_uncommitted_future_header_can_fall_back(self):
        old = pad_slot(encode_container(self.initial, profile=2, generation=1))
        new = encode_container(self.saved, profile=2, generation=2)
        bad_crc = bytearray(new)
        bad_crc[4] = 2
        uncommitted = bytearray(patch_header(new, 4, b"\x02"))
        uncommitted[92:96] = bytes(4)
        for label, bad in (("crc", bad_crc), ("marker", uncommitted)):
            with self.subTest(damage=label):
                self.assertEqual(read_raw_dual(old + pad_slot(bytes(bad)))["snapshot"], self.initial)

    def test_same_snapshot_id_with_different_hash_is_a_conflict(self):
        changed = deepcopy(self.initial)
        changed["wallet"]["shards"] = 10
        card = self.two_slot_card(self.initial, changed)
        self.assert_code("RAW_SNAPSHOT_ID_CONFLICT", read_raw_dual, card)
        self.assert_code("RAW_SNAPSHOT_ID_CONFLICT", raw_write_plan, card, self.saved)

    def test_mixed_players_are_a_conflict(self):
        other = deepcopy(self.initial)
        other["player_id"] = "10000000-0000-4000-8000-000000000002"
        other["snapshot_id"] = snapshot_uuid(23)
        card = self.two_slot_card(self.initial, other)
        self.assert_code("RAW_PLAYER_CONFLICT", read_raw_dual, card)
        self.assert_code("RAW_PLAYER_CONFLICT", raw_write_plan, card, self.saved)

    def test_equal_generation_different_snapshots_are_a_conflict(self):
        card = self.two_slot_card(self.initial, self.saved, 2, 2)
        self.assert_code("RAW_EQUAL_GENERATION_CONFLICT", read_raw_dual, card)

    def test_reexport_of_identical_snapshot_remains_valid(self):
        for generations in ((1, 2), (2, 2)):
            with self.subTest(generations=generations):
                card = self.two_slot_card(self.saved, self.saved, *generations)
                self.assertEqual(read_raw_dual(card)["snapshot"], self.saved)

    def test_hash_valid_nonobject_payloads_fall_back_without_crashing(self):
        old = pad_slot(encode_container(self.initial, profile=2, generation=1))
        template = encode_container(self.saved, profile=2, generation=2)
        for invalid in ([], None, 0, "not a snapshot"):
            with self.subTest(root_type=type(invalid).__name__):
                malformed = replace_plain_payload(template, invalid)
                self.assert_code("SAVE_INVALID", decode_container, malformed)
                self.assertEqual(read_raw_dual(old + pad_slot(malformed))["snapshot"], self.initial)

    def test_hash_valid_snapshot_missing_collection_falls_back(self):
        invalid = deepcopy(self.saved)
        del invalid["collection"]
        self.assert_code("SAVE_INVALID", encode_container, invalid)
        template = encode_container(self.saved, profile=2, generation=2)
        malformed = replace_plain_payload(template, invalid)
        self.assert_code("SAVE_INVALID", decode_container, malformed)
        old = pad_slot(encode_container(self.initial, profile=2, generation=1))
        self.assertEqual(read_raw_dual(old + pad_slot(malformed))["snapshot"], self.initial)

    def test_generation_overflow_refuses_without_wrap(self):
        old = encode_container(self.initial, profile=2, generation=0xFFFFFFFF)
        card = pad_slot(old) + bytes(SLOT_BYTES)
        self.assertEqual(read_raw_dual(card)["generation"], 0xFFFFFFFF)
        self.assert_code("CARD_GENERATION_EXHAUSTED", raw_write_plan, card, self.saved)
        self.assert_code("CARD_GENERATION_EXHAUSTED", encode_container, self.saved, generation=0x100000000)
        self.assertEqual(read_raw_dual(card)["snapshot"], self.initial)

    def test_nonempty_damaged_card_is_not_automatically_initialized(self):
        damaged = bytearray(8192)
        damaged[200] = 1
        self.assert_code("RAW_NO_VALID_SLOT", raw_write_plan, bytes(damaged), self.initial)

    def test_claim_vectors_match_rewards_and_snapshot_hashes(self):
        for vector in self.draw["vectors"]:
            with self.subTest(hero=vector["hero"]["hero_card_id"]):
                source = deepcopy(vector["input_snapshot"])
                result = claim_hero(
                    source, vector["hero"], self.pack, vector["observed_utc_ms"],
                    vector["clock_source"], self.draw["device_id"], vector["new_snapshot_id"],
                )
                self.assertEqual(result["reward"], vector["expected_reward"])
                self.assertEqual(digest(result["snapshot"]), vector["expected_snapshot_hash"])
                self.assertEqual(source, vector["input_snapshot"])
                validate_snapshot(result["snapshot"])

    def test_claim_day_change_preserves_unknown_nested_fields(self):
        source = deepcopy(self.saved)
        source["clock"]["future_clock"] = {"format": 7, "label": "保留"}
        source["day_ledger"]["future_ledger"] = [1, {"ok": True}]
        source["wallet"]["future_wallet"] = {"tickets": 3}
        source["extensions"]["future_extension"] = "portable"
        before = deepcopy(source)
        result = claim_hero(
            source, self.draw["vectors"][0]["hero"], self.pack,
            self.draw["utc_ms"] + 86_400_000, "network",
            self.draw["device_id"], snapshot_uuid(24),
        )["snapshot"]
        self.assertEqual(source, before)
        self.assertEqual(result["clock"]["future_clock"], before["clock"]["future_clock"])
        self.assertEqual(result["day_ledger"]["future_ledger"], before["day_ledger"]["future_ledger"])
        self.assertEqual(result["wallet"]["future_wallet"], before["wallet"]["future_wallet"])
        self.assertEqual(result["extensions"], before["extensions"])
        self.assertEqual(result["day_ledger"]["day_id"], self.saved["day_ledger"]["day_id"] + 1)
        self.assertEqual(len(result["day_ledger"]["claims"]), 1)
        self.assertEqual(decode_container(encode_container(result, codec=1))["snapshot"], result)

    def test_future_snapshot_is_readonly_and_cannot_be_redeemed_or_bumped(self):
        future = deepcopy(self.saved)
        future["save_schema_version"] = 2
        future["wallet"]["shards"] = 100
        template = encode_container(self.saved, profile=1)
        encoded_future = replace_plain_payload(template, future)
        decoded = decode_ndef_single(encode_ndef_single(encoded_future))
        self.assertTrue(decoded["read_only"])
        self.assertEqual(decoded["snapshot"], future)
        self.assert_code("SAVE_SCHEMA_UNSUPPORTED", encode_container, future)
        self.assert_code(
            "SAVE_SCHEMA_UNSUPPORTED", redeem_ink_skin,
            future, future["collection"][0]["template_id"], self.pack,
            self.draw["device_id"], snapshot_uuid(25), self.draw["utc_ms"] + 1,
        )
        self.assert_code(
            "SAVE_SCHEMA_UNSUPPORTED", bump_snapshot,
            future, deepcopy(future), self.draw["device_id"], snapshot_uuid(26),
            self.draw["utc_ms"] + 1,
        )
        self.assertEqual(future["wallet"]["shards"], 100)

    def test_login_selection_never_requests_automatic_card_write(self):
        cases = [
            (None, self.initial, "card"),
            (self.saved, self.initial, "local"),
            (self.initial, self.saved, "card"),
            (self.saved, self.saved, "local"),
        ]
        for local, card, expected in cases:
            with self.subTest(expected=expected, local_id=None if local is None else local["snapshot_id"]):
                result = select_login_snapshot(local, card)
                self.assertEqual(result["decision"], expected)
                self.assertFalse(result["write_card"])

    def test_login_same_id_different_hash_and_parallel_branches_conflict(self):
        changed = deepcopy(self.saved)
        changed["wallet"]["shards"] += 10
        self.assertEqual(select_login_snapshot(self.saved, changed)["decision"], "conflict")
        branch = self.child(self.initial, 27)
        branch["writer_device_id"] = "20000000-0000-4000-8000-000000000002"
        result = select_login_snapshot(self.saved, branch)
        self.assertEqual(result["decision"], "conflict")
        self.assertFalse(result["write_card"])


if __name__ == "__main__":
    unittest.main()
