"""Capture and apply municipal qualification to a Zaragoza SIUa snapshot."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from shapely import STRtree, make_valid, union_all
from shapely.geometry import Polygon, shape

from capture_zoning import encode, hits

HERE = Path(__file__).resolve().parent
CATALOG = HERE / "municipal-use-mappings.json"
LAYER = "Calificaciones_Urbanas"
CLASS_LAYER = "Clasificaciones"
NON_URBAN_LAYER = "Calificaciones_No_Urbanas"


def source_urls(layer):
    base = ("https://idezar-sig.zaragoza.es/servicios/geoserver/ows?"
            f"service=WFS&version=2.0.0&request=GetFeature&typeNames=urbanismo:{layer}")
    return {"features.json": base + "&srsName=CRS:84&outputFormat=application%2Fjson",
            "hits.xml": base + "&resultType=hits"}


def validate(data, count):
    collection = json.loads(data)
    features = collection["features"]
    if (collection["type"] != "FeatureCollection"
            or collection["crs"]["properties"]["name"] not in {
                "urn:ogc:def:crs:EPSG::4326", "urn:ogc:def:crs:CRS::84"}
            or len(features) != count or count <= 0
            or collection["numberMatched"] != count or collection["numberReturned"] != count
            or len({feature["id"] for feature in features}) != count):
        raise ValueError("Incomplete municipal qualification response or unexpected CRS")
    return collection


def capture(directory, saved, layer=LAYER):
    directory.mkdir(parents=True)
    files = {}
    for name, url in source_urls(layer).items():
        target = directory / name
        if saved:
            suffix = "full.json" if name == "features.json" else "hits.xml"
            target.write_bytes((saved / f"municipal-{layer}-{suffix}").read_bytes())
        else:
            subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                            "--max-time", "90", "--output", str(target), url], check=True)
        raw = target.read_bytes()
        files[name] = {"url": url, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    count = hits((directory / "hits.xml").read_bytes())
    collection = validate((directory / "features.json").read_bytes(), count)
    metadata = {"layer": f"urbanismo:{layer}", "responseTime": collection["timeStamp"],
                "referenceEdition": None, "count": count, "files": files,
                "attribution": "Ayuntamiento de Zaragoza · IDEZar"}
    (directory / "capture.json").write_bytes(encode(metadata))


def read_snapshot(directory, layer=LAYER):
    metadata = json.loads((directory / "capture.json").read_bytes())
    urls = source_urls(layer)
    if metadata["layer"] != f"urbanismo:{layer}" or set(metadata["files"]) != set(urls):
        raise ValueError("Unexpected municipal capture scope")
    files = {}
    for name, url in urls.items():
        raw = (directory / name).read_bytes()
        info = metadata["files"][name]
        if info != {"url": url, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}:
            raise ValueError(f"Municipal capture checksum mismatch: {name}")
        files[name] = raw
    count = hits(files["hits.xml"])
    if count != metadata["count"]:
        raise ValueError("Municipal capture count mismatch")
    return metadata, validate(files["features.json"], count)["features"]


class MunicipalUse:
    def __init__(self, directory):
        self.metadata, self.features = read_snapshot(directory)
        self.catalog_bytes = CATALOG.read_bytes()
        self.spec = json.loads(self.catalog_bytes)
        if self.spec["layer"] != self.metadata["layer"]:
            raise ValueError("Municipal rules target another layer")
        self.geometries = []
        self.rules = []
        for feature in self.features:
            props = feature["properties"]
            code = props[self.spec["sourceField"]]
            geom = make_valid(shape(feature["geometry"])) if feature["geometry"] else Polygon()
            self.geometries.append(geom)
            eligible = all(props[key] == value for key, value in self.spec["requiredAttributes"].items())
            rule = self.spec["rules"].get(code) if eligible else None
            self.rules.append(rule)
        self.tree = STRtree(self.geometries)

    def resolve(self, geometry, classification, regional_code):
        criteria = self.spec["requiredClassification"]
        if regional_code or any(classification.get(key) != value for key, value in criteria.items()):
            return None, None
        zone = shape(geometry)
        by_use = defaultdict(list)
        evidence = []
        for index in sorted(self.tree.query(zone, predicate="intersects")):
            clipped = zone.intersection(self.geometries[index])
            if clipped.area <= 0:
                continue
            candidate = self.rules[index]
            label = candidate[0] if candidate else "UNMAPPED"
            by_use[label].append(clipped)
            feature = self.features[index]
            evidence.append({"sourceId": feature["id"], "properties": feature["properties"],
                             "normalizedUse": label, "overlap": round(clipped.area / zone.area, 8),
                             "ruleEvidence": candidate[1] if candidate else None})
        fractions = {label: union_all(parts).area / zone.area for label, parts in by_use.items()}
        dominant = [label for label, value in fractions.items()
                    if label != "UNMAPPED" and value >= self.spec["minimumCoverage"]]
        details = {"coverageByUse": {key: round(value, 8) for key, value in fractions.items()},
                   "features": evidence, "decision": "Sin uso cartográfico suficientemente dominante"}
        if len(dominant) != 1:
            return None, details
        label = dominant[0]
        competition = union_all([part for key, parts in by_use.items() if key != label
                                 for part in parts]).area / zone.area
        if competition > self.spec["maximumCompetingCoverage"]:
            details["decision"] = "Solape con calificación competidora o sin equivalencia"
            return None, details
        codes = sorted({item["properties"][self.spec["sourceField"]] for item in evidence
                        if item["normalizedUse"] == label})
        code = "|".join(codes)
        details.update(decision="Uso municipal verificado", competingCoverage=round(competition, 8),
                       layer=self.spec["layer"], originalCodes=codes)
        return {"use": label, "originalCode": code, "mappingStatus": "VERIFIED",
                "mappingId": f"50297:municipal:{code}",
                "provenance": {"sourceField": self.spec["sourceField"], "originalCode": code,
                               "planningInstrument": self.spec["instrument"],
                               "basis": "ZONING_DESIGNATION"}}, details


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--layer", choices=(LAYER, CLASS_LAYER, NON_URBAN_LAYER), default=LAYER)
    parser.add_argument("--saved", type=Path, help="Import existing full.json and hits.xml responses")
    args = parser.parse_args()
    capture(args.directory, args.saved, args.layer)
