"""Measure municipal zoning overlap for SIUa areas with an unresolved use."""
import argparse
from collections import Counter
from pathlib import Path

from shapely import STRtree, make_valid, union_all
from shapely.geometry import shape

from generate_zoning import load


def audit(dataset, sources):
    pending = [record for record in load(dataset) if record["characteristicUse"]["use"] == "UNKNOWN"]
    summary = {"pending": len(pending), "layers": {}}
    for source in sources:
        collection = load(source)
        features = collection["features"]
        if len(features) != collection["numberMatched"] or len(features) != collection["numberReturned"]:
            raise ValueError(f"Incomplete municipal layer: {source}")
        geometries = [make_valid(shape(f["geometry"])) if f["geometry"] else shape({"type": "Polygon", "coordinates": []})
                      for f in features]
        keys = [f["properties"]["calificacion"] for f in features]
        tree = STRtree(geometries)
        overlaps = Counter()
        for record in pending:
            zone = shape(record["geometry"])
            hits = []
            for index in tree.query(zone, predicate="intersects"):
                if keys[index]:
                    intersection = zone.intersection(geometries[index])
                    if intersection.area > 0:
                        hits.append(intersection)
            if not hits:
                continue
            overlaps["positive_area"] += 1
            ratio = union_all(hits).area / zone.area
            if ratio >= 0.5:
                overlaps["at_least_50_pct"] += 1
            if ratio >= 0.95:
                overlaps["at_least_95_pct"] += 1
        summary["layers"][source.name] = {
            "features": len(features),
            "unique_feature_ids_in_response": len({f["id"] for f in features}),
            "key_counts": dict(sorted(Counter(k for k in keys if k).items())),
            "pending_overlaps": dict(overlaps),
        }
    return summary


if __name__ == "__main__":
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("sources", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps(audit(args.dataset, args.sources), indent=2))
