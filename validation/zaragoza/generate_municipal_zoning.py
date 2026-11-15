"""Build the primary Zaragoza SUPS release from three municipal WFS layers."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from jsonschema import Draft202012Validator, FormatChecker
from shapely import STRtree, union_all
from shapely.geometry import shape

from audit_classification_conflict import CONFLICT_ID, derive
from capture_zoning import INE, encode
from generate_zoning import (
    AUDIT, DATASET, HERE, MANIFEST, MUNICIPAL_DATASET, NON_URBAN_DATASET, ROOT, S3,
    digest, geometry, load, municipal_dataset,
)
from municipal_qualification import CATALOG, CLASS_LAYER, NON_URBAN_LAYER, MunicipalUse, read_snapshot

CLASS_CATALOG = HERE / "municipal-classification-mappings.json"
SOURCES = "municipal-sources.zip"
REGIONAL_BASELINE = "regional-contrast.json"


def source_records(features, layer, spec, validator, classes):
    is_class = layer == CLASS_LAYER
    records, inventory, rejected, repaired = [], {}, {}, {}
    counts_by_key = Counter()
    groups = defaultdict(list)
    field = spec["field"] if is_class else "calificacion"
    for feature in features:
        props = feature["properties"]
        code = props[field]
        counts_by_key[code or ""] += 1
        evidence = {"layer": f"urbanismo:{layer}", "sourceId": feature["id"], "properties": props}
        try:
            geom, repair = geometry(feature)
        except ValueError as error:
            rejected[feature["id"]] = {"code": code, "reason": str(error)}
            continue
        fingerprint = digest(encode(geom))
        area_id = f"{INE}:IDEZar:{layer}:{fingerprint}"
        if repair:
            repaired[area_id] = repair
        groups[area_id].append((fingerprint, geom, evidence))

    duplicates = {}
    for area_id, group in groups.items():
        fingerprint, geom, evidence = group[0]
        props = evidence["properties"]
        code = props[field]
        conflict = len({encode(item[2]["properties"]) for item in group}) > 1
        if len(group) > 1:
            duplicates[area_id] = {"conflictingAttributes": conflict,
                                   "sourceFeatures": [item[2] for item in group]}
            evidence = {"layer": f"urbanismo:{layer}", **duplicates[area_id]}
        record = {"schemaVersion": "1.0", "areaId": area_id, "geometry": geom,
                  "regulationIds": [], "sourceEvidence": evidence}
        classification = use = None
        pending = {}
        if is_class:
            codes = sorted({item[2]["properties"][field] or "" for item in group})
            classification = {"class": "UNKNOWN", "originalCode": "|".join(codes),
                              "jurisdiction": spec["jurisdiction"], "mappingStatus": "REQUIRES_REVIEW"}
            if not conflict:
                classification["originalClass"] = props["descripcion"] or code or ""
            rule = spec["rules"].get(code) if all(
                props[key] == expected for key, expected in spec["conditions"].items()) and not conflict else None
            if rule:
                if rule[0] not in classes or rule[1] not in classes[rule[0]]:
                    raise ValueError(f"Unknown SUPS class or category: {rule}")
                classification.update({"class": rule[0], "category": rule[1], "mappingStatus": "VERIFIED",
                                       "mappingId": f"{INE}:municipal-classification:{code}"})
            else:
                pending["classification"] = ("Geometría idéntica con clasificaciones contradictorias."
                                              if conflict else spec["pending"].get(
                                                  code, "Clave o atributos sin regla aplicable."))
            record.update(areaType="LAND_CLASSIFICATION", landClassification=classification)
        else:
            use = {"use": "UNKNOWN", "mappingStatus": "REQUIRES_REVIEW"}
            if code and not conflict:
                use.update(originalCode=code, provenance={"sourceField": field, "originalCode": code,
                                                         "basis": "ZONING_DESIGNATION"})
            pending["use"] = ("Geometría idéntica con calificaciones contradictorias." if conflict
                              else spec["nonUrbanQualificationPending"])
            record.update(areaType="ZONING", characteristicUse=use)
        validator.validate(json.loads(encode(record)))
        records.append(record)
        inventory[area_id] = {"geometry": fingerprint, "classification": classification,
                              "use": use, "pending": pending}
    records.sort(key=lambda record: record["areaId"])
    merged = sum(len(group) - 1 for group in groups.values())
    if not records or len(records) + len(rejected) + merged != len(features):
        raise ValueError(f"Inconsistent source counts: {layer}")
    pending = {area_id: item["pending"] for area_id, item in inventory.items() if item["pending"]}
    verified = "classificationVerified" if is_class else "useVerified"
    counts = {"downloaded": len(features), "exported": len(records), "geometryRejected": len(rejected),
              "geometryRepaired": len(repaired), "mergedSourceRows": merged,
              "pendingAreas": len(pending), verified: len(records) - len(pending)}
    return records, {"counts": counts, "areas": inventory}, {
        "counts": counts, "sourceKeyCounts": counts_by_key, "pending": pending,
        "geometryRejections": rejected, "geometryRepairs": repaired, "duplicateGeometries": duplicates}


def spatial_contrast(municipal, regional):
    regional_geoms = [shape(record["geometry"]) for record in regional]
    labels = [record["landClassification"]["class"] for record in regional]
    tree = STRtree(regional_geoms)
    municipal_geoms = [shape(record["geometry"]) for record in municipal]
    municipal_union, regional_union = union_all(municipal_geoms), union_all(regional_geoms)
    common_area = municipal_union.intersection(regional_union).area
    verified_footprint = union_all([geom for record, geom in zip(municipal, municipal_geoms)
                                    if record["landClassification"]["mappingStatus"] == "VERIFIED"])
    proposed_footprint = union_all([geom for record, geom in zip(municipal, municipal_geoms)
                                   if record["landClassification"]["mappingStatus"] == "PROPOSED"])
    pending_footprint = union_all([geom for record, geom in zip(municipal, municipal_geoms)
                                   if record["landClassification"]["class"] == "UNKNOWN"])
    details = {}
    class_pairs = defaultdict(list)
    for record, geom in zip(municipal, municipal_geoms):
        by_class = defaultdict(list)
        land = record["landClassification"]
        for index in tree.query(geom, predicate="intersects"):
            intersection = geom.intersection(regional_geoms[index])
            if intersection.area > 0:
                by_class[labels[index]].append(intersection)
        for label, parts in by_class.items():
            class_pairs[(land["class"], label)].extend(parts)
        conflict = union_all([part for label, parts in by_class.items()
                              if label not in {"UNKNOWN", land["class"]} for part in parts])
        details[record["areaId"]] = {
            "municipalCode": land["originalCode"], "municipalClass": land["class"],
            "regionalAreaByClass": {label: round(union_all(parts).area / geom.area, 8)
                                    for label, parts in by_class.items()},
            "differentKnownClass": round(conflict.area / geom.area, 8) if land["class"] != "UNKNOWN" else None,
        }
    matrix = defaultdict(dict)
    for (municipal_class, regional_class), parts in class_pairs.items():
        matrix[municipal_class][regional_class] = round(100 * union_all(parts).area / common_area, 6)
    result = {"method": "CRS84 planar polygon intersections; union before area by class pair. "
                      "Class pairs can overlap when source classes overlap.",
            "municipalFootprintCoveredPct": round(100 * common_area / municipal_union.area, 6),
            "regionalFootprintCoveredPct": round(100 * common_area / regional_union.area, 6),
            "municipalFootprintVerifiedPct": round(100 * verified_footprint.area / municipal_union.area, 6),
            "municipalFootprintPendingOnlyPct": round(
                100 * pending_footprint.difference(verified_footprint).area / municipal_union.area, 6),
            "municipalFootprintVerifiedAndPendingPct": round(
                100 * pending_footprint.intersection(verified_footprint).area / municipal_union.area, 6),
            "classPairPctOfCommonFootprint": matrix,
            "polygonsWithDifferentKnownClassAboveOnePct": sum(
                (item["differentKnownClass"] or 0) > 0.01 for item in details.values()),
            "areas": details}
    if not proposed_footprint.is_empty:
        result["municipalFootprintProposedPct"] = round(100 * proposed_footprint.area / municipal_union.area, 6)
    return result


def apply_conflict_proposal(records, inventory, audit, non_urban_raw, regional_raw, validator):
    conflict = next((record for record in records if record["areaId"] == CONFLICT_ID), None)
    if conflict is None:
        raise ValueError("Expected conflict geometry changed; review evidence before applying the proposal")
    evidence, protected, residual = derive(conflict, non_urban_raw, regional_raw)
    if not protected["coordinates"] or not residual["coordinates"]:
        raise ValueError("Conflict split no longer has both expected pieces")
    replacements = {}
    pieces = (
        ("proposed", protected, {"class": "NON_DEVELOPABLE", "category": "PROTECTED",
                                "mappingStatus": "PROPOSED", "mappingId": f"{INE}:municipal-classification:conflict-proposal"},
         {}),
        ("residual", residual, {"class": "UNKNOWN", "mappingStatus": "REQUIRES_REVIEW"},
         {"classification": "Fuera de la huella con respaldo municipal de protección."}),
    )
    del inventory["areas"][CONFLICT_ID]
    del audit["pending"][CONFLICT_ID]
    records.remove(conflict)
    for label, cut, mapping_fields, pending in pieces:
        geom, repair = geometry({"geometry": cut})
        if repair:
            raise ValueError(f"Conflict split required an unexpected geometry repair: {label}")
        fingerprint = digest(encode(geom))
        area_id = f"{INE}:IDEZar:{CLASS_LAYER}:{fingerprint}"
        if area_id in inventory["areas"]:
            raise ValueError("Conflict split duplicates an existing municipal area")
        land = {"originalCode": conflict["landClassification"]["originalCode"],
                "jurisdiction": conflict["landClassification"]["jurisdiction"], **mapping_fields}
        record = {**conflict, "areaId": area_id, "geometry": geom, "landClassification": land,
                  "sourceEvidence": {**conflict["sourceEvidence"], "parentAreaId": CONFLICT_ID,
                                     "classificationConflictAudit": "zoning-audit.json"}}
        validator.validate(json.loads(encode(record)))
        records.append(record)
        inventory["areas"][area_id] = {"geometry": fingerprint, "classification": land,
                                       "use": None, "pending": pending}
        if pending:
            audit["pending"][area_id] = pending
        replacements[label] = area_id
    records.sort(key=lambda record: record["areaId"])
    inventory["counts"].update(exported=len(records), proposedAreas=1, derivedAdditionalAreas=1,
                               pendingAreas=len(audit["pending"]))
    audit["conflictProposal"] = dict(evidence, replacements=replacements, mappingStatus="PROPOSED")


def generate(class_dir, urban_dir, non_urban_dir, regional_path, output, apply_proposal=False):
    spec = load(CLASS_CATALOG)
    class_meta, class_features = read_snapshot(class_dir, CLASS_LAYER)
    non_urban_meta, non_urban_features = read_snapshot(non_urban_dir, NON_URBAN_LAYER)
    urban = MunicipalUse(urban_dir)
    if spec["layer"] != class_meta["layer"]:
        raise ValueError("Classification rules target another layer")
    validator = Draft202012Validator(load(ROOT / "schemas/v1/zoning-area.schema.json"),
                                     format_checker=FormatChecker())
    classes = {item["id"]: {c["id"] for c in item["categories"]}
               for item in load(ROOT / "vocabularies/land-classifications.json")["classes"]}
    uses = {item["id"] for item in load(ROOT / "vocabularies/land-uses.json")["uses"]}
    class_records, class_inv, class_audit = source_records(class_features, CLASS_LAYER, spec, validator, classes)
    urban_data, urban_inv, urban_audit = municipal_dataset(urban, validator, uses)
    non_urban_records, non_urban_inv, non_urban_audit = source_records(
        non_urban_features, NON_URBAN_LAYER, spec, validator, classes)
    regional_data = regional_path.read_bytes()
    regional = load(regional_path)
    if not regional or any(not row["areaId"].startswith(f"{INE}:SIUa:") for row in regional):
        raise ValueError("Expected the published Zaragoza SIUa dataset for comparison")
    if apply_proposal:
        apply_conflict_proposal(class_records, class_inv, class_audit,
                                (non_urban_dir / "features.json").read_bytes(), regional_data, validator)
    contrast = spatial_contrast(class_records, regional)
    contrast["baselineSha256"] = digest(regional_data)
    folders = {"classification": (class_dir, class_meta), "urban": (urban_dir, urban.metadata),
               "non-urban": (non_urban_dir, non_urban_meta)}
    captures = {name: metadata for name, (_, metadata) in folders.items()}
    audit = {"classification": class_audit, "urbanQualification": urban_audit,
             "nonUrbanQualification": non_urban_audit, "regionalContrast": contrast,
             "sources": captures, "catalogReferenceDate": spec["catalogReferenceDate"]}
    objects = {DATASET: encode(class_records), MUNICIPAL_DATASET: urban_data,
               NON_URBAN_DATASET: encode(non_urban_records), AUDIT: encode(audit)}
    catalogs = {path.name: path.read_bytes() for path in (CLASS_CATALOG, CATALOG)}
    fingerprints = {name: digest(body) for name, body in {**objects, **catalogs}.items()}
    stamp = max(datetime.fromisoformat(item["responseTime"]) for item in captures.values())
    version = f"{stamp:%Y%m%dT%H%M%SZ}-{digest(encode(fingerprints))[:16]}"
    directory = output / version
    directory.mkdir(parents=True)
    with ZipFile(directory / SOURCES, "w", compression=ZIP_DEFLATED) as archive:
        for folder, (path, metadata) in folders.items():
            for name in sorted((*metadata["files"], "capture.json")):
                archive.writestr(ZipInfo(f"{folder}/{name}"), (path / name).read_bytes(), compress_type=ZIP_DEFLATED)
        for name, body in catalogs.items():
            archive.writestr(ZipInfo(name), body, compress_type=ZIP_DEFLATED)
        archive.writestr(ZipInfo(REGIONAL_BASELINE), regional_data, compress_type=ZIP_DEFLATED)
    objects[SOURCES] = (directory / SOURCES).read_bytes()
    manifest = dict(class_inv, municipalityCode=INE, version=version, s3Uri=f"{S3}/{version}/",
                    sourceArchive=SOURCES, source=captures, attribution=urban.metadata["attribution"],
                    sourceLicense=urban.spec["sourceLicense"], sourceTerms=urban.spec["sourceTerms"],
                    regionalContrast={"sha256": digest(regional_data), "archivePath": REGIONAL_BASELINE,
                                      "attribution": "Gobierno de Aragón · IGEAR · SIUa",
                                      "sourceTerms": "https://icearagon.aragon.es/portal/en/politica-privacidad.jsp"},
                    municipalZoningAreas=dict(urban_inv, file=MUNICIPAL_DATASET),
                    nonUrbanZoningAreas=dict(non_urban_inv, file=NON_URBAN_DATASET),
                    objects={name: {"bytes": len(body), "sha256": digest(body)} for name, body in objects.items()})
    if apply_proposal:
        manifest["classificationConflictProposal"] = class_audit["conflictProposal"]["replacements"]
    for name, body in objects.items():
        if name != SOURCES:
            (directory / name).write_bytes(body)
    (directory / MANIFEST).write_bytes(encode(manifest))
    print(directory)
    print(encode({"classification": class_inv["counts"], "urban": urban_inv["counts"],
                  "nonUrban": non_urban_inv["counts"]}).decode(), end="")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("classification", "urban", "non_urban", "regional_baseline", "output"):
        parser.add_argument(arg, type=Path)
    parser.add_argument("--apply-conflict-proposal", action="store_true")
    args = parser.parse_args()
    generate(args.classification, args.urban, args.non_urban, args.regional_baseline, args.output,
             args.apply_conflict_proposal)
