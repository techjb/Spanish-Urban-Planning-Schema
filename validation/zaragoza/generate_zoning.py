"""Generate a reproducible SUPS release or compare two Zaragoza manifests."""
import argparse
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from jsonschema import Draft202012Validator, FormatChecker
from shapely import get_coordinates, is_valid_reason, make_valid, normalize, orient_polygons
from shapely.geometry import mapping, shape

from capture_zoning import FILTER, INE, LAYERS, PAGE_SIZE, check_page, encode, hits, source_key
from municipal_qualification import MunicipalUse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATASET = "sups-zoning-areas.json"
MUNICIPAL_DATASET = "sups-municipal-zoning-areas.json"
NON_URBAN_DATASET = "sups-municipal-non-urban-zoning-areas.json"
AUDIT = "zoning-audit.json"
SOURCES = "siua-source.zip"
MANIFEST = "manifest.json"
S3 = "s3://goolzoom-sups-data/50297 - Zaragoza"


def load(path):
    return json.loads(path.read_bytes())


def digest(data):
    return sha256(data).hexdigest()


def read_capture(directory):
    manifest = load(directory / "capture.json")
    if (manifest["municipalityCode"] != INE or manifest["filter"] != FILTER
            or set(manifest["layers"]) != set(LAYERS)):
        raise ValueError("Unexpected capture scope")

    def read(name):
        data = (directory / name).read_bytes()
        if digest(data) != manifest["files"][name]["sha256"]:
            raise ValueError(f"Source checksum mismatch: {name}")
        return data

    for name in manifest["files"]:
        read(name)
    layers = {}
    for layer, entry in manifest["layers"].items():
        total = entry["count"]
        offsets = range(0, total, PAGE_SIZE)
        if (total <= 0 or hits(read(entry["before"])) != total or hits(read(entry["after"])) != total
                or [page["offset"] for page in entry["pages"]] != list(offsets)):
            raise ValueError(f"{layer}: incomplete capture")
        features = []
        for page in entry["pages"]:
            expected = min(PAGE_SIZE, total - page["offset"])
            features.extend(check_page(read(page["file"]), layer, total, expected))
        inventory = check_page(read(entry["inventory"]), layer, total, total, attributes_only=True)
        keys = list(map(source_key, features))
        if keys != sorted(set(keys)) or keys != list(map(source_key, inventory)):
            raise ValueError(f"{layer}: duplicated or missing source keys")
        layers[layer] = dict(zip(keys, features))
    return manifest, layers


def geometry(feature):
    raw = feature["geometry"]
    if not raw or raw["type"] not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Missing or non-polygonal geometry")
    polygons = [raw["coordinates"]] if raw["type"] == "Polygon" else raw["coordinates"]
    if any(not rings or any(len(ring) < 4 or ring[0] != ring[-1] for ring in rings)
           for rings in polygons):
        raise ValueError("Malformed polygon rings")
    geom = shape(raw)
    coordinates = get_coordinates(geom)
    if (geom.is_empty or geom.has_z or geom.has_m
            or not ((coordinates[:, 0] >= -180) & (coordinates[:, 0] <= 180)
                    & (coordinates[:, 1] >= -90) & (coordinates[:, 1] <= 90)).all()):
        raise ValueError("Empty geometry or invalid CRS84 coordinates")
    repair = None
    if not geom.is_valid:
        repair = is_valid_reason(geom)
        geom = make_valid(geom)
        if geom.geom_type not in {"Polygon", "MultiPolygon"} or geom.is_empty or not geom.is_valid:
            raise ValueError(f"{repair}; make_valid returned {geom.geom_type}")
    return mapping(orient_polygons(normalize(geom))), repair


def classification(props, catalog):
    spec = catalog["classification"]
    code = "|".join(str(props[field] or "") for field in spec["fields"])
    rule = spec["rules"].get(code)
    result = {"class": "UNKNOWN", "originalClass": props["clase_s"] or "",
              "originalCategory": props["clase"] or "", "originalCode": props["notepa"] or "",
              "jurisdiction": "ES-AR", "mappingStatus": "REQUIRES_REVIEW"}
    if not matches(props, catalog["conditions"]):
        return result, "Instrumento, expediente u origen fuera del catálogo"
    if not rule:
        return result, "Combinación de claves nueva o contradictoria"
    return dict(result, **{"class": rule[0]}, category=rule[1], mappingStatus="VERIFIED",
                mappingId=f"50297:classification:{code}"), None


def matches(props, conditions):
    return all(props[field] == value for field, value in conditions.items())


