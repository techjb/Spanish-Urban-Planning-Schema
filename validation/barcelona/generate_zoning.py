"""Download, validate and version the Barcelona SUPS Zoning Area dataset."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isclose
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from shapely import make_valid, normalize, orient_polygons, to_geojson
from shapely.errors import GEOSException
from shapely.geometry import shape
from shapely.validation import explain_validity

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AMB = "https://geoportal.amb.cat/geoserveis/rest/services/qualificacio_refos/MapServer/0"
WHERE = "CODI_INE = '08019'"
FIELDS = ("REGIM", "CLAU_URB", "CLAU_PD", "EXP_PD", "PLAN", "DESCRIP", "US_SECT")
BATCH = 100


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode()


def read(path):
    return json.loads(path.read_bytes())


def digest(data):
    return sha256(data).hexdigest()


def inventory(count, ids):
    if count <= 0 or count != len(ids) or len(ids) != len(set(ids)):
        raise ValueError("AMB count and unique ID inventory disagree")
    return sorted(ids)


def check_page(response, ids, sr):
    if (response.get("exceededTransferLimit") or response.get("properties", {}).get("exceededTransferLimit")
            or response.get("type") != "FeatureCollection"):
        raise ValueError("Truncated or invalid AMB page")
    crs = response.get("crs", {}).get("properties", {}).get("name")
    if crs is None and sr != 4326 or crs is not None and not (crs.endswith(f":{sr}") or
                                                             sr == 4326 and crs.endswith(":CRS84")):
        raise ValueError(f"Unexpected output CRS: {crs}")
    rows = response["features"]
    if sorted(f["properties"]["OBJECTID"] for f in rows) != ids:
        raise ValueError("Incomplete AMB geometry batch")
    for feature in rows:
        attrs = feature["properties"]
        if attrs["CODI_INE"] != "08019" or feature.get("id", attrs["OBJECTID"]) != attrs["OBJECTID"]:
            raise ValueError("Out-of-scope or inconsistent AMB feature")
        if not set(FIELDS) <= attrs.keys():
            raise ValueError("Missing AMB fields")
    return rows


def capture(target):
    requests = {}
    started = datetime.now(timezone.utc).isoformat()

    def get(archive, name, url, **params):
        link = url + "?" + urlencode(params)
        with urlopen(link, timeout=90) as response:
            data = response.read()
        result = json.loads(data)
        if "error" in result:
            raise ValueError(f"{link}: {result['error']}")
        put(archive, name, data)
        requests[name] = {"url": link, "sha256": digest(data),
                          "downloadedAt": datetime.now(timezone.utc).isoformat()}
        return result

    def get_inventory(archive, suffix):
        count = get(archive, f"count{suffix}.json", AMB + "/query", f="json",
                    where=WHERE, returnCountOnly="true")["count"]
        ids = get(archive, f"ids{suffix}.json", AMB + "/query", f="json",
                  where=WHERE, returnIdsOnly="true")
        if ids.get("objectIdFieldName") != "OBJECTID" or ids.get("exceededTransferLimit"):
            raise ValueError("Invalid AMB ID response")
        return inventory(count, ids["objectIds"])

    with ZipFile(target, "w") as archive:
        metadata = get(archive, "service.json", AMB.rsplit("/", 1)[0], f="json")
        layer = get(archive, "layer.json", AMB, f="json")
        required = {"OBJECTID", "CODI_INE", *FIELDS}
        if not required <= {field["name"] for field in layer["fields"]}:
            raise ValueError("AMB changed its source fields")
        ids = get_inventory(archive, "")
        for start in range(0, len(ids), BATCH):
            batch = ids[start:start + BATCH]
            for sr in (4326, 25831):
                page = get(archive, f"{sr}-{start:05d}.json", AMB + "/query", f="geojson",
                           where=WHERE, objectIds=",".join(map(str, batch)), outFields="*",
                           returnGeometry="true", outSR=sr)
                check_page(page, batch, sr)
        if get_inventory(archive, "-end") != ids:
            raise ValueError("AMB inventory changed during download")
        subject = metadata.get("documentInfo", {}).get("Subject", "")
        put(archive, "capture.json", encode({"startedAt": started, "where": WHERE, "layer": AMB,
                                             "declaredEdition": subject, "requests": requests}))


def put(archive, name, data):
    archive.writestr(ZipInfo(name), data, compress_type=ZIP_DEFLATED)


def load_capture(path):
    with ZipFile(path) as archive:
        meta = json.loads(archive.read("capture.json"))
        if meta["where"] != WHERE or meta["layer"] != AMB:
            raise ValueError("Unexpected AMB layer or filter")
        for name, request in meta["requests"].items():
            if digest(archive.read(name)) != request["sha256"]:
                raise ValueError(f"Source fingerprint mismatch: {name}")
        ids = inventory(json.loads(archive.read("count.json"))["count"],
                        json.loads(archive.read("ids.json"))["objectIds"])
        end = inventory(json.loads(archive.read("count-end.json"))["count"],
                        json.loads(archive.read("ids-end.json"))["objectIds"])
        if ids != end:
            raise ValueError("AMB inventories differ")
        for start in range(0, len(ids), BATCH):
            batch = ids[start:start + BATCH]
            pages = []
            for sr in (4326, 25831):
                name = f"{sr}-{start:05d}.json"
                if name not in meta["requests"]:
                    raise ValueError(f"Untracked source page: {name}")
                rows = check_page(json.loads(archive.read(name)), batch, sr)
                pages.append(sorted(rows, key=lambda row: row["properties"]["OBJECTID"]))
            for geo, projected in zip(*pages):
                if geo["properties"] != projected["properties"]:
                    raise ValueError("AMB properties differ between coordinate systems")
                yield geo, projected


def select(rules, layer, field, attributes, version=None):
    code = attributes.get(field)
    if not code:
        return None, "MISSING_CODE"
    matching_code = rules[layer, field, code]
    candidates = [rule for rule in matching_code
                  if (version is None or rule["sourceVersion"] == version)
                  and all(key in attributes and (attributes[key] in value if isinstance(value, list)
                                                 else attributes[key] == value)
                          for key, value in rule.get("conditions", {}).items())]
    if not candidates:
        return None, "NO_APPLICABLE_RULE" if matching_code else "UNMAPPED_CODE"
    # A more specific rule must imply the conditions of a less specific one.
    conditions = {rule["mappingId"]: set(rule.get("conditions", {})) for rule in candidates}
    best = [rule for rule in candidates if not any(
        conditions[rule["mappingId"]] < other for other in conditions.values())]
    if len(best) != 1:
        return None, "AMBIGUOUS_RULE"
    return best[0], None


def polygon(geometry):
    if geometry is None:
        raise ValueError("AMB returned null geometry")
    if geometry.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError(f"Nonpolygonal AMB geometry: {geometry.get('type')}")
    geom = shape(geometry)
    if geom.is_empty:
        raise ValueError("Empty AMB geometry")
    if geom.is_valid and geom.area > 0:
        return geom, None
    problem = explain_validity(geom)
    repaired = make_valid(geom)
    if (repaired.geom_type not in ("Polygon", "MultiPolygon")
            or not repaired.is_valid or repaired.area <= 0
            or not isclose(repaired.area, geom.area, rel_tol=1e-8)):
        raise ValueError(problem)
    return repaired, {"method": "GEOS make_valid (linework)", "originalProblem": problem,
                      "relativeAreaChange": abs(repaired.area - geom.area) / geom.area}


def normalize_feature(feature, rules, muc_match):
    attrs = feature["properties"]
    oid = attrs["OBJECTID"]
    area_id = f"ES-08019-AMB-PCD-{oid}"
    evidence = {"areaId": area_id, "original": attrs, "pending": {}, "mappingEvidence": {}}
    try:
        geom, repair = polygon(feature["geometry"])
        x1, y1, x2, y2 = geom.bounds
        if not (1 < x1 <= x2 < 3 and 40 < y1 <= y2 < 43):
            raise ValueError("Coordinates outside the Barcelona WGS84 bounds")
    except (ValueError, TypeError, GEOSException) as exc:
        evidence["geometryError"] = str(exc)
        return None, evidence
    if repair:
        evidence["geometryRepair"] = repair

    record = {"schemaVersion": "1.0", "areaId": area_id, "regulationIds": [], "areaType": "MIXED",
              "geometry": json.loads(to_geojson(orient_polygons(normalize(geom))))}
    rule, reason = select(rules, AMB, "REGIM", attrs)
    if rule:
        record["landClassification"] = {
            "class": rule["normalizedClass"], "category": rule["normalizedCategory"],
            "originalCode": attrs["REGIM"],
            "jurisdiction": "ES-08019", "sourceDocumentId": rule["sourceDocumentId"],
            "mappingStatus": rule["status"], "mappingId": rule["mappingId"]}
        if rule["originalLabel"] is not None:
            record["landClassification"]["originalClass"] = rule["originalLabel"]
        evidence["mappingEvidence"]["classification"] = rule["sourceDocumentId"]
    else:
        evidence["pending"]["classification"] = reason
    field = "CLAU_PD" if attrs["CLAU_PD"] and attrs["CLAU_PD"] != attrs["CLAU_URB"] else "CLAU_URB"
    rule, reason = select(rules, AMB, field, attrs)
    # An ambiguous direct rule still needs review even if the MUC has a candidate.
    if not rule and reason != "AMBIGUOUS_RULE" and muc_match:
        evidence["ambUsePending"] = reason
        evidence["muc"] = muc_match
        if muc_match.get("code"):
            field = "C_QUAL_MUC"
            rule, reason = select(rules, muc_match["source"], field, {field: muc_match["code"]},
                                  muc_match["edition"])
            if not rule:
                reason = f"MUC_{reason}"
        else:
            reason = muc_match["reason"]
    if rule:
        provenance = dict(rule["provenance"])
        if field != "C_QUAL_MUC" and attrs["EXP_PD"]:
            provenance["planningInstrument"] = attrs["EXP_PD"]
        record["characteristicUse"] = {
            "use": rule["normalizedUse"], "subtype": rule["normalizedSubtype"],
            "originalCode": rule["originalCode"],
            "provenance": provenance, "mappingId": rule["mappingId"], "mappingStatus": rule["status"]}
        if rule["originalLabel"] is not None:
            record["characteristicUse"]["originalUse"] = rule["originalLabel"]
        evidence["mappingEvidence"]["use"] = rule["sourceDocumentId"]
    else:
        evidence["pending"]["use"] = reason
    return record, evidence


def load_rules():
    rules = defaultdict(list)
    catalog = read(HERE / "municipal-mappings.json")
    ids = set()
    for rule in catalog["mappings"]:
        ident = rule["mappingId"]
        if ident in ids:
            raise ValueError(f"Duplicate mappingId: {ident}")
        ids.add(ident)
        if rule["status"] == "VERIFIED" and rule["municipalityCode"] == "08019":
            rules[rule["sourceLayer"], rule["sourceField"], rule["originalCode"]].append(rule)
    return rules


def muc_lookup(path, edition):
    # Reuse the audited municipal filter and shapefile loader.
    import sys
    sys.path.insert(0, str(ROOT / "tests"))
    from compare_barcelona_muc import COVERAGE, MUC_DOWNLOAD, load_muc
    from shapely import STRtree
    from shapely.ops import unary_union

    shapes = load_muc(path)
    if not shapes:
        raise ValueError("No Barcelona MUC polygons")
    tree = STRtree([geom for _, geom in shapes])

    def overlap(feature):
        result = {"source": MUC_DOWNLOAD, "edition": edition, "code": None, "coverage": {}}
        if not feature["geometry"]:
            return dict(result, reason="NO_AMB_GEOMETRY")
        geom = make_valid(shape(feature["geometry"]))
        if geom.is_empty or geom.area <= 0:
            return dict(result, reason="NO_AMB_AREA")
        x1, y1, x2, y2 = geom.bounds
        if not (400000 < x1 <= x2 < 500000 and 4500000 < y1 <= y2 < 4700000):
            raise ValueError(f"Unexpected EPSG:25831 coordinates for AMB {feature['properties']['OBJECTID']}")
        pieces = defaultdict(list)
        for index in tree.query(geom, predicate="intersects"):
            code, zoning = shapes[index]
            intersection = geom.intersection(zoning)
            if intersection.area > 0:
                pieces[code or ""].append(intersection)
        ratios = {code: unary_union(parts).area / geom.area for code, parts in pieces.items()}
        matches = [code for code, ratio in ratios.items() if code and ratio >= COVERAGE
                   and all(other == code or share <= 1 - COVERAGE for other, share in ratios.items())]
        result["coverage"] = {code: round(ratio, 8) for code, ratio in ratios.items()}
        if len(matches) == 1:
            result["code"] = matches[0]
            return result
        return dict(result, reason="MUC_OVERLAP_UNRESOLVED")

    return overlap


def build(source, output, muc_zip=None, muc_edition=None, muc_downloaded_at=None):
    from jsonschema import Draft202012Validator

    rules = load_rules()
    schema_path = ROOT / "schemas/v1/zoning-area.schema.json"
    schema = read(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    class_path = ROOT / "vocabularies/land-classifications.json"
    use_path = ROOT / "vocabularies/land-uses.json"
    classes = {(item["id"], sub["id"]) for item in read(class_path)["classes"]
               for sub in item["categories"]}
    uses = {(item["id"], sub["id"]) for item in read(use_path)["uses"] for sub in item["subtypes"]}
    inputs = [Path(__file__), schema_path, class_path, use_path, HERE / "municipal-mappings.json",
              HERE / "planning-audit.json", HERE / "muc-pending-comparison.json"]
    if muc_zip:
        inputs.append(ROOT / "tests/compare_barcelona_muc.py")
    previous_muc = read(HERE / "muc-pending-comparison.json")
    muc_hash = digest(muc_zip.read_bytes()) if muc_zip else None
    if muc_zip:
        known_edition = previous_muc["mucSnapshot"]
        known_hash = previous_muc["mucArchiveSha256"]
        if (muc_edition == known_edition) != (muc_hash == known_hash):
            raise ValueError("MUC archive does not match the documented edition and checksum")
        if not muc_downloaded_at or datetime.fromisoformat(muc_downloaded_at).utcoffset() is None:
            raise ValueError("MUC download date must be an ISO-8601 timestamp with UTC offset")
    lookup = muc_lookup(muc_zip, muc_edition) if muc_zip else None
    records, audit, counts, index = [], [], Counter(), {}
    for feature, projected in load_capture(source):
        record, evidence = normalize_feature(feature, rules, None)
        counts["downloaded"] += 1
        if record and lookup and evidence["pending"].get("use") != "AMBIGUOUS_RULE" and "use" in evidence["pending"]:
            match = lookup(projected)
            record, evidence = normalize_feature(feature, rules, match)
        audit.append(evidence)
        if not record:
            counts["geometryRejected"] += 1
            continue
        if "geometryRepair" in evidence:
            counts["geometryRepaired"] += 1
        error = next(validator.iter_errors(record), None)
        if error:
            raise ValueError(f"{record['areaId']} {error.json_path}: {error.message}")
        records.append(record)
        counts["exported"] += 1
        classification = record.get("landClassification")
        use = record.get("characteristicUse")
        if classification:
            if (classification["class"], classification.get("category")) not in classes:
                raise ValueError("Classification outside SUPS vocabulary")
            counts["classificationMapped"] += 1
        if use:
            if (use["use"], use.get("subtype")) not in uses:
                raise ValueError("Use outside SUPS vocabulary")
            counts["useMuc" if use["provenance"]["sourceField"] == "C_QUAL_MUC" else "useAmb"] += 1
        index[record["areaId"]] = {
            "geometry": digest(encode(record["geometry"])),
            "classification": [classification["class"], classification.get("category")] if classification else None,
            "use": [use["use"], use.get("subtype")] if use else None,
            "pending": evidence["pending"],
        }
    if not records:
        raise ValueError("No valid Zoning Areas")
    for field in ("geometryRejected", "geometryRepaired", "classificationMapped", "useAmb", "useMuc"):
        counts.setdefault(field, 0)
    counts["useMapped"] = counts["useAmb"] + counts["useMuc"]
    pending = Counter((field, reason) for item in audit for field, reason in item["pending"].items())
    with ZipFile(source) as archive:
        meta = json.loads(archive.read("capture.json"))
    payload = {"sups-zoning-areas.json": encode(records), "zoning-audit.json": encode(audit)}
    previous = read(HERE / "planning-audit.json")
    baseline = {
        "downloaded": previous["amb"]["recordCount"],
        "classificationMapped": previous["amb"]["classificationSummary"]["DOCUMENTED"],
        "useAmb": previous["amb"]["useSummary"]["DOCUMENTED"],
        "useMuc": previous_muc["additionalUseMappings"],
    }
    historical_muc = {row["objectId"]: row for row in previous_muc["polygons"]}
    changed_muc = []
    if muc_zip:
        for item in audit:
            oid = item["original"]["OBJECTID"]
            historical = historical_muc.get(oid)
            current = item.get("muc")
            old_code = historical["mucCode"] if historical else None
            new_code = current["code"] if current else None
            if old_code != new_code:
                changed_muc.append({"objectId": oid, "before": old_code, "after": new_code,
                                    "geometryError": item.get("geometryError")})
    manifest = {"municipalityCode": "08019", "geometryCrs": "OGC:CRS84", "amb": meta,
                "ambArchiveSha256": digest(source.read_bytes()), "counts": dict(counts),
                "previousAudit": baseline, "differenceFromAudit": {k: counts[k] - v for k, v in baseline.items()},
                "pendingCounts": {f"{field}/{reason}": n for (field, reason), n in pending.items()},
                "inputs": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in inputs},
                "outputs": {name: digest(data) for name, data in payload.items()}, "areas": index}
    if muc_zip:
        manifest["muc"] = {"edition": muc_edition, "archiveSha256": muc_hash,
                           "source": previous_muc["mucSource"], "downloadedAt": muc_downloaded_at,
                           "filter": WHERE, "syntheticCodeField": "C_QUAL_MUC",
                           "minimumCoverage": 0.99, "maximumOtherCodeCoverage": 0.01,
                           "intersectionCrs": "EPSG:25831", "changesFromPreviousAudit": changed_muc}
    payload["manifest.json"] = encode(manifest)
    with ZipFile(output, "w") as archive:
        for name, data in payload.items():
            put(archive, name, data)
        put(archive, "amb-source.zip", source.read_bytes())
        if muc_zip:
            put(archive, "muc-source.zip", muc_zip.read_bytes())
    return dict(counts)


def compare(old, new):
    def manifest(path):
        with ZipFile(path) as archive:
            return json.loads(archive.read("manifest.json"))

    before, after = manifest(old), manifest(new)
    left, right = before["areas"], after["areas"]
    common = sorted(left.keys() & right.keys())
    return {
        "added": sorted(right.keys() - left.keys()), "removed": sorted(left.keys() - right.keys()),
        **{field: {area: {"before": left[area][field], "after": right[area][field]}
                   for area in common if left[area][field] != right[area][field]}
           for field in ("geometry", "classification", "use", "pending")},
        "pendingCounts": {"before": before["pendingCounts"], "after": after["pendingCounts"]},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    update = commands.add_parser("update")
    update.add_argument("--amb-source", type=Path)
    update.add_argument("--muc-zip", type=Path)
    update.add_argument("--muc-edition")
    update.add_argument("--muc-downloaded-at")
    update.add_argument("--output", type=Path, default=HERE / "barcelona-zoning.zip")
    diff = commands.add_parser("compare")
    diff.add_argument("old", type=Path)
    diff.add_argument("new", type=Path)
    args = parser.parse_args()
    if args.command == "compare":
        print(json.dumps(compare(args.old, args.new), ensure_ascii=False, indent=2))
        return
    if args.muc_zip and not (args.muc_downloaded_at and args.muc_edition
                             and re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.muc_edition)):
        parser.error("--muc-zip requires --muc-edition and --muc-downloaded-at")
    if args.muc_edition:
        datetime.strptime(args.muc_edition, "%Y-%m-%d")
    with TemporaryDirectory(dir=args.output.resolve().parent) as directory:
        stage = Path(directory)
        source = args.amb_source or stage / "amb-source.zip"
        if not args.amb_source:
            try:
                capture(source)
            except URLError as exc:
                parser.exit(1, f"AMB download failed: {exc.reason}\n")
        result = stage / "validated.zip"
        counts = build(source, result, args.muc_zip, args.muc_edition, args.muc_downloaded_at)
        os.replace(result, args.output)
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
