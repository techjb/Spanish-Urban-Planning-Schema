"""Compare pending AMB polygons with the official MUC zoning layer in EPSG:25831."""
import argparse
import io
import json
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

import shapefile
from shapely import STRtree, make_valid
from shapely.geometry import shape
from shapely.ops import unary_union

from audit_barcelona_planning import AMB, INE, ROOT
from audit_madrid_uses import fetch

FIELDS = ("REGIM", "CLAU_URB", "CLAU_PD", "EXP_PD", "PLAN", "DESCRIP", "US_SECT")
COVERAGE = 0.99
MUC_GLOSSARY = "https://territori.gencat.cat/web/.content/home/06_territori_i_urbanisme/07_observatori_territori/mapa_urbanistic_de_catalunya/caracteristiques_tecniques/metodologia/documents/codificacio_i_glossari_muc.pdf"
MUC_DOWNLOAD = "https://territori.gencat.cat/web/.content/home/06_territori_i_urbanisme/07_observatori_territori/mapa_urbanistic_de_catalunya/serveis_web_dades_obertes/Descarrega_de_dades/SHP/docs_SHP_Ambit_comarcal/MUC_QUAL_SHP_ETRS89_Barcelones.zip"
MUC_USES = {
    **dict.fromkeys(("R1", "R2", "R3"), ("RESIDENTIAL", "UNSPECIFIED")),
    "R4": ("RESIDENTIAL", "MULTIFAMILY"),
    **dict.fromkeys(("R5", "R6"), ("RESIDENTIAL", "SINGLE_FAMILY")),
    "A1": ("INDUSTRIAL", "UNSPECIFIED"),
    "A3": ("LOGISTICS", "DISTRIBUTION"),
    **dict.fromkeys(("SX", "SX1", "SX2", "SX3", "SF", "SA", "SP"), ("INFRASTRUCTURE", "TRANSPORT")),
    "ST": ("INFRASTRUCTURE", "UTILITIES"),
    "SE": ("FACILITIES", "UNSPECIFIED"),
    "SD": ("FACILITIES", "OTHER"),
    "SV": ("GREEN_SPACE", "UNSPECIFIED"),
}


def load_muc(path):
    with ZipFile(path) as archive:
        stem = "MUC_QUAL_Barcelones"
        projection = archive.read(stem + ".prj").decode()
        if not projection.startswith('PROJCS["ETRS_1989_UTM_Zone_31N"'):
            raise ValueError("Expected ETRS89 / UTM zone 31N")
        with shapefile.Reader(**{
            suffix: io.BytesIO(archive.read(f"{stem}.{suffix}"))
            for suffix in ("shp", "shx", "dbf")
        }) as reader:
            return [
                (row.record["C_QUAL_MUC"], make_valid(shape(row.shape.__geo_interface__)))
                for row in reader.iterShapeRecords(fields=["CODI_INE", "C_QUAL_MUC"])
                if row.record["CODI_INE"] == INE
            ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("muc_zip", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    audit = json.loads((ROOT / "validation/barcelona/planning-audit.json").read_text(encoding="utf-8"))
    pending = Counter({
        tuple(group["original"][field] for field in FIELDS): group["recordCount"]
        for group in audit["amb"]["groups"] if group["use"]["status"] == "REQUIRES_REVIEW"
    })
    seen = Counter()
    muc = load_muc(args.muc_zip)
    if not muc:
        raise ValueError("MUC layer has no Barcelona polygons")
    tree = STRtree([geometry for _, geometry in muc])
    query = AMB + "/query"
    where = f"CODI_INE = '{INE}'"
    ids = sorted(fetch(query, {"f": "json", "where": where, "returnIdsOnly": "true"})["objectIds"])
    if len(ids) != len(set(ids)) or len(ids) != audit["amb"]["recordCount"]:
        raise RuntimeError("AMB inventory changed; regenerate the audit")
    rows = []
    for start in range(0, len(ids), 100):
        batch = ids[start:start + 100]
        result = fetch(AMB + "/query", {
            "f": "geojson", "where": where, "objectIds": ",".join(map(str, batch)),
            "outFields": ",".join(("OBJECTID", "CODI_INE", *FIELDS)),
            "outSR": "25831", "returnGeometry": "true",
        })
        features = result["features"]
        if sorted(f["properties"]["OBJECTID"] for f in features) != batch:
            raise RuntimeError("Incomplete AMB geometry batch")
        for feature in features:
            attributes = feature["properties"]
            if attributes["CODI_INE"] != INE:
                raise RuntimeError("Out-of-scope AMB polygon")
            key = tuple(attributes[field] for field in FIELDS)
            if key not in pending:
                continue
            seen[key] += 1
            row = {"objectId": attributes["OBJECTID"], "original": dict(zip(FIELDS, key))}
            geometry = make_valid(shape(feature["geometry"])) if feature["geometry"] else None
            if geometry is None or geometry.area <= 0:
                rows.append(dict(row, mucCode=None, mucCoverage={}, reason="NO_AMB_AREA"))
                continue
            if not 400000 < geometry.bounds[0] < 500000:
                raise ValueError("Expected AMB coordinates in EPSG:25831")
            overlaps = defaultdict(list)
            for index in tree.query(geometry, predicate="intersects"):
                code, zoning = muc[index]
                overlap = zoning.intersection(geometry)
                if overlap.area:
                    overlaps[code].append(overlap)
            ratios = {code: unary_union(parts).area / geometry.area for code, parts in overlaps.items()}
            matches = [code for code, ratio in ratios.items() if code and ratio >= COVERAGE]
            match = matches[0] if len(matches) == 1 and all(
                ratio <= 1 - COVERAGE for code, ratio in ratios.items() if code != matches[0]
            ) else None
            rows.append(dict(row, mucCode=match, mucCoverage={
                code: round(ratio, 6) for code, ratio in sorted(ratios.items())
            }))
    if seen != pending:
        raise RuntimeError("Pending AMB groups changed; regenerate the audit")
    catalog = json.loads((ROOT / "vocabularies/land-uses.json").read_text(encoding="utf-8"))
    allowed = {(use["id"], subtype["id"]) for use in catalog["uses"] for subtype in use["subtypes"]}
    if not set(MUC_USES.values()) <= allowed:
        raise ValueError("Invalid SUPS use mapping")
    for row in rows:
        mapping = MUC_USES.get(row["mucCode"])
        if mapping:
            row["mucUse"] = {"normalizedUse": mapping[0], "normalizedSubtype": mapping[1]}
    summary = dict(Counter(row["mucCode"] or "UNRESOLVED" for row in rows))
    mapped = sum("mucUse" in row for row in rows)
    args.output.write_text(json.dumps({
        "municipalityCode": INE, "ambSource": AMB, "auditExtractedAt": audit["extractedAt"],
        "mucSource": MUC_DOWNLOAD, "mucGlossary": MUC_GLOSSARY, "mucSnapshot": "2025-01-01",
        "mucArchiveSha256": sha256(args.muc_zip.read_bytes()).hexdigest(),
        "additionalUseMappings": mapped, "remaining": len(rows) - mapped,
        "minimumCoverage": COVERAGE, "summary": summary, "polygons": sorted(rows, key=lambda row: row["objectId"]),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(len(rows), mapped, summary)


if __name__ == "__main__":
    main()