def use(props, catalog):
    spec = catalog["use"]
    code = props[spec["field"]]
    result = {"use": "UNKNOWN", "mappingStatus": "REQUIRES_REVIEW"}
    if code:
        provenance = {"sourceField": spec["field"], "originalCode": code, "basis": "PUBLISHED_USE"}
        if props["n_expedien"]:
            provenance["planningInstrument"] = props["n_expedien"]
        result.update(originalCode=code, provenance=provenance)
    if not code:
        return result, "El SIUa no publica uso global para el polígono"
    rule = spec["rules"].get(code)
    if not matches(props, catalog["conditions"]):
        return result, "Instrumento, expediente u origen fuera del catálogo"
    if not rule:
        return result, spec["pending"].get(code, "Clave nueva sin equivalencia")
    if not matches(props, {key: value for key, value in rule.items() if key != "use"}):
        return result, "Clave fuera de las condiciones de la regla"
    return dict(result, use=rule["use"], mappingStatus="VERIFIED", mappingId=f"50297:use:{code}"), None


def municipal_dataset(municipal, validator, uses):
    records, inventory, pending, rejected = [], {}, {}, {}
    seen = set()
    field = municipal.spec["sourceField"]
    for feature, rule in zip(municipal.features, municipal.rules):
        props = feature["properties"]
        code = props[field]
        evidence = {"layer": municipal.metadata["layer"], "sourceId": feature["id"],
                    "properties": props}
        try:
            geom, repair = geometry(feature)
        except ValueError as error:
            rejected[feature["id"]] = str(error)
            continue
        geometry_hash = digest(encode(geom))
        area_id = f"50297:IDEZar:Calificaciones_Urbanas:{geometry_hash}"
        if area_id in seen:
            raise ValueError("Duplicated municipal polygon; review identity before publication")
        seen.add(area_id)
        if repair:
            evidence["geometryRepair"] = repair
        characteristic = {"use": "UNKNOWN", "mappingStatus": "REQUIRES_REVIEW"}
        if code:
            characteristic.update(originalCode=code, provenance={
                "sourceField": field, "originalCode": code, "basis": "ZONING_DESIGNATION"})
        if rule:
            characteristic.update(use=rule[0], mappingStatus="VERIFIED",
                                  mappingId=f"50297:municipal:{code}")
            characteristic["provenance"]["planningInstrument"] = municipal.spec["instrument"]
            evidence["ruleEvidence"] = rule[1]
        else:
            reason = municipal.spec["nativePending"].get(code, "Clave sin regla aplicable")
            pending[area_id] = {"use": reason}
        record = {"schemaVersion": "1.0", "areaId": area_id, "areaType": "ZONING",
                  "geometry": geom, "regulationIds": [], "characteristicUse": characteristic,
                  "sourceEvidence": evidence}
        validator.validate(json.loads(encode(record)))
        if characteristic["use"] not in uses:
            raise ValueError(f"Invalid municipal use vocabulary: {area_id}")
        records.append(record)
        inventory[area_id] = {"geometry": geometry_hash, "classification": None,
                              "use": characteristic, "pending": pending.get(area_id, {})}
    records.sort(key=lambda record: record["areaId"])
    counts = {"downloaded": len(municipal.features), "exported": len(records),
              "geometryRejected": len(rejected), "pendingAreas": len(pending),
              "useVerified": len(records) - len(pending),
              "uses": dict(Counter(record["characteristicUse"]["use"] for record in records))}
    if not records or len(records) + len(rejected) != counts["downloaded"]:
        raise ValueError("Inconsistent municipal zoning counts")
    return encode(records), {"counts": counts, "areas": inventory}, {
        "counts": counts, "pending": pending, "geometryRejections": rejected}


