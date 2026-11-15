"""Build, compare and publish reproducible València SUPS Zoning Area releases."""

import argparse
import base64
from collections import Counter, defaultdict
from datetime import datetime
import json
from math import isclose
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from jsonschema import Draft202012Validator
from shapely import make_valid, normalize, orient_polygons, to_geojson
from shapely.errors import GEOSException
from shapely.geometry import shape
from shapely.validation import explain_validity

from capture_zoning import LAYER, OID, digest, encode, missing_geojson, read_capture

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CODE = "46250"
NAME = "València"
BUCKET = "goolzoom-sups-data"
REGION = "eu-west-3"
PREFIX = f"{CODE} - {NAME}"
DATASET = "sups-zoning-areas.json"
AUDIT = "zoning-audit.json"
SOURCE = "valencia-source.zip"
MANIFEST = "manifest.json"
CATALOGUE = HERE / "municipal-mappings.json"
PREVIOUS = HERE / "planning-audit.json"
SCHEMA = ROOT / "schemas/v1/zoning-area.schema.json"
CLASS_VOCAB = ROOT / "vocabularies/land-classifications.json"
USE_VOCAB = ROOT / "vocabularies/land-uses.json"
FIELDS = ("clase", "uso", "tipouso", "califi", "origen")


def read(path):
    return json.loads(path.read_bytes())


def code(value):
    return (value or "").strip()


def vocabulary(path, group, values):
    return {row["id"]: {item["id"] for item in row[values]} for row in read(path)[group]}


def load_rules():
    catalogue = read(CATALOGUE)
    if (catalogue["municipalityCode"], catalogue["sourceLayer"]) != (CODE, LAYER):
        raise ValueError("Catálogo de otro municipio o capa")
    rules, reasons = defaultdict(list), defaultdict(list)
    ids = set()
    classes = vocabulary(CLASS_VOCAB, "classes", "categories")
    uses = vocabulary(USE_VOCAB, "uses", "subtypes")
    for rule in catalogue["rules"]:
        field = rule["sourceField"]
        if field == "clase":
            valid = rule["normalizedCategory"] in classes[rule["normalizedClass"]]
        else:
            valid = (field in ("califi", "uso") and rule["normalizedSubtype"] in uses[rule["normalizedUse"]])
        if not valid or not rule["evidence"] or rule["mappingId"] in ids:
            raise ValueError(f"Equivalencia inválida: {rule}")
        ids.add(rule["mappingId"])
        rules[field, rule["originalCode"]].append(rule)
    for rule in catalogue["pendingRules"]:
        reasons[rule["sourceField"], rule["originalCode"]].append(rule)
    return rules, reasons, classes, uses


def matches(rule, attrs):
    return all(attrs[key] == value for key, value in rule["conditions"].items())


def select(index, reasons, field, attrs):
    original = attrs[field]
    candidates = index.get((field, original), ())
    applicable = [rule for rule in candidates if matches(rule, attrs)]
    best = [rule for rule in applicable if not any(
        rule["conditions"].items() < other["conditions"].items() for other in applicable)]
    if len(best) == 1:
        return best[0], None
    reason = "AMBIGUOUS_RULE" if best else "NO_APPLICABLE_RULE" if candidates else (
        "UNMAPPED_CODE" if original else "MISSING_CODE")
    pending = {"field": field, "code": original, "origin": attrs["origen"], "reason": reason}
    if not best:
        documented = [rule for rule in reasons.get((field, original), ()) if matches(rule, attrs)]
        if len(documented) == 1:
            pending.update({key: documented[0][key] for key in ("reason", "evidence") if key in documented[0]})
    else:
        pending["mappingIds"] = sorted(rule["mappingId"] for rule in best)
    return None, pending


