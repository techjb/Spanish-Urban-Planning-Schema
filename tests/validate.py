"""Validate SUPS schemas, registered parameter names, and primitive value types."""
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
catalog = json.loads((ROOT / "vocabularies/parameters.json").read_text())
registered = {p["id"]: p for p in catalog["parameters"]}
assert len(registered) == len(catalog["parameters"]), "Duplicate parameter identifier"

def load_schema(name):
    schema = json.loads((ROOT / "schemas/v1" / f"{name}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())

schemas = {name: load_schema(name) for name in
           ("regulation", "cadastral-plot", "urban-planning-plot", "planning-document", "zoning-area", "regulation-source")}

def expected_type(key, meta):
    if key.endswith(("Pct", "Ratio", "M", "M2", "M3", "Deg", "Ha")) or key.startswith(("minParkingSpacesPer", "minTreesPer")):
        return "number"
    if key.endswith(("Floors", "Count", "Spaces", "DwellingsPerBuilding")) or key in ("maxDwellingCount", "minDwellingCount"):
        return "integer"
    if key.endswith(("Allowed", "Required", "Eligible", "Completed")):
        return "boolean"
    return None

def check_value(key, value):
    typ = expected_type(key, registered[key])
    if typ == "number":
        assert type(value) in (int, float), f"{key}: expected number, got {value!r}"
    elif typ == "integer":
        assert type(value) is int, f"{key}: expected integer, got {value!r}"
    elif typ == "boolean":
        assert type(value) is bool, f"{key}: expected boolean, got {value!r}"

def validate_regulation(data):
    schemas["regulation"].validate(data)
    for key, parameter in data["parameters"].items():
        assert key in registered, f"Unknown SUPS parameter: {key}"
        assert registered[key]["scope"] == "regulation", f"Wrong scope: {key}"
        status = parameter["status"]
        if status == "FIXED":
            assert parameter.get("value") is not None, f"{key}: fixed value missing"
            check_value(key, parameter["value"])
        if status == "CONDITIONAL":
            assert parameter.get("variants"), f"{key}: missing variants"
            for variant in parameter["variants"]:
                assert variant.get("value") is not None, f"{key}: null conditional value"
                assert variant.get("condition"), f"{key}: empty condition"
                check_value(key, variant["value"])

for name, example in [("regulation", "simple-regulation"),
                      ("regulation", "conditional-regulation"),
                      ("urban-planning-plot", "resolved-plot")]:
    data = json.loads((ROOT / "examples" / f"{example}.json").read_text())
    if name == "regulation":
        validate_regulation(data)
    else:
        schemas[name].validate(data)
    print(f"PASS: examples/{example}.json")

sample = json.loads((ROOT / "examples/simple-regulation.json").read_text())
sample["parameters"]["notInSUPS"] = {"status": "FIXED", "value": 3}
try:
    validate_regulation(sample)
except AssertionError:
    print("PASS: rejects unknown parameter")
else:
    raise AssertionError("Unknown parameter was accepted")

print(f"PASS: {len(registered)} unique registered identifiers")