def generate(directory, output, catalog_path, municipal_directory=None):
    capture, layers = read_capture(directory)
    municipal = MunicipalUse(municipal_directory) if municipal_directory else None
    catalog = load(catalog_path)
    class_name, use_name = LAYERS
    if (catalog["municipalityCode"] != INE or catalog["classification"]["layer"] != class_name
            or catalog["use"]["layer"] != use_name):
        raise ValueError("Mappings target incompatible layers")
    primary, secondary = layers[class_name], layers[use_name]
    if primary.keys() != secondary.keys():
        raise ValueError("SIUa layers have different inventories; review their relationship")
    counts = Counter(key[0] for key in primary)
    known_duplicates = set(catalog["nonUniqueObjectIds"])
    if {key for key, count in counts.items() if count > 1} - known_duplicates:
        raise ValueError("New duplicated objectid; review identity before publication")
    validator = Draft202012Validator(load(ROOT / "schemas/v1/zoning-area.schema.json"),
                                     format_checker=FormatChecker())
    classes = {item["id"]: {c["id"] for c in item["categories"]}
               for item in load(ROOT / "vocabularies/land-classifications.json")["classes"]}
    uses = {item["id"] for item in load(ROOT / "vocabularies/land-uses.json")["uses"]}
    records, inventory, pending, repairs, rejected = [], {}, {}, {}, {}
    municipal_audit = {}
    matched_geometry = 0
    for key, feature in primary.items():
        zoning = secondary[key]
        class_props, use_props = feature["properties"], zoning["properties"]
        raw = feature["geometry"]
        if raw != zoning["geometry"]:
            raise ValueError(f"SIUa geometries differ for source key {key}")
        matched_geometry += 1
        object_id = key[0]
        area_id = f"50297:SIUa:{object_id}"
        if object_id in known_duplicates:
            area_id += ":" + digest(encode(key))[:16]
        evidence = {"sourceKey": key, "classification": class_props, "use": use_props}
        try:
            geom, repair = geometry(feature)
        except ValueError as error:
            rejected[area_id] = {"reason": str(error), "sourceKey": key}
            continue
        if repair:
            repairs[area_id] = repair
        land, class_reason = classification(class_props, catalog)
        characteristic, use_reason = use(use_props, catalog)
        if municipal and use_reason:
            municipal_use, details = municipal.resolve(geom, land, use_props["uso_glob"])
            if details is not None:
                municipal_audit[area_id] = details
            if municipal_use:
                characteristic, use_reason = municipal_use, None
                evidence["municipalQualification"] = details
        if class_reason or use_reason:
            pending[area_id] = {dimension: reason for dimension, reason in
                                (("classification", class_reason), ("use", use_reason)) if reason}
        record = {"schemaVersion": "1.0", "areaId": area_id, "areaType": "MIXED",
                  "geometry": geom, "regulationIds": [], "landClassification": land,
                  "characteristicUse": characteristic, "sourceEvidence": evidence}
        validator.validate(json.loads(encode(record)))
        if (land["class"] not in classes or land.get("category", "UNKNOWN")
                not in classes[land["class"]] or characteristic["use"] not in uses):
            raise ValueError(f"Invalid SUPS vocabulary: {area_id}")
        records.append(record)
        inventory[area_id] = {"geometry": digest(encode(geom)), "classification": land,
                              "use": characteristic, "pending": pending.get(area_id, {})}
    if not records or len(records) != len(inventory):
        raise ValueError("Empty dataset or duplicated SUPS IDs")
    records.sort(key=lambda record: record["areaId"])
    metrics = {"downloadedByLayer": {layer: len(features) for layer, features in layers.items()},
               "uniqueSourceZones": len(primary), "exported": len(records),
               "geometryRejected": len(rejected), "geometryRepaired": len(repairs),
               "pendingAreas": len(pending),
               "classificationVerified": sum("classification" not in item["pending"] for item in inventory.values()),
               "useVerified": sum("use" not in item["pending"] for item in inventory.values())}
    audit = {"counts": metrics, "pending": pending, "geometryRejections": rejected, "geometryRepairs": repairs,
             "crossCheck": {"method": "Exact GeoJSON equality on objectid, shape_area, shape_le_1",
                            "matchedGeometries": matched_geometry,
                            "matchedFullAttributes": sum(f["properties"] == secondary[key]["properties"]
                                                         for key, f in primary.items())},
             "priorAudit": "Five Zaragoza ordinance-grade samples; no geographic coverage baseline.",
             "duplicateObjectIds": {key: count for key, count in counts.items() if count > 1},
             "referenceDates": {field: sorted({str(f["properties"][field]) for f in primary.values()})
                                for field in ("date_acu", "inicio", "fin", "control", "n_expedien", "cod_plan")}}
    if municipal:
        metrics["useVerifiedMunicipal"] = sum(
            item["decision"] == "Uso municipal verificado" for item in municipal_audit.values())
        audit["municipalQualification"] = {
            "method": "STRtree polygon intersection and union by use; area fractions in CRS84",
            "minimumCoverage": municipal.spec["minimumCoverage"],
            "maximumCompetingCoverage": municipal.spec["maximumCompetingCoverage"],
            "source": municipal.metadata, "areas": municipal_audit,
        }
        native_data, native_inventory, native_audit = municipal_dataset(municipal, validator, uses)
        audit["municipalZoningAreas"] = native_audit
    data, audit_data = encode(records), encode(audit)
    times = [datetime.fromisoformat(capture["capturedAt"])]
    hashes = [capture, digest(data), digest(audit_data), digest(catalog_path.read_bytes())]
    if municipal:
        times.append(datetime.fromisoformat(municipal.metadata["responseTime"]))
        hashes.extend((digest(municipal.catalog_bytes), digest(native_data)))
    stamp = max(times).strftime("%Y%m%dT%H%M%SZ")
    revision = digest(encode(hashes))
    version = f"{stamp}-{revision[:16]}"
    destination = output / version
    destination.mkdir(parents=True)
    with ZipFile(destination / SOURCES, "w", compression=ZIP_DEFLATED) as archive:
        for name in sorted((*capture["files"], "capture.json")):
            archive.writestr(ZipInfo(name), (directory / name).read_bytes(), compress_type=ZIP_DEFLATED)
        if municipal:
            for name in sorted((*municipal.metadata["files"], "capture.json")):
                archive.writestr(ZipInfo(f"municipal/{name}"), (municipal_directory / name).read_bytes(),
                                 compress_type=ZIP_DEFLATED)
            archive.writestr(ZipInfo("municipal/municipal-use-mappings.json"), municipal.catalog_bytes,
                             compress_type=ZIP_DEFLATED)
    contents = {DATASET: data, AUDIT: audit_data, SOURCES: (destination / SOURCES).read_bytes()}
    if municipal:
        contents[MUNICIPAL_DATASET] = native_data
    manifest = {"municipalityCode": INE, "version": version, "s3Uri": f"{S3}/{version}/",
                "attribution": "Gobierno de Aragón · IGEAR · Sistema de Información Urbanística de Aragón (SIUa)",
                "sourceLicense": "CC-BY-4.0", "sourceTerms": catalog["sourceTerms"],
                "processing": "SUPS normalization, polygon orientation and two-dimensional CRS84 geometry validation",
                "source": capture, "referenceDates": audit["referenceDates"], "counts": metrics,
                "mappingsSha256": digest(catalog_path.read_bytes()), "areas": inventory,
                "objects": {name: {"bytes": len(body), "sha256": digest(body)} for name, body in contents.items()}}
    if municipal:
        manifest["municipalQualification"] = dict(municipal.metadata, **{
            key: municipal.spec[key] for key in ("sourceTerms", "sourceLicense", "licenseReference", "norms")
        })
        manifest["municipalMappingsSha256"] = digest(municipal.catalog_bytes)
        manifest["processing"] += "; municipal zoning enrichment by polygon overlap"
        manifest["municipalZoningAreas"] = dict(native_inventory, file=MUNICIPAL_DATASET)
    for name, body in contents.items():
        if name != SOURCES:
            (destination / name).write_bytes(body)
    (destination / MANIFEST).write_bytes(encode(manifest))
    print(destination)
    print(json.dumps(metrics))
    return destination


