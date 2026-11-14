"""Validate SUPS search/filter semantics, not only JSON shape."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[1]
def schema(name):
    data=json.loads((ROOT/"schemas/v1"/f"{name}.schema.json").read_text())
    Draft202012Validator.check_schema(data)
    return Draft202012Validator(data, format_checker=FormatChecker())
plot_validator=schema("urban-planning-plot")
area_validator=schema("zoning-area")
sample=json.loads((ROOT/"examples/resolved-plot.json").read_text())
plot_validator.validate(sample)
assert sample["landClassification"]["class"]=="URBAN"
assert sample["landClassification"]["category"]=="CONSOLIDATED"
assert sample["parameters"]["effectiveBuildableAreaM2"]==1500
assert sample["parameterEvidence"]["effectiveBuildableAreaM2"]["status"]=="RESOLVED"
assert any(u["use"]=="RESIDENTIAL" and u["status"]=="ALLOWED" for u in sample["allowedUses"])
assert any(u["use"]=="COMMERCIAL" and u["status"]=="CONDITIONAL" for u in sample["allowedUses"])
assert sample["calculationStatus"]=="PARTIAL", "Individual resolved parameters do not imply globally resolved parcel"
import copy
invalid=copy.deepcopy(sample)
invalid["landClassification"]["class"]="RANDOM"
try:
    plot_validator.validate(invalid)
except ValidationError:
    pass
else:
    raise AssertionError("Unknown land class accepted")
invalid=copy.deepcopy(sample)
invalid["allowedUses"][0]["status"]="UNLIMITED"
try:
    plot_validator.validate(invalid)
except ValidationError:
    pass
else:
    raise AssertionError("Invalid use status accepted")
area_validator.validate({"schemaVersion":"1.0","areaId":"EXAMPLE-CLASSIFICATION-1","regulationIds":[],"areaType":"LAND_CLASSIFICATION","landClassification":{"class":"URBAN","category":"CONSOLIDATED"},"geometry":{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]}})
print("PASS: parcel filter example, invalid values rejected, classification-only area accepted")
