"""Capture the official SIUa WFS responses for Zaragoza (INE 50297)."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from urllib.parse import urlencode
from xml.etree import ElementTree

INE = "50297"
BASE = "https://icearagon.aragon.es/SIUa_WMS"
LAYERS = ("clasificacion_idearagon", "usoglobal")
FILTER = f"cod_ine={INE}"
PAGE_SIZE = 250
CRS = "urn:ogc:def:crs:CRS::84"
WFS_COLLECTION = "{http://www.opengis.net/wfs/2.0}FeatureCollection"
KEY_FIELDS = ("objectid", "shape_area", "shape_le_1")


def source_key(feature):
    return tuple(feature["properties"][field] for field in KEY_FIELDS)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def check_page(data, layer, total, expected, attributes_only=False):
    page = json.loads(data)
    features = page["features"]
    if (page["type"] != "FeatureCollection"
            or page["numberMatched"] != total or page["numberReturned"] != expected
            or len(features) != expected
            or (expected and not attributes_only and page["crs"]["properties"]["name"] != CRS)):
        raise ValueError(f"{layer}: incomplete page, changed count or unexpected CRS")
    for feature in features:
        props = feature["properties"]
        if props["cod_ine"] != int(INE) or type(props["objectid"]) is not int:
            raise ValueError(f"{layer}: unexpected municipality or identifier")
    return features


def hits(data):
    root = ElementTree.fromstring(data)
    if root.tag != WFS_COLLECTION or root.attrib.get("numberReturned") != "0":
        raise ValueError("Unexpected WFS hits response")
    return int(root.attrib["numberMatched"])


def capture(directory):
    directory.mkdir(parents=True)
    manifest = {"municipalityCode": INE, "baseUrl": BASE, "filter": FILTER,
                "capturedAt": datetime.now(timezone.utc).isoformat(), "files": {}, "layers": {}}

    def download(name, request, **params):
        url = BASE + "?" + urlencode(dict(service="WFS", version="2.0.0", request=request, **params))
        path = directory / name
        subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                        "--retry", "2", "--max-time", "150", "--output", str(path), url],
                       check=True)
        data = path.read_bytes()
        manifest["files"][name] = {"url": url, "sha256": sha256(data).hexdigest(),
                                   "bytes": len(data)}
        return data

    catalog = ElementTree.fromstring(download("capabilities.xml", "GetCapabilities"))
    manifest["wfsUpdateSequence"] = catalog.attrib.get("updateSequence")
    for layer in LAYERS:
        typename = {"typeNames": f"SIUa:{layer}"}
        params = dict(typename, CQL_FILTER=FILTER)
        schema = f"{layer}.xsd"
        download(schema, "DescribeFeatureType", **typename)
        before, after = (f"{layer}-{phase}.xml" for phase in ("before", "after"))
        total = hits(download(before, "GetFeature", **params, resultType="hits"))
        if total <= 0:
            raise ValueError(f"{layer}: empty extract")
        ordered = dict(params, sortBy=",".join(f"{field} A" for field in KEY_FIELDS), srsName="CRS:84",
                       outputFormat="application/json")
        pages, ids = [], []
        for offset in range(0, total, PAGE_SIZE):
            name = f"{layer}-{offset:06d}.json"
            expected = min(PAGE_SIZE, total - offset)
            features = check_page(download(name, "GetFeature", **ordered,
                                           count=PAGE_SIZE, startIndex=offset),
                                  layer, total, expected)
            pages.append({"file": name, "offset": offset, "count": expected})
            ids.extend(map(source_key, features))
        inventory = f"{layer}-inventory.json"
        keys = check_page(download(inventory, "GetFeature", **ordered, count=total,
                                   propertyName=",".join((*KEY_FIELDS, "cod_ine"))),
                          layer, total, total, attributes_only=True)
        if (ids != sorted(set(ids)) or ids != list(map(source_key, keys))
                or hits(download(after, "GetFeature", **params, resultType="hits")) != total):
            raise ValueError(f"{layer}: inconsistent paging, duplicated IDs or changing source")
        manifest["layers"][layer] = dict(count=total, schema=schema, before=before, after=after,
                                         inventory=inventory, pages=pages)
        print(layer, total, flush=True)
    (directory / "capture.json").write_bytes(encode(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    capture(parser.parse_args().directory)
