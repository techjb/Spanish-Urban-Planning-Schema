"""Identify the municipal planning instruments for pending PR and SUZ-PD areas."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path

from shapely import STRtree, make_valid, union_all
from shapely.geometry import shape

from capture_zoning import encode, hits
from generate_zoning import MUNICIPAL_DATASET, digest, load
from municipal_qualification import source_urls
from publish_zoning import publication

SCOPE_LAYERS = {"PR": "PLA_1_Ambitos_recogido", "SUZ-PD": "PLA_1_Ambitos_desarrollo"}
INSTRUMENT_LAYER = "PLA_1_Instrumentos_ambito"
MIN_COVERAGE = 0.95
MAX_COMPETITION = 0.01


def snapshot(directory, layer):
    data = directory / f"municipal-{layer}-full.json"
    count_path = directory / f"municipal-{layer}-hits.xml"
    expected = hits(count_path.read_bytes())
    collection = load(data)
    features = collection["features"]
    if (expected <= 0 or len(features) != expected or collection["numberMatched"] != expected
            or collection["numberReturned"] != expected
            or len({feature["id"] for feature in features}) != expected):
        raise ValueError(f"Incomplete municipal snapshot: {layer}")
    urls = source_urls(layer)
    metadata = {"count": expected, "responseTime": collection["timeStamp"],
                "features": {"url": urls["features.json"], "sha256": digest(data.read_bytes())},
                "hits": {"url": urls["hits.xml"], "sha256": digest(count_path.read_bytes())}}
    return features, metadata


def document_links(props):
    fields = ("id", "tipo_instrumento", "expediente", "apr_definitiva", "fecha_publicacion",
              "enlace_acuerdo", "enlace_normas", "enlace_planos", "enlace_memoria", "enlace_documentos")
    return {field: props[field] for field in fields if props[field] is not None}


def audit(release, directory):
    publication(release)
    areas = load(release / MUNICIPAL_DATASET)
    instruments, source = snapshot(directory, INSTRUMENT_LAYER)
    by_scope = defaultdict(list)
    for feature in instruments:
        props = feature["properties"]
        by_scope[props["codigo_ambito"]].append(document_links(props))
    output = {"sources": {INSTRUMENT_LAYER: source}, "scopeMatches": {},
              "method": "Intersection area fractions in CRS84. One scope must reach 95% and "
                        "the union of other intersecting scopes may cover at most 1%. "
                        "Instrument documents are joined by codigo_ambito."}
    for code, layer in SCOPE_LAYERS.items():
        features, output["sources"][layer] = snapshot(directory, layer)
        if code == "SUZ-PD":
            features = [feature for feature in features if feature["properties"]["tipo_ambito"] == "SUZ"]
        geoms = [make_valid(shape(feature["geometry"])) for feature in features]
        tree = STRtree(geoms)
        records, counts, matched_scopes = {}, Counter(), Counter()
        for area in areas:
            use = area["characteristicUse"]
            if use.get("originalCode") != code or use["use"] != "UNKNOWN":
                continue
            zone = shape(area["geometry"])
            overlaps = {}
            for index in tree.query(zone, predicate="intersects"):
                intersection = zone.intersection(geoms[index])
                if intersection.area > 0:
                    overlaps[index] = intersection
            dominant = [index for index, geom in overlaps.items() if geom.area / zone.area >= MIN_COVERAGE]
            result = {"status": "SIN_AMBITO_INEQUIVOCO", "candidates": {
                features[index]["properties"]["codigo_ambito"]: round(geom.area / zone.area, 8)
                for index, geom in overlaps.items()}}
            if len(dominant) == 1:
                winner = dominant[0]
                competing = union_all([geom for index, geom in overlaps.items() if index != winner])
                if competing.area / zone.area <= MAX_COMPETITION:
                    scope = features[winner]["properties"]["codigo_ambito"]
                    docs = sorted(by_scope[scope], key=lambda props: props["id"])
                    result.update(status="AMBITO_IDENTIFICADO", codigoAmbito=scope,
                                  ficha=features[winner]["properties"]["enlace_ficha"], instrumentos=docs)
                    if not any(doc.get("enlace_planos") for doc in docs):
                        counts["withoutPlanLink"] += 1
                    matched_scopes[scope] += 1
            counts[result["status"]] += 1
            records[area["areaId"]] = result
        output["scopeMatches"][code] = {"counts": dict(counts), "areas": records,
                                         "matchedScopes": dict(matched_scopes)}
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("snapshots", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = audit(args.release, args.snapshots)
    args.output.write_bytes(encode(result))
    print(encode({code: data["counts"] for code, data in result["scopeMatches"].items()}).decode(), end="")
