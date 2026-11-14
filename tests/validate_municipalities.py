"""Cross-municipality checks for committed SUPS Plot fixtures.

Run: python tests/validate_municipalities.py
Requires: jsonschema (see requirements-dev.txt).
Does not re-download or independently certify municipal source data.
"""
import json
from collections import Counter
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
schema = json.loads((ROOT / "schemas/v1/plot.schema.json").read_text(encoding="utf-8"))
validator = Draft202012Validator(schema, format_checker=FormatChecker())
expected = {"madrid": 20, "valencia": 5, "barcelona": 5, "bilbao": 5}
seen = set()
total = 0
for city, count in expected.items():
    path = ROOT / "validation" / city / "sups-plots.json"
    plots = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(plots, list), f"{city}: expected list"
    assert len(plots) == count, f"{city}: expected {count}, found {len(plots)}"
    statuses = Counter()
    for i, plot in enumerate(plots):
        validator.validate(plot)
        pid = plot["plotId"]
        assert pid not in seen, f"duplicate plotId: {pid}"
        seen.add(pid)
        statuses[plot["calculationStatus"]] += 1
        if city == "madrid":
            assert plot["calculationStatus"] == "UNKNOWN", f"{pid}: expected UNKNOWN"
            assert plot["parameters"] == {}, f"{pid}: unexpected resolved parameters"
        else:
            assert plot["calculationStatus"] == "PARTIAL", f"{pid}: expected PARTIAL"
            area = plot["parameters"].get("plotAreaM2")
            assert type(area) in (float, int) and area > 0, f"{pid}: missing positive plot area"
            assert "effectiveBuildableAreaM2" not in plot["parameters"], f"{pid}: unsupported parcel buildability"
    total += len(plots)
    print(f"PASS {city}: {len(plots)} fixtures, statuses={dict(statuses)}")
assert total == 35
print(f"PASS: {total} unique real-source plot fixtures structurally validated")