def normalize_attributes(original, rules, reasons):
    attrs = {key: code(original[key]) for key in FIELDS}
    classification, class_pending = select(rules, reasons, "clase", attrs)
    field = "uso" if attrs["uso"] else "califi"
    use, use_pending = select(rules, reasons, field, attrs)
    land = {"class": "UNKNOWN", "category": "UNKNOWN", "jurisdiction": CODE,
            "mappingStatus": "REQUIRES_REVIEW", "originalCode": attrs["clase"]}
    characteristic = {"use": "UNKNOWN", "subtype": "UNKNOWN", "mappingStatus": "REQUIRES_REVIEW",
                      "originalCode": attrs[field]}
    if attrs[field]:
        provenance = {"sourceField": field, "originalCode": attrs[field],
                      "basis": "PUBLISHED_USE" if field == "uso" else "ZONING_DESIGNATION"}
        if attrs["origen"]:
            provenance["planningInstrument"] = attrs["origen"]
        characteristic["provenance"] = provenance
    if classification:
        land.update({"class": classification["normalizedClass"], "category": classification["normalizedCategory"],
                     "originalClass": classification["originalLabel"], "sourceDocumentId": classification["evidence"],
                     "mappingId": classification["mappingId"], "mappingStatus": "VERIFIED"})
    if use:
        characteristic.update(use=use["normalizedUse"], subtype=use["normalizedSubtype"],
                              mappingId=use["mappingId"], mappingStatus="VERIFIED")
    pending = {field: value for field, value in (("classification", class_pending), ("use", use_pending)) if value}
    return land, characteristic, pending, {field: rule for field, rule in (
        ("classification", classification), ("use", use)) if rule}


def polygon(raw):
    if not raw or raw.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError("Geometría ausente o no poligonal")
    geom = shape(raw)
    if geom.is_empty:
        raise ValueError("Geometría vacía")
    west, south, east, north = geom.bounds
    if not (-1 < west <= east < 1 and 38 < south <= north < 41):
        raise ValueError(f"Coordenadas fuera del entorno municipal en EPSG:4326: {geom.bounds}")
    repair = None
    if not geom.is_valid:
        issue = explain_validity(geom)
        repaired = make_valid(geom)
        if (repaired.geom_type not in ("Polygon", "MultiPolygon") or not repaired.is_valid
                or repaired.is_empty or repaired.area <= 0 or not isclose(geom.area, repaired.area, rel_tol=1e-8)):
            raise ValueError(issue)
        repair = {"method": "GEOS make_valid (linework)", "issue": issue,
                  "relativeAreaChange": abs(geom.area - repaired.area) / geom.area}
        geom = repaired
    if geom.area <= 0 or geom.has_z:
        raise ValueError("Geometría sin superficie positiva o con una dimensión inesperada")
    return json.loads(to_geojson(orient_polygons(normalize(geom)))), repair


def file_info(path):
    return {"sha256": digest(path.read_bytes()), "bytes": path.stat().st_size}


