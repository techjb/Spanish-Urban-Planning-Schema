"""Offline checks using the Barcelona catalog, audit and archived AMB response."""
import json
from collections import Counter
from itertools import accumulate

from jsonschema import Draft202012Validator
from pyproj import Transformer
from shapefile import POLYGON, Shape
from shapely import transform
from shapely.geometry import mapping, shape

from generate_zoning import (AMB, HERE, ZipFile, check_page, encode, inventory, load_rules,
                             normalize_feature, read, select)

rules = load_rules()
counts = Counter()
audit = read(HERE / "planning-audit.json")
for group in audit["amb"]["groups"]:
    attrs = group["original"]
    field = "CLAU_PD" if attrs["CLAU_PD"] and attrs["CLAU_PD"] != attrs["CLAU_URB"] else "CLAU_URB"
    use, _ = select(rules, AMB, field, attrs)
    classification, _ = select(rules, AMB, "REGIM", attrs)
    counts["class"] += group["recordCount"] * bool(classification)
    counts["use"] += group["recordCount"] * bool(use)
assert counts == {"class": 4607, "use": 2688}, counts

cross = read(HERE / "muc-pending-comparison.json")
assert cross["auditExtractedAt"] == audit["extractedAt"]
matched = 0
for row in cross["polygons"]:
    candidate, _ = select(rules, cross["mucSource"], "C_QUAL_MUC", {"C_QUAL_MUC": row["mucCode"]},
                          cross["mucSnapshot"])
    if candidate:
        assert row["mucUse"]["normalizedUse"] == candidate["normalizedUse"]
        assert row["mucUse"]["normalizedSubtype"] == candidate["normalizedSubtype"]
        matched += 1
assert (matched, len(cross["polygons"]) - matched) == (1477, 442)

with ZipFile(HERE / "respuestas-oficiales.zip") as archive:
    esri = json.loads(archive.read("barcelona-amb-0.json"))["response"]
feature = next(row for row in esri["features"] if row["attributes"]["OBJECTID"] == 74768)
project = Transformer.from_crs(25831, 4326, always_xy=True).transform
rings = feature["geometry"]["rings"]
esri_geometry = Shape(POLYGON, points=[point for ring in rings for point in ring],
                      parts=list(accumulate(map(len, rings[:-1]), initial=0)))
geometry = mapping(transform(shape(esri_geometry.__geo_interface__), project, interleaved=False))
geo = {"properties": feature["attributes"], "geometry": geometry}
page = {"type": "FeatureCollection", "features": [geo]}
check_page(page, [74768], 4326)
first, evidence = normalize_feature(geo, rules, None)
second, _ = normalize_feature(geo, rules, None)
assert encode(first) == encode(second)
assert first["characteristicUse"]["use"] == "RESIDENTIAL"
assert not evidence["pending"]
Draft202012Validator(read(HERE.parents[1] / "schemas/v1/zoning-area.schema.json")).validate(first)

unknown = dict(geo, properties=dict(geo["properties"], CLAU_PD="NEW-UNMAPPED"))
record, evidence = normalize_feature(unknown, rules, None)
assert "characteristicUse" not in record
assert evidence["pending"]["use"] == "UNMAPPED_CODE"

for action in (lambda: check_page(page, [74768, 74769], 4326), lambda: inventory(2, [74768])):
    try:
        action()
    except ValueError:
        pass
    else:
        raise AssertionError("Incomplete extraction accepted")
print("AMB coverage, historical MUC rules, reproducible fixture, unknown code and truncated extraction: OK")
