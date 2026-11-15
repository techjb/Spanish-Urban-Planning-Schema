"""Capture the complete Bilbao inventory of the Bizkaia planning service."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile


SERVICE = ("https://geo.bizkaia.eus/arcgisserverinspire/rest/services/"
           "LurraldeAntolamendua_PlanificacionTerritorial/Plangintza_Planeamiento/MapServer")
FILTER = "Municipio = 'BILBAO'"
LAYERS = (*range(1, 5), *range(6, 11), *range(12, 38), *range(39, 45))


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode()


def capture_layer(layer, metadata):
    files = {}
    requests = {}

    def fetch(name, **params):
        url = f"{SERVICE}/{layer}/query?{urlencode({'where': FILTER, **params})}"
        with urlopen(url, timeout=150) as response:
            data = response.read()
        value = json.loads(data)
        if "error" in value or value.get("exceededTransferLimit"):
            raise ValueError(f"{url}: {value.get('error', 'transfer limit exceeded')}")
        path = f"{layer}/{name}.json"
        files[path] = data
        requests[path] = {"url": url, "sha256": sha256(data).hexdigest()}
        return value

    def inventory(stage):
        count = fetch(f"{stage}-count", f="json", returnCountOnly="true")["count"]
        ids = fetch(f"{stage}-ids", f="json", returnIdsOnly="true")
        ids = ids["objectIds"] or []
        if len(ids) != count or len(set(ids)) != count:
            raise ValueError(f"Layer {layer}: count and ID inventory disagree")
        return sorted(ids)

    ids = inventory("before")
    pages = []
    size = min(metadata["maxRecordCount"], 100)
    for start in range(0, len(ids), size):
        batch = ids[start:start + size]
        name = f"page-{start:06}"
        page = fetch(name, f="geojson", objectIds=",".join(map(str, batch)), outFields="*",
                     returnGeometry="true", outSR=4326, orderByFields="OBJECTID")
        rows = page["features"]
        if sorted(row["properties"]["OBJECTID"] for row in rows) != batch:
            raise ValueError(f"Layer {layer}: incomplete page {start}")
        if any(row["properties"]["Municipio"] != "BILBAO" for row in rows):
            raise ValueError(f"Layer {layer}: unexpected municipal scope")
        pages.append(f"{layer}/{name}.json")
    if inventory("after") != ids:
        raise ValueError(f"Layer {layer}: inventory changed during extraction")
    print(f"{layer}: {len(ids)}", flush=True)
    return files, requests, pages


def capture(destination):
    started = datetime.now(timezone.utc).isoformat()
    url = f"{SERVICE}/layers?f=json"
    with urlopen(url, timeout=60) as response:
        metadata_raw = response.read()
    metadata = json.loads(metadata_raw)
    layers = {item["id"]: item for item in metadata["layers"] if item.get("geometryType")}
    if set(layers) != set(LAYERS):
        raise ValueError(f"Service layer inventory changed: {sorted(layers)}")
    files = {"layers.json": metadata_raw}
    requests = {"layers.json": {"url": url, "sha256": sha256(metadata_raw).hexdigest()}}
    pages = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {layer: pool.submit(capture_layer, layer, layers[layer]) for layer in LAYERS}
        for layer, future in futures.items():
            bodies, queries, pages[str(layer)] = future.result()
            files.update(bodies)
            requests.update(queries)
    manifest = {"downloadStartedAt": started, "downloadCompletedAt": datetime.now(timezone.utc).isoformat(),
                "requests": requests, "pages": pages, "municipalityCode": "48020", "filter": FILTER}
    with ZipFile(destination, "x", ZIP_DEFLATED) as archive:
        archive.writestr("capture.json", encode(manifest))
        for name, body in sorted(files.items()):
            archive.writestr(name, body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    capture(parser.parse_args().destination)
