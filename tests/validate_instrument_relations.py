"""Check instrument relationships and backward compatibility."""
import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
schema = json.loads((ROOT / "schemas/v1/planning-document.schema.json").read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, format_checker=FormatChecker())

legacy = {"schemaVersion": "1.0", "documentId": "legacy-plan", "name": "Legacy plan"}
validator.validate(legacy)

example = json.loads((ROOT / "examples/planning-document-amendment.json").read_text())
validator.validate(example)

for scope in (
    {"type": "ENTIRE_TARGET"},
    {"type": "UNKNOWN"},
    {
        "type": "GEOMETRY",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        },
    },
):
    document = deepcopy(example)
    document["instrumentRelations"][0]["scope"] = scope
    validator.validate(document)

for key, value in (
    ("scope", {"type": "ZONING_AREAS", "areaIds": []}),
    ("scope", {"type": "ENTIRE_TARGET", "areaIds": ["area-a"]}),
    ("scope", {"type": "GEOMETRY"}),
    ("effectiveFrom", "2026-02-30"),
    ("sourceIds", []),
    ("type", "UNKNOWN"),
):
    document = deepcopy(example)
    document["instrumentRelations"][0][key] = value
    assert not validator.is_valid(document), (key, value)

print("PASS: instrument relationships and SUPS 1.0 compatibility")