def build(source, output):
    if output.exists():
        raise FileExistsError(output)
    source_fingerprint = file_info(source)
    capture, features = read_capture(source)
    if file_info(source) != source_fingerprint:
        raise ValueError("La copia fuente cambió durante la lectura")
    rules, reasons, classes, uses = load_rules()
    schema = read(SCHEMA)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    coverage = Counter(downloaded=len(features), exported=0, geometryRejected=0, geometryRepaired=0,
                       classDocumented=0, useDocumented=0, classDocumentedSource=0, useDocumentedSource=0)
    old = read(PREVIOUS)
    old_groups = {tuple(row["original"][key] for key in FIELDS): row["recordCount"] for row in old["groups"]}
    groups = Counter()
    pending_counts = Counter()
    use_fields = Counter()
    records, audit, areas = [], [], {}
    for feature in features:
        attrs = feature["properties"]
        groups[tuple(attrs[key] for key in FIELDS)] += 1
        area_id = f"{CODE}-pgou231-{attrs[OID]}"
        land, use, pending, mapping = normalize_attributes(attrs, rules, reasons)
        known_class = land["class"] != "UNKNOWN"
        known_use = use["use"] != "UNKNOWN"
        coverage["classDocumentedSource"] += known_class
        coverage["useDocumentedSource"] += known_use
        if known_use:
            use_fields[use["provenance"]["sourceField"]] += 1
        item = {"areaId": area_id, "sourceId": attrs[OID], "original": attrs, "pending": pending,
                "evidence": {key: {"mappingId": rule["mappingId"], "url": rule["evidence"]}
                             for key, rule in mapping.items()}}
        audit.append(item)
        entry = {"pending": pending}
        areas[area_id] = entry
        try:
            geometry, repair = polygon(feature.get("geometry"))
        except (ValueError, TypeError, GEOSException) as error:
            item["geometryRejected"] = entry["geometryRejected"] = str(error)
            if missing_geojson(feature):
                item["geometryEvidence"] = "ArcGIS JSON sin anillos en EPSG:25830; consulta archivada en native-page-*.json"
            coverage["geometryRejected"] += 1
            continue
        if repair:
            item["geometryRepair"] = repair
            coverage["geometryRepaired"] += 1
        record = {"schemaVersion": "1.0", "areaId": area_id, "areaType": "MIXED", "regulationIds": [],
                  "geometry": geometry, "landClassification": land, "characteristicUse": use}
        validator.validate(record)
        if land["category"] not in classes[land["class"]] or use["subtype"] not in uses[use["use"]]:
            raise ValueError(f"Valor fuera del vocabulario SUPS: {area_id}")
        records.append(record)
        entry.update(geometry=digest(encode(geometry)), classification=[land["class"], land["category"]],
                     use=[use["use"], use["subtype"]])
        for domain, detail in pending.items():
            pending_counts[domain, detail["field"], detail["code"], detail["origin"], detail["reason"]] += 1
        coverage["exported"] += 1
        coverage["classDocumented"] += known_class
        coverage["useDocumented"] += known_use
    if not records or len(areas) != len(features) or len(records) + coverage["geometryRejected"] != len(features):
        raise ValueError("El inventario SUPS no concuerda con la extracción")
    comparison = {"extractedAt": old["extractedAt"], "downloaded": old["recordCount"],
                  "classDocumented": old["classificationSummary"]["DOCUMENTED"],
                  "useDocumented": old["useSummary"]["DOCUMENTED"], "useByField": dict(use_fields),
                  "previousUseByField": old["documentedUseBySourceField"],
                  "changedGroups": [{"original": dict(zip(FIELDS, key)), "before": old_groups.get(key, 0),
                                     "after": groups[key]} for key in sorted(groups.keys() | old_groups.keys(), key=repr)
                                    if groups[key] != old_groups.get(key, 0)]}
    dates = [value for feature in features if (value := feature["properties"]["fecha_valor"]) is not None]
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as scratch:
        stage = Path(scratch) / "release"
        stage.mkdir()
        (stage / DATASET).write_bytes(encode(records))
        (stage / AUDIT).write_bytes(encode({"areas": audit, "coverage": coverage, "previousAudit": comparison,
                                          "pendingExported": [
                                              dict(zip(("domain", "field", "code", "origin", "reason", "count"),
                                                       (*key, count)))
                                              for key, count in sorted(pending_counts.items(),
                                                                       key=lambda item: (-item[1], item[0]))],
                                          "sourceFeatureDates": {"field": "fecha_valor", "populated": len(dates),
                                                                 "min": min(dates, default=None),
                                                                 "max": max(dates, default=None)}}))
        objects = {name: file_info(stage / name) for name in (DATASET, AUDIT)}
        objects[SOURCE] = source_fingerprint
        inputs = {path.relative_to(ROOT).as_posix(): file_info(path)["sha256"] for path in (
            CATALOGUE, PREVIOUS, SCHEMA, CLASS_VOCAB, USE_VOCAB, Path(__file__).resolve(),
            HERE / "capture_zoning.py")}
        stamp = datetime.fromisoformat(capture["startedAt"]).strftime("%Y%m%dT%H%M%SZ")
        version = f"{stamp}-{digest(encode([objects, inputs]))[:16]}"
        uri = f"s3://{BUCKET}/{PREFIX}/{version}/"
        manifest = {"version": version, "municipalityCode": CODE, "municipality": NAME, "schemaVersion": "1.0",
                    "source": capture, "objects": objects, "inputs": inputs, "areas": areas, "coverage": coverage,
                    "s3Uri": uri, "attribution": "Fuente: Ajuntament de València, Geoportal",
                    "geometryCrs": "OGC:CRS84"}
        (stage / MANIFEST).write_bytes(encode(manifest))
        stage.rename(output)
    return manifest


