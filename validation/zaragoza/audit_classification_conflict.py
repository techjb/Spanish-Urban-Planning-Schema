"""Trace the municipal SU/SNU-E conflict without changing the published release."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from zipfile import ZipFile

from shapely import union_all
from shapely.geometry import mapping, shape

from capture_zoning import encode
from generate_zoning import DATASET, MANIFEST, digest, load
from publish_zoning import publication

CONFLICT_ID = ("50297:IDEZar:Clasificaciones:"
               "097a39a7cbda02f64503e2ee40fd04546a5064c87e1296b2704650daa2cc5ece")
PROTECTED_CODES = {
    "SNU-EC", "SNU-EN-CC", "SNU-EN-MA", "SNU-EN-NI", "SNU-EN-RF", "SNU-EN-SE",
    "SNU-EN-SR", "SNU-EN-VB", "SNU-EP-HH", "SNU-EP-R", "SNU-EP-S", "SNU-EP-V",
    "SNU-ES-D", "SNU-ES-SCI", "SNU-ET",
}


def overlap_by_code(records, target):
    intersections = defaultdict(list)
    for record in records:
        geom = shape(record["geometry"])
        if not target.intersects(geom):
            continue
        clipped = target.intersection(geom)
        if clipped.area:
            props = record["properties"]
            code = props["calificacion"]
            if props["tipo"] != "CALF" or props["clase"] != "P":
                raise ValueError(f"Unexpected attributes on overlapping municipal record {record['id']}")
            intersections[code].append(clipped)
    return {code: union_all(parts) for code, parts in intersections.items()}


def derive(conflict, municipal_raw, regional_raw):
    rows = conflict["sourceEvidence"]["sourceFeatures"]
    codes = {row["properties"]["clasificacion"] for row in rows}
    if codes != {"SU", "SNU-E"} or conflict["landClassification"]["class"] != "UNKNOWN":
        raise ValueError("Published municipal conflict changed; revisit the interpretation")
    target = shape(conflict["geometry"])
    municipal = json.loads(municipal_raw)["features"]
    regional = json.loads(regional_raw)
    municipal_by_code = overlap_by_code(municipal, target)
    protected = union_all([geom for code, geom in municipal_by_code.items() if code in PROTECTED_CODES])
    other_codes = union_all([geom for code, geom in municipal_by_code.items() if code not in PROTECTED_CODES])
    candidate = protected.difference(other_codes)
    unassigned = target.difference(candidate)
    regional_non_developable = union_all([
        shape(record["geometry"]) for record in regional
        if record["landClassification"]["class"] == "NON_DEVELOPABLE"])

    def percentage(geom):
        return round(100 * geom.area / target.area, 6)

    report = {
        "areaId": CONFLICT_ID,
        "areaM2PublishedByMunicipality": rows[0]["properties"]["superficie"],
        "method": "Polygon intersections and unions in CRS84. Percentages are of the conflict footprint.",
        "originalSourceRows": rows,
        "municipalNonUrbanSha256": digest(municipal_raw),
        "regionalContrastSha256": digest(regional_raw),
        "municipalCoverageByCodePct": {code: percentage(geom) for code, geom in municipal_by_code.items()},
        "municipalNonUrbanCoveragePct": percentage(union_all(list(municipal_by_code.values()))),
        "municipalProtectedCoveragePct": percentage(protected),
        "proposedProtectedPct": percentage(candidate),
        "stillUnassignedPct": percentage(unassigned),
        "regionalNonDevelopablePct": percentage(target.intersection(regional_non_developable)),
        "proposedProtectedAndRegionalNonDevelopablePct": percentage(
            candidate.intersection(regional_non_developable)),
    }
    if not candidate.is_valid or not unassigned.is_valid:
        raise ValueError("Invalid diagnostic split")
    if abs(candidate.area + unassigned.area - target.area) > target.area * 1e-8:
        raise ValueError("Diagnostic split does not account for the whole conflict")
    return report, mapping(candidate), mapping(unassigned)


def audit(release, directory):
    publication(release)
    manifest = load(release / MANIFEST)
    conflict = next(record for record in load(release / DATASET) if record["areaId"] == CONFLICT_ID)
    with ZipFile(release / manifest["sourceArchive"]) as source:
        municipal_raw = source.read("non-urban/features.json")
        regional_raw = source.read(manifest["regionalContrast"]["archivePath"])
    report, candidate, unassigned = derive(conflict, municipal_raw, regional_raw)
    report["sourceVersion"] = manifest["version"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "classification-conflict-audit.json").write_bytes(encode(report))
    (directory / "classification-conflict-proposal.geojson").write_bytes(encode({
        "type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": candidate,
             "properties": {"sourceAreaId": CONFLICT_ID, "mappingStatus": "PROPOSED",
                            "class": "NON_DEVELOPABLE", "category": "PROTECTED"}},
            {"type": "Feature", "geometry": unassigned,
             "properties": {"sourceAreaId": CONFLICT_ID, "mappingStatus": "REQUIRES_REVIEW",
                            "class": "UNKNOWN"}},
        ],
    }))
    print(encode(report).decode(), end="")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    audit(args.release, args.directory)
