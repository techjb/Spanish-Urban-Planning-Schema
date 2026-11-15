"""Validate and normalize a frozen Bilbao capture, or compare two release manifests."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from jsonschema import Draft202012Validator, FormatChecker
from shapely import STRtree, normalize, orient_polygons, union_all
from shapely.geometry import mapping, shape
from shapely.validation import explain_validity

from capture_zoning import FILTER, LAYERS, encode


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INE = "48020"
PREFIX = "48020 - Bilbao"
BUCKET = "goolzoom-sups-data"
OUTPUTS = ("sups-zoning-areas.json", "zoning-audit.json", "source.zip")
CLASS_LAYERS = range(1, 5)


def load(path):
    return json.loads(path.read_bytes())


def digest(data):
    return sha256(data).hexdigest()


def inventory_rows(archive, capture):
    if (capture["municipalityCode"] != INE or capture["filter"] != FILTER
            or set(capture["pages"]) != set(map(str, LAYERS))):
        raise ValueError("Unexpected capture scope")
    names = archive.namelist()
    if len(names) != len(set(names)) or set(names) != {"capture.json", *capture["requests"]}:
        raise ValueError("Snapshot inventory differs from capture manifest")
    for name, info in capture["requests"].items():
        if digest(archive.read(name)) != info["sha256"]:
            raise ValueError(f"Snapshot checksum mismatch: {name}")

    def response(name):
        obj = json.loads(archive.read(name))
        if "error" in obj or obj.get("exceededTransferLimit"):
            raise ValueError(f"Invalid service response: {name}")
        return obj

    result = {}
    for layer in LAYERS:
        before = response(f"{layer}/before-ids.json")["objectIds"] or []
        after = response(f"{layer}/after-ids.json")["objectIds"] or []
        counts = [response(f"{layer}/{stage}-count.json")["count"] for stage in ("before", "after")]
        rows = [row for page in capture["pages"][str(layer)] for row in response(page)["features"]]
        ids = [row["properties"]["OBJECTID"] for row in rows]
        if not (sorted(before) == sorted(after) == sorted(ids)
                and counts == [len(set(ids)), len(ids)]):
            raise ValueError(f"Layer {layer}: incomplete or duplicate extraction")
        if any(row["properties"]["Municipio"] != "BILBAO" for row in rows):
            raise ValueError(f"Layer {layer}: data outside Bilbao filter")
        result[layer] = sorted(rows, key=lambda row: row["properties"]["OBJECTID"])
    if not any(result[layer] for layer in (1, 2, 3)):
        raise ValueError("Empty municipal classification")
    return result


def source_field(layer):
    if layer in CLASS_LAYERS:
        return "ClasificacionCA"
    return "UsoGlobalCA" if layer <= 10 else "CalificacionPormenorizadaCA"


def normalize_attribute(layer, attributes, catalog):
    field = source_field(layer)
    code = attributes[field]
    match = [rule for rule in catalog[str(layer)]
             if all(attributes[key] == value for key, value in rule["when"].items())]
    classification = layer in CLASS_LAYERS
    target = "class" if classification else "use"
    result = {target: "UNKNOWN", "mappingStatus": "REQUIRES_REVIEW"}
    if classification:
        result.update(jurisdiction="ES-PV", category="UNKNOWN")
    if code:
        result["originalCode"] = code
        result["originalClass" if classification else "originalUse"] = code
        if not classification:
            result["provenance"] = {"sourceField": field, "originalCode": code,
                                    "basis": "ZONING_DESIGNATION"}
    if len(match) == 1:
        rule = match[0]
        if "value" in rule:
            result.update(rule["value"], mappingStatus="VERIFIED", mappingId=rule["id"])
            return result, None
        return result, rule["pending"]
    return result, "ambiguous_mapping" if match else "unmapped_key" if code else "missing_key"


def complete_global_uses(zones, rows, catalog):
    evidence = {}
    for global_layer, detail_layers in catalog["useFallback"].items():
        detail = defaultdict(list)
        for layer in detail_layers:
            for row in rows[layer]:
                oid = row["properties"]["OBJECTID"]
                area_id = f"ES-{INE}-DFB-{layer}-{oid}"
                if area_id in zones:
                    detail[oid].append(area_id)
        for row in rows[int(global_layer)]:
            oid = row["properties"]["OBJECTID"]
            global_id = f"ES-{INE}-DFB-{global_layer}-{oid}"
            if global_id not in zones:
                continue
            record, geom, pending = zones[global_id]
            hits = [area_id for area_id in detail[oid] if zones[area_id][1].equals(geom)]
            applied = False
            if len(hits) == 1 and pending.get("use") in {
                    "economic_activity_without_specific_use", "rural_categories_without_specific_use",
                    "general_system_without_specific_use"}:
                detailed_use = zones[hits[0]][0]["characteristicUse"]
                if detailed_use["mappingStatus"] == "VERIFIED":
                    for key in ("use", "subtype", "mappingStatus", "mappingId", "provenance"):
                        if key in detailed_use:
                            record["characteristicUse"][key] = detailed_use[key]
                    del pending["use"]
                    applied = True
            evidence[global_id] = {"matchingDetailAreaIds": hits, "useApplied": applied}
    return evidence


def prior_audit(rows):
    evidence = load(HERE / "evidencias.json")
    result = {}
    for layer, category in ((6, "use"), (13, "res"), (39, "district")):
        old = {hit["attrs"]["OBJECTID"]: hit["attrs"] for sample in evidence["parcelas"]
               for hit in sample["hits"][category]}
        current = {row["properties"]["OBJECTID"]: row["properties"] for row in rows[layer]}
        result[str(layer)] = {str(oid): {
            "found": oid in current,
            "changedFields": [key for key in sorted(attrs)
                              if oid in current and current[oid].get(key) != attrs[key]],
            "sameNameCurrentIds": [new_oid for new_oid, props in current.items()
                                   if props.get("NombreAmbito") == attrs.get("NombreAmbito")],
        } for oid, attrs in sorted(old.items())}
    return {"reference": evidence["fecha"], "source": "validation/bilbao/evidencias.json",
            "comparison": "Foral OBJECTID and source attributes only. No parcel intersection.",
            "layers": result}


def geometry_of(row):
    data = row["geometry"]
    if not data or data["type"] not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Missing or non-polygonal geometry")
    geom = shape(data)
    if geom.is_empty or geom.has_z or geom.area <= 0 or not geom.is_valid:
        raise ValueError(explain_validity(geom) if not geom.is_valid else "Empty, 3D or zero-area geometry")
    west, south, east, north = geom.bounds
    if not (-4 < west <= east < -2 and 42 < south <= north < 44):
        raise ValueError("Coordinates outside expected Bilbao region in EPSG:4326")
    return normalize(geom)


def overlay_classification(zones):
    # Union per class/category avoids counting overlaps within the same designation.
    groups = defaultdict(list)
    for record, geom, _ in zones.values():
        if record["areaType"] == "LAND_CLASSIFICATION":
            classification = record["landClassification"]
            groups[classification["class"], classification["category"]].append(
                (record["areaId"], geom, classification))
    sources = [item for values in groups.values() for item in values]
    index = STRtree([geom for _, geom, _ in sources])
    audit = {}
    for area_id, (record, geom, pending) in zones.items():
        if record["areaType"] == "LAND_CLASSIFICATION":
            continue
        overlaps = defaultdict(list)
        for position in sorted(index.query(geom, predicate="intersects")):
            source_id, source_geom, category = sources[position]
            intersection = geom.intersection(source_geom)
            if intersection.area > 0:
                overlaps[category["class"], category["category"]].append(
                    (source_id, intersection, category))
        ratios = {key: union_all([piece for _, piece, _ in parts]).area / geom.area
                  for key, parts in overlaps.items()}
        winners = [key for key, ratio in ratios.items() if key[0] != "UNKNOWN" and ratio >= 0.999]
        selected = None
        if len(winners) == 1 and all(ratio <= 0.001 for key, ratio in ratios.items()
                                      if key != winners[0]):
            selected = winners[0]
            candidates = {encode(attrs): attrs for _, _, attrs in overlaps[selected]}
            if len(candidates) == 1:
                record["landClassification"] = next(iter(candidates.values()))
            else:
                record["landClassification"] = {"class": selected[0], "category": selected[1],
                                                "jurisdiction": "ES-PV", "mappingStatus": "VERIFIED"}
            record["areaType"] = "MIXED"
        else:
            pending["classification"] = ("classification_overlap_or_suspension"
                                         if ratios else "no_classification_overlap")
            record["landClassification"] = {"class": "UNKNOWN", "category": "UNKNOWN",
                                            "jurisdiction": "ES-PV", "mappingStatus": "REQUIRES_REVIEW"}
        audit[area_id] = {"assigned": selected, "intersections": [
            {"class": key[0], "category": key[1], "coverage": round(ratio, 9),
             "sourceAreaIds": sorted(source_id for source_id, _, _ in overlaps[key])}
            for key, ratio in sorted(ratios.items())]}
    return audit


def validate(records):
    schema = load(ROOT / "schemas/v1/zoning-area.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    classes = {item["id"]: {category["id"] for category in item["categories"]}
               for item in load(ROOT / "vocabularies/land-classifications.json")["classes"]}
    uses = {item["id"]: {subtype["id"] for subtype in item["subtypes"]}
            for item in load(ROOT / "vocabularies/land-uses.json")["uses"]}
    for record in records:
        validator.validate(record)
        classification = record["landClassification"]
        if classification["category"] not in classes[classification["class"]]:
            raise ValueError(f"Invalid class/category: {record['areaId']}")
        use = record.get("characteristicUse")
        if use and (use["use"] not in uses or
                    ("subtype" in use and use["subtype"] not in uses[use["use"]])):
            raise ValueError(f"Invalid use/subtype: {record['areaId']}")


def generate(source, parent):
    catalog = load(HERE / "municipal-mappings.json")
    if catalog["municipalityCode"] != INE or set(catalog["layers"]) != set(map(str, LAYERS)):
        raise ValueError("Incorrect municipal mapping catalog scope")
    with ZipFile(source) as archive:
        capture = json.loads(archive.read("capture.json"))
        rows = inventory_rows(archive, capture)
        source_layers = {layer["id"]: layer for layer in json.loads(archive.read("layers.json"))["layers"]}

    zones, rejected = {}, {}
    layer_audit = {}
    for layer, features in rows.items():
        field = source_field(layer)
        layer_audit[str(layer)] = {"downloaded": len(features), "sourceField": field,
                                   "name": source_layers[layer]["name"],
                                   "keys": sorted(Counter(row["properties"][field] for row in features).items(),
                                                  key=lambda item: str(item[0]))}
        for row in features:
            attributes = row["properties"]
            oid = attributes["OBJECTID"]
            area_id = f"ES-{INE}-DFB-{layer}-{oid}"
            try:
                geom = geometry_of(row)
            except (ValueError, TypeError, KeyError) as error:
                rejected[area_id] = str(error)
                continue
            value, reason = normalize_attribute(layer, attributes, catalog["layers"])
            is_class = layer in CLASS_LAYERS
            kind = "classification" if is_class else "use"
            field = "landClassification" if is_class else "characteristicUse"
            exception = catalog["legalExceptions"]
            legal = attributes.get(exception["field"]) in exception["values"]
            if legal and not is_class:
                value.update(use="UNKNOWN", mappingStatus="REQUIRES_REVIEW")
                value.pop("mappingId", None)
                value.pop("subtype", None)
                reason = "pgou_2022_annulled_pgou_1995_use_unverified"
            # GeoJSON exterior rings counterclockwise, interior rings clockwise.
            record = {"schemaVersion": "1.0", "areaId": area_id, "regulationIds": [],
                      "geometry": json.loads(encode(mapping(orient_polygons(geom)))), field: value,
                      "areaType": "LAND_CLASSIFICATION" if is_class else "ZONING"}
            zones[area_id] = record, geom, {kind: reason} if reason else {}

    use_overlay = complete_global_uses(zones, rows, catalog)
    overlay = overlay_classification(zones)
    records = [record for record, _, _ in zones.values()]
    validate(records)
    areas = {}
    for area_id, (record, _, pending) in zones.items():
        areas[area_id] = {key: digest(encode(record.get(field))) for key, field in (
            ("geometry", "geometry"), ("classification", "landClassification"), ("use", "characteristicUse"))}
        areas[area_id]["pending"] = {
            key: {"reason": reason, "originalCode": record.get(
                "landClassification" if key == "classification" else "characteristicUse", {}).get("originalCode")}
            for key, reason in pending.items()}
    counts = {"downloaded": sum(map(len, rows.values())), "exported": len(records),
              "geometryRejected": len(rejected), "pendingAreas": sum(bool(v["pending"]) for v in areas.values()),
              "classificationVerified": sum(r["landClassification"]["class"] != "UNKNOWN" for r in records),
              "useApplicable": sum("characteristicUse" in r for r in records),
              "useVerified": sum(r.get("characteristicUse", {}).get("mappingStatus") == "VERIFIED" for r in records)}
    if counts["downloaded"] != counts["exported"] + counts["geometryRejected"]:
        raise ValueError("Release count mismatch")

    audit = {"layers": layer_audit, "rejectedGeometry": rejected, "classificationOverlay": overlay,
             "useOverlay": use_overlay, "priorAudit": prior_audit(rows),
             "pending": {key: item["pending"] for key, item in areas.items() if item["pending"]},
             "counts": counts, "catalog": catalog}
    bodies = dict(zip(OUTPUTS[:2], (encode(records), encode(audit))))
    source_bytes = source.read_bytes()
    objects = {name: {"sha256": digest(body), "bytes": len(body)}
               for name, body in {**bodies, "source.zip": source_bytes}.items()}
    timestamp = datetime.fromisoformat(capture["downloadStartedAt"]).strftime("%Y%m%dT%H%M%SZ")
    version = f"{timestamp}-{digest(encode(objects))[:16]}"
    uri = f"s3://{BUCKET}/{PREFIX}/{version}/"
    manifest = {"municipalityCode": INE, "version": version, "s3Uri": uri, "objects": objects,
                "capture": capture, "counts": counts, "areas": areas, "geometryRejected": rejected}
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / version
    with TemporaryDirectory(dir=parent) as work:
        staged = Path(work) / version
        staged.mkdir()
        for name, body in {**bodies, "manifest.json": encode(manifest)}.items():
            (staged / name).write_bytes(body)
        copyfile(source, staged / "source.zip")
        staged.rename(destination)
    return destination


def compare(before, after):
    old, new = before["areas"], after["areas"]
    shared = sorted(old.keys() & new.keys())
    return {"added": sorted(new.keys() - old.keys()), "removed": sorted(old.keys() - new.keys()),
            **{key: [area for area in shared if old[area][key] != new[area][key]]
               for key in ("geometry", "classification", "use")},
            "pending": {area: {"before": old.get(area, {}).get("pending", {}),
                               "after": new.get(area, {}).get("pending", {})}
                        for area in sorted(old.keys() | new.keys())
                        if old.get(area, {}).get("pending", {}) != new.get(area, {}).get("pending", {})},
            "geometryRejected": {"before": before["geometryRejected"], "after": after["geometryRejected"]}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("generate")
    new.add_argument("source", type=Path)
    new.add_argument("parent", type=Path)
    diff = commands.add_parser("compare")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    args = parser.parse_args()
    if args.command == "generate":
        print(generate(args.source, args.parent))
    else:
        print(encode(compare(load(args.before), load(args.after))).decode(), end="")
