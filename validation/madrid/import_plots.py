#!/usr/bin/env python3
"""Fetch real Madrid urban-planning plots and build conservative SUPS Plot fixtures.

Usage: python validation/madrid/import_plots.py --limit 20
Requires: pip install requests jsonschema
No synthetic features are generated. An unavailable endpoint is a hard failure.
"""
import argparse
import json
from pathlib import Path
import sys
import requests
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
URL = "https://sigma.madrid.es/hosted/rest/services/DESARROLLO_URBANO_ACTUALIZADO/USOS_SUELO/MapServer/3/query"
FIELDS = "UBOV_ID,ZURV_TX_NOMBRE,USP_TX_DENOM,AMB_TX_ETIQ,AMB_TX_DENOM,UBOV_TX_ETIQ"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output")
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    params = {
        "where": "1=1", "outFields": FIELDS, "returnGeometry": "true",
        "outSR": 4326, "resultRecordCount": args.limit,
        "orderByFields": "UBOV_ID", "f": "geojson",
    }
    response = requests.get(URL, params=params, timeout=40)
    response.raise_for_status()
    source = response.json()
    if source.get("type") != "FeatureCollection" or not source.get("features"):
        raise ValueError("No GeoJSON features returned; source was not usable")
    schema = json.loads((ROOT / "schemas/v1/plot.schema.json").read_text())
    validator = Draft202012Validator(schema)
    plots = []
    for feature in source["features"]:
        attrs = feature.get("properties") or {}
        identifier = attrs.get("UBOV_ID")
        if identifier is None:
            raise ValueError("Feature without UBOV_ID")
        plot = {
            "schemaVersion": "1.0",
            "plotId": "MADRID-UBOV-" + str(identifier),
            "parameters": {},
            "calculationStatus": "UNKNOWN",
        }
        # The municipality's attributes do not independently prove legal
        # buildability, setbacks, occupancy or height. Do not invent them.
        validator.validate(plot)
        plots.append(plot)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "source.geojson").write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "sups-plots.json").write_text(json.dumps(plots, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "manifest.json").write_text(json.dumps({
        "source_url": response.url,
        "count": len(plots),
        "note": "Source geometries and municipal attributes are in source.geojson; legal parcel parameters remain unresolved.",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Imported {len(plots)} real municipal urban-planning plots to {args.output}")

if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, ValueError) as exc:
        print(f"Import failed (no fabricated records): {exc}", file=sys.stderr)
        sys.exit(1)
