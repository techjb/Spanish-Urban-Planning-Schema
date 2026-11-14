"""Validate committed urban planning and cadastral parcel fixtures."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
ROOT = Path(__file__).resolve().parents[1]
def validator(name):
    schema=json.loads((ROOT/"schemas/v1"/f"{name}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema,format_checker=FormatChecker())
urban=validator("urban-planning-plot")
cad=validator("cadastral-plot")
seen=set()
for city,count in {"madrid":20,"valencia":5,"barcelona":5,"bilbao":5}.items():
    is_urban=city=="madrid"
    kind="urban-planning" if is_urban else "cadastral"
    path=ROOT/"validation"/city/f"sups-{kind}-plots.json"
    records=json.loads(path.read_text())
    assert len(records)==count,(city,len(records))
    for p in records:
        (urban if is_urban else cad).validate(p)
        key=("urban",p["plotId"]) if is_urban else ("cadastral",p["cadastralReference"])
        assert key not in seen,key
        seen.add(key)
        if is_urban:
            assert p["calculationStatus"]=="UNKNOWN" and p["parameters"]=={}
        else:
            assert p["measuredAreaM2"]>0
            assert "officialAreaM2" not in p
    print(f"PASS {city}: {count} {kind} parcels")
assert len(seen)==35
print("PASS: 35 unique parcel records")
