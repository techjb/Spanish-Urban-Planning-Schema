"""Check normalized vocabulary IDs and illustrative municipality mappings."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads((ROOT/p).read_text())
classes=read("vocabularies/land-classifications.json")["classes"]
uses=read("vocabularies/land-uses.json")["uses"]
assert len({x["id"] for x in classes})==len(classes)
assert len({x["id"] for x in uses})==len(uses)
for x in classes:
    assert len({c["id"] for c in x["categories"]})==len(x["categories"])
for x in uses:
    assert len({c["id"] for c in x["subtypes"]})==len(x["subtypes"])
c={x["id"]:{y["id"] for y in x["categories"]} for x in classes}
u={x["id"]:{y["id"] for y in x["subtypes"]} for x in uses}
mapping=read("examples/municipal-mappings.json")
assert mapping["municipalityCode"] and mapping["sourceVersion"]
for m in mapping["mappings"]:
    assert m["status"] in {"VERIFIED","PROPOSED","REQUIRES_REVIEW"}
    if m["domain"]=="LAND_CLASSIFICATION":
        assert m["normalizedCategory"] in c[m["normalizedClass"]]
    elif m["domain"]=="CHARACTERISTIC_USE":
        assert m["normalizedSubtype"] in u[m["normalizedUse"]]
    else: raise AssertionError("Unknown mapping domain")
from jsonschema import Draft202012Validator
for path in ["schemas/v1/zoning-area.schema.json","schemas/v1/urban-planning-plot.schema.json"]:
    Draft202012Validator.check_schema(read(path))
zone=read("schemas/v1/zoning-area.schema.json")
plot=read("schemas/v1/urban-planning-plot.schema.json")
assert set(zone["properties"]["characteristicUse"]["properties"]["use"]["enum"])==set(u)
assert set(plot["properties"]["landClassification"]["properties"]["class"]["enum"])==set(c)
assert set(zone["properties"]["landClassification"]["properties"]["class"]["enum"])==set(c)
assert set(plot["properties"]["allowedUses"]["items"]["properties"]["use"]["enum"]).issubset(set(u))
print("PASS: classification and use vocabularies, mapping examples and schema consistency")
