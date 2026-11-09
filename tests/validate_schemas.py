"""Optional JSON Schema check of the published schemas and positive data corpus.

Usage (any working directory): python tests/validate_schemas.py
Optional dependency: jsonschema>=4.18 (and its referencing dependency).
Exit codes: 0 = all checked data valid; 1 = invalid data/schema; 2 = dependency absent.

This checks structure, not rule execution, NFC hardware or binary integrity.
The placeholder views nested in wire_examples are intentionally NOT treated as
core battle/view fixtures. Their envelopes are checked as wire-format examples.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def frame_inspection(hex_text):
    """Adapt a golden binary record to frame.schema's documented inspection form.

    CRC and cross-field binary invariants are exercised by test_wire.py, not by
    JSON Schema. This adapter only exposes the actual header and payload fields.
    """
    raw = bytes.fromhex(hex_text)
    if len(raw) < 24:
        raise ValueError("binary fixture is shorter than the 24-byte frame header")
    fields = struct.unpack(">2sBBIIHBBHHI", raw[:24])
    names = ("magic", "frame_version", "kind", "link_id", "transfer_id", "total_len",
             "frag_index", "frag_count", "payload_len", "flags", "crc32")
    result = dict(zip(names, fields))
    result["magic"] = result["magic"].decode("ascii")
    result["payload_hex"] = raw[24:].hex()
    return result


def positive_instances():
    """Yield (source label, schema filename/component, instance) from fixed inputs."""
    yield "content/core_pack.json", "content-pack.schema.json", load_json("content/core_pack.json")
    for name in ("player_initial.json", "player_after_claim.json"):
        path = f"examples/{name}"
        yield path, "player-snapshot.schema.json", load_json(path)
    for name in ("hero_fixed.json", "hero_blind_box.json"):
        path = f"examples/{name}"
        yield path, "hero-descriptor.schema.json", load_json(path)
    for name in ("battle_view_player0.json", "battle_view_spectator.json"):
        path = f"examples/{name}"
        yield path, "battle-view.schema.json", load_json(path)

    draw = load_json("fixtures/draw_vectors.json")
    yield "fixtures/draw_vectors.json#/initial_snapshot", "player-snapshot.schema.json", draw["initial_snapshot"]
    for index, vector in enumerate(draw["vectors"]):
        prefix = f"fixtures/draw_vectors.json#/vectors/{index}"
        yield f"{prefix}/input_snapshot", "player-snapshot.schema.json", vector["input_snapshot"]
        yield f"{prefix}/hero", "hero-descriptor.schema.json", vector["hero"]
    storage = load_json("fixtures/storage_vectors.json")
    yield "fixtures/storage_vectors.json#/snapshot", "player-snapshot.schema.json", storage["snapshot"]

    battle = load_json("fixtures/battle_golden.json")
    yield "fixtures/battle_golden.json#/initial_state", "battle-state.schema.json", battle["initial_state"]
    for index, step in enumerate(battle["steps"]):
        prefix = f"fixtures/battle_golden.json#/steps/{index}"
        yield f"{prefix}/expected_state", "battle-state.schema.json", step["expected_state"]
        yield f"{prefix}/command", "envelope.schema.json#/$defs/command_body", step["command"]

    golden = load_json("fixtures/wire_golden.json")
    yield "fixtures/wire_golden.json#/envelope", "envelope.schema.json", golden["envelope"]
    for index, frame_hex in enumerate(golden["frames_hex"]):
        yield f"fixtures/wire_golden.json#/frames_hex/{index}", "frame.schema.json", frame_inspection(frame_hex)
    for field in ("open_hex", "accept_hex"):
        yield f"fixtures/wire_golden.json#/{field}", "frame.schema.json", frame_inspection(golden[field])

    examples = load_json("examples/wire_examples.json")
    for fixture_index, fixture in enumerate(examples["fixtures"]):
        for message_index, envelope in enumerate(fixture["envelopes"]):
            source = f"examples/wire_examples.json#/fixtures/{fixture_index}/envelopes/{message_index}"
            yield source, "envelope.schema.json", envelope
    vector = examples["binary_frame_vector"]
    prefix = "examples/wire_examples.json#/binary_frame_vector"
    yield f"{prefix}/envelope", "envelope.schema.json", vector["envelope"]
    for field in ("open", "accept", "complete_ack"):
        yield f"{prefix}/{field}/decoded", "frame.schema.json", vector[field]["decoded"]
    for index, frame in enumerate(vector["data_frames"]):
        yield f"{prefix}/data_frames/{index}/decoded", "frame.schema.json", frame["decoded"]


def json_pointer(path):
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in path)


def main():
    try:
        import jsonschema
        from referencing import Registry, Resource
    except ImportError:
        print("SKIP: optional dependency missing; install jsonschema>=4.18 to run schema validation.")
        return 2

    schema_paths = sorted((ROOT / "schemas").glob("*.schema.json"))
    if not schema_paths:
        print("FAIL: no schema files found", file=sys.stderr)
        return 1
    try:
        schemas = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in schema_paths}
        for name, schema in schemas.items():
            try:
                jsonschema.validators.validator_for(schema).check_schema(schema)
            except jsonschema.SchemaError as error:
                print(f"FAIL schema {name}: {error.message}", file=sys.stderr)
                return 1
        ids = [schema["$id"] for schema in schemas.values()]
        if len(ids) != len(set(ids)):
            raise ValueError("schema $id values must be unique")
        # Register only local resources. No schema is fetched from the network.
        registry = Registry().with_resources(
            (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
        )
        validators = {
            name: jsonschema.validators.validator_for(schema)(
                schema, registry=registry, format_checker=jsonschema.FormatChecker()
            )
            for name, schema in schemas.items()
        }
        command_ref = schemas["envelope.schema.json"]["$id"] + "#/$defs/command_body"
        validators["envelope.schema.json#/$defs/command_body"] = jsonschema.Draft202012Validator(
            {"$ref": command_ref}, registry=registry
        )

        valid_counts, failures, total = Counter(), [], 0
        for source, schema_name, instance in positive_instances():
            total += 1
            errors = list(validators[schema_name].iter_errors(instance))
            if errors:
                for error in errors[:3]:
                    failures.append(f"{source} -> {schema_name} {json_pointer(error.absolute_path)}: {error.message[:500]}")
            else:
                valid_counts[schema_name] += 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL loading/checking the positive corpus: {error}", file=sys.stderr)
        return 1

    print(f"Schemas checked: {len(schemas)}")
    print(f"Valid positive objects: {sum(valid_counts.values())}/{total}")
    for name in sorted(validators):
        print(f"  {name}: {valid_counts[name]}")
    print("Wire demo nested views: envelope-format checks only; not counted as core battle/view instances.")
    unused = [name for name in sorted(schemas) if valid_counts[name] == 0]
    if unused:
        print("Schema definitions checked without a supplied positive instance: " + ", ".join(unused))
    if failures:
        for failure in failures:
            print("FAIL " + failure, file=sys.stderr)
        return 1
    print("PASS: all supplied schemas and adapted positive instances are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