def diff(old, new):
    if any(item["municipalityCode"] != CODE for item in (old, new)):
        raise ValueError("Se requieren dos manifiestos de València")
    before, after = old["areas"], new["areas"]
    common = before.keys() & after.keys()
    result = {key: sorted(ids) for key, ids in (
        ("added", after.keys() - before.keys()), ("removed", before.keys() - after.keys()),
        ("exportedAdded", {key for key, area in after.items() if "geometry" in area}
         - {key for key, area in before.items() if "geometry" in area}),
        ("exportedRemoved", {key for key, area in before.items() if "geometry" in area}
         - {key for key, area in after.items() if "geometry" in area}))}
    for field in ("geometry", "classification", "use", "pending", "geometryRejected"):
        result[field] = sorted(key for key in common if before[key].get(field) != after[key].get(field))
    result["pendingTotals"] = {domain: [sum(domain in entry["pending"] for entry in version.values())
                                       for version in (before, after)] for domain in ("classification", "use")}
    return result


def verified_paths(source, directory):
    manifest_path = directory / MANIFEST
    manifest = read(manifest_path)
    version = manifest["version"]
    prefix = f"{PREFIX}/{version}"
    if (manifest["municipalityCode"] != CODE or not re.fullmatch(r"\d{8}T\d{6}Z-[a-f0-9]{16}", version)
            or manifest["s3Uri"] != f"s3://{BUCKET}/{prefix}/"):
        raise ValueError("Destino del manifiesto incorrecto")
    paths = {DATASET: directory / DATASET, AUDIT: directory / AUDIT, SOURCE: source}
    if manifest["objects"] != {name: file_info(path) for name, path in paths.items()}:
        raise ValueError("Los archivos locales no coinciden con el manifiesto")
    paths[MANIFEST] = manifest_path
    return prefix, paths


def publish(source, directory, profile):
    prefix, paths = verified_paths(source, directory)
    cli = ["aws", "--region", REGION, "--no-cli-pager"]
    if profile:
        cli.extend(["--profile", profile])
    with TemporaryDirectory() as scratch:
        received = Path(scratch) / "download"
        for name, path in paths.items():
            expected = file_info(path)
            checksum = base64.b64encode(bytes.fromhex(expected["sha256"])).decode()
            remote = ["--bucket", BUCKET, "--key", f"{prefix}/{name}"]
            result = subprocess.run(
                [*cli, "s3api", "put-object", *remote, "--body", str(path), "--if-none-match", "*",
                 "--checksum-sha256", checksum, "--content-type",
                 "application/zip" if name.endswith(".zip") else "application/json"], capture_output=True, text=True)
            if result.returncode and "PreconditionFailed" not in result.stderr:
                raise RuntimeError(result.stderr.strip())
            subprocess.run([*cli, "s3api", "get-object", *remote, str(received)],
                           check=True, stdout=subprocess.DEVNULL)
            if file_info(received) != expected:
                raise ValueError(f"El objeto de S3 difiere del fichero local: {name}")
    return f"s3://{BUCKET}/{prefix}/"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command, names in (("build", ("source", "output")), ("diff", ("old", "new")),
                           ("publish", ("source", "output"))):
        sub = commands.add_parser(command)
        for name in names:
            sub.add_argument(name, type=Path)
        if command == "publish":
            sub.add_argument("--profile")
    args = parser.parse_args()
    if args.command == "build":
        manifest = build(args.source, args.output)
        print(json.dumps({"s3Uri": manifest["s3Uri"], "coverage": manifest["coverage"]}, ensure_ascii=True))
    elif args.command == "diff":
        print(json.dumps(diff(read(args.old), read(args.new)), indent=2))
    else:
        print(publish(args.source, args.output, args.profile))


if __name__ == "__main__":
    main()
