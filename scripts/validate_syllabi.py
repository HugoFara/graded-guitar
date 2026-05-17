#!/usr/bin/env python3
"""
Validate each syllabi/*.json against syllabi/schema.json using only the standard library.

This avoids pulling in `jsonschema` as a dependency just for Milestone 0. We re-implement
the small subset of JSON Schema features that schema.json actually uses:
  type, required, additionalProperties, enum, items, minItems, $ref (local $defs),
  format (date / uri — checked structurally, not strictly).

When the project later grows real Python tooling (Milestone 1), swap this for `jsonschema`.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYLLABI = ROOT / "syllabi"
SCHEMA_PATH = SYLLABI / "schema.json"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URI_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


class ValidationError(Exception):
    pass


def resolve_ref(schema: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise ValidationError(f"unsupported $ref: {ref}")
    node = schema
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def check_type(value, expected: str, path: str) -> None:
    ok = (
        (expected == "object" and isinstance(value, dict))
        or (expected == "array" and isinstance(value, list))
        or (expected == "string" and isinstance(value, str))
        or (expected == "integer" and isinstance(value, int) and not isinstance(value, bool))
        or (expected == "number" and isinstance(value, (int, float)) and not isinstance(value, bool))
        or (expected == "boolean" and isinstance(value, bool))
        or (expected == "null" and value is None)
    )
    if not ok:
        raise ValidationError(f"{path}: expected type {expected}, got {type(value).__name__}")


def validate(value, subschema: dict, root: dict, path: str = "$") -> None:
    if "$ref" in subschema:
        subschema = resolve_ref(root, subschema["$ref"])

    if "type" in subschema:
        check_type(value, subschema["type"], path)

    if "enum" in subschema and value not in subschema["enum"]:
        raise ValidationError(f"{path}: {value!r} not in enum {subschema['enum']}")

    if subschema.get("format") == "date" and isinstance(value, str):
        if not DATE_RE.match(value):
            raise ValidationError(f"{path}: not a YYYY-MM-DD date: {value!r}")
        try:
            date.fromisoformat(value)
        except ValueError as e:
            raise ValidationError(f"{path}: invalid date {value!r}: {e}")

    if subschema.get("format") == "uri" and isinstance(value, str):
        if not URI_RE.match(value):
            raise ValidationError(f"{path}: not a URI: {value!r}")

    if isinstance(value, dict) and subschema.get("type") == "object":
        for req in subschema.get("required", []):
            if req not in value:
                raise ValidationError(f"{path}: missing required property {req!r}")
        props = subschema.get("properties", {})
        additional = subschema.get("additionalProperties", True)
        for k, v in value.items():
            child_path = f"{path}.{k}"
            if k in props:
                validate(v, props[k], root, child_path)
            elif additional is False:
                raise ValidationError(f"{path}: unexpected property {k!r}")
            elif isinstance(additional, dict):
                validate(v, additional, root, child_path)

    if isinstance(value, list) and subschema.get("type") == "array":
        if "minItems" in subschema and len(value) < subschema["minItems"]:
            raise ValidationError(
                f"{path}: expected at least {subschema['minItems']} items, got {len(value)}"
            )
        items_schema = subschema.get("items")
        if items_schema is not None:
            for i, item in enumerate(value):
                validate(item, items_schema, root, f"{path}[{i}]")


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text())
    failures = 0
    for path in sorted(SYLLABI.glob("*.json")):
        if path.name == "schema.json":
            continue
        try:
            doc = json.loads(path.read_text())
            validate(doc, schema, schema, path=path.name)
            grades = set(doc.get("grades", []))
            for i, piece in enumerate(doc.get("pieces", [])):
                g = piece.get("grade")
                if g not in grades:
                    raise ValidationError(
                        f"{path.name}: pieces[{i}].grade {g!r} not in declared grades {sorted(grades)}"
                    )
            print(f"  ok   {path.relative_to(ROOT)}")
        except (ValidationError, json.JSONDecodeError) as e:
            print(f"  FAIL {path.relative_to(ROOT)}: {e}")
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