def compare(old, new):
    if old["municipalityCode"] != INE or new["municipalityCode"] != INE:
        raise ValueError("Both manifests must describe Zaragoza")
    result = compare_inventory(old, new)
    empty = {"areas": {}, "counts": {"pendingAreas": 0}}
    for field in ("municipalZoningAreas", "nonUrbanZoningAreas"):
        if field in old or field in new:
            result[field] = compare_inventory(old.get(field, empty), new.get(field, empty))
    return result


def compare_inventory(old, new):
    before, after = old["areas"], new["areas"]
    shared = sorted(before.keys() & after.keys())
    return {"added": sorted(after.keys() - before.keys()),
            "removed": sorted(before.keys() - after.keys()),
            "changed": {field: [key for key in shared if before[key][field] != after[key][field]]
                        for field in ("geometry", "classification", "use", "pending")},
            "pendingBefore": old["counts"]["pendingAreas"], "pendingAfter": new["counts"]["pendingAreas"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("generate")
    build.add_argument("capture", type=Path)
    build.add_argument("output", type=Path)
    build.add_argument("--catalog", type=Path, default=HERE / "municipal-mappings.json")
    build.add_argument("--municipal", type=Path)
    diff = sub.add_parser("compare")
    diff.add_argument("old", type=Path)
    diff.add_argument("new", type=Path)
    args = parser.parse_args()
    if args.command == "generate":
        generate(args.capture, args.output, args.catalog, args.municipal)
    else:
        print(encode(compare(load(args.old), load(args.new))).decode(), end="")
