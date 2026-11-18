"""Check instrument relationships and backward compatibility."""
import json
from copy import deepcopy
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
schema = json.loads((ROOT / "schemas/v1/planning-document.schema.json").read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, format_checker=FormatChecker())


def validate_document(document):
    validator.validate(document)
    if document["schemaVersion"] == "1.0":
        return

    seen_ids = set()
    relations = document.get("instrumentRelations", [])
    for relation in relations:
        if relation["targetDocumentId"] == document["documentId"]:
            raise ValueError("An instrument cannot relate to itself")
        relation_id = relation["relationId"]
        if relation_id in seen_ids:
            raise ValueError(f"Duplicate relation ID: {relation_id}")
        seen_ids.add(relation_id)

    for record in [document, *relations]:
        start = record.get("effectiveFrom")
        end = record.get("effectiveTo")
        if start and end and date.fromisoformat(start) >= date.fromisoformat(end):
            raise ValueError("effectiveFrom must precede effectiveTo")


def run_tests():
    legacy = {
        "schemaVersion": "1.0",
        "documentId": "legacy-plan",
        "name": "Legacy plan",
        "instrumentRelations": "legacy custom value",
        "publicationDate": "legacy custom value",
        "effectiveTo": "legacy custom value",
        "effectiveEndStatus": "legacy custom value",
    }
    validate_document(legacy)

    example = json.loads((ROOT / "examples/planning-document-amendment.json").read_text())
    validate_document(example)
    parameters = json.loads((ROOT / "vocabularies/parameters.json").read_text())
    parameter_ids = {parameter["id"] for parameter in parameters["parameters"]}
    for relation in example["instrumentRelations"]:
        for determination in relation["normativeScope"]["determinations"]:
            assert determination["parameterId"] in parameter_ids

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
        ("normativeScope", {"type": "SPECIFIC_DETERMINATIONS", "determinations": []}),
        ("effectiveEndStatus", "DATED"),
        ("effectiveTo", "2026-03-01"),
    ):
        document = deepcopy(example)
        document["instrumentRelations"][0][key] = value
        assert not validator.is_valid(document), (key, value)

    for scope_type in ("ENTIRE_TARGET", "UNKNOWN"):
        document = deepcopy(example)
        relation = document["instrumentRelations"][0]
        relation["normativeScope"] = {"type": scope_type}
        relation.update(effectiveEndStatus="DATED", effectiveTo="2026-03-01")
        validate_document(document)

    for changes in (
        {"targetDocumentId": example["documentId"]},
        {"effectiveEndStatus": "DATED", "effectiveTo": "2026-02-01"},
        {"effectiveEndStatus": "DATED", "effectiveTo": "2026-01-31"},
    ):
        document = deepcopy(example)
        document["instrumentRelations"][0].update(changes)
        try:
            validate_document(document)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Accepted invalid relation: {changes}")

    print("PASS: instrument relationships and SUPS 1.0 compatibility")


if __name__ == "__main__":
    run_tests()
