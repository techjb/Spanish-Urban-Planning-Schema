"""Capture the Geoportal's complete municipal PGOU polygon layer."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile

LAYER = "https://geoportal.valencia.es/server/rest/services/OPENDATA/UrbanismoEInfraestructuras/MapServer/231"
CATALOGUE = "https://opendata.vlci.valencia.es/api/3/action/package_show"
WHERE = "1=1"
OID = "objectid"
FIELDS = (OID, "clase", "califi", "tipoca", "uso", "tipouso", "origen",
          "uso_califi", "ttggss", "idoperacion", "fecha_valor", "linkid", "operacionbaja", "categoria")
BATCH = 200


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode()


def digest(data):
    return sha256(data).hexdigest()


def inventory(count, response):
    ids = response["objectIds"]
    if (response.get("exceededTransferLimit") or response["objectIdFieldName"].lower() != OID
            or count <= 0 or len(ids) != count or len(set(ids)) != count
            or any(type(oid) is not int or oid < 0 for oid in ids)):
        raise ValueError("El recuento no coincide con el inventario de identificadores")
    return sorted(ids)


def check_page(page, expected):
    if page.get("type") != "FeatureCollection" or page.get("exceededTransferLimit") or (
            page.get("properties", {}).get("exceededTransferLimit")):
        raise ValueError("Página no válida o truncada")
    crs = page.get("crs", {}).get("properties", {}).get("name")
    if crs and not crs.endswith((":4326", ":CRS84")):
        raise ValueError(f"CRS inesperado: {crs}")
    features = page["features"]
    if sorted(row["properties"][OID] for row in features) != expected:
        raise ValueError(f"Página incompleta o duplicada para {expected[0]}–{expected[-1]}")
    for row in features:
        attrs = row["properties"]
        if not set(FIELDS) <= attrs.keys() or row.get("id", attrs[OID]) != attrs[OID]:
            raise ValueError(f"Campos o identificador incorrectos: {attrs[OID]}")
    return sorted(features, key=lambda row: row["properties"][OID])


def download(url, **params):
    link = url + "?" + urlencode(params)
    for attempt in range(3):
        try:
            with urlopen(link, timeout=75) as response:
                raw = response.read()
            break
        except (URLError, TimeoutError) as error:
            if attempt == 2 or isinstance(error, HTTPError) and error.code < 429:
                raise
            sleep(2 ** attempt)
    data = json.loads(raw)
    if "error" in data:
        raise ValueError(f"{link}: {data['error']}")
    return raw, data, {"url": link, "sha256": digest(raw), "bytes": len(raw),
                       "downloadedAt": datetime.now(timezone.utc).isoformat()}


def batches(ids, size):
    for start in range(0, len(ids), size):
        yield f"page-{start:05d}.json", ids[start:start + size]


def missing_geojson(feature):
    geometry = feature.get("geometry")
    return not geometry or not geometry.get("coordinates")


def check_native(page, expected):
    if (page.get("exceededTransferLimit") or page["geometryType"] != "esriGeometryPolygon"
            or page["spatialReference"]["wkid"] != 25830):
        raise ValueError("Diagnóstico geométrico nativo inválido")
    rows = page["features"]
    if sorted(row["attributes"][OID] for row in rows) != expected:
        raise ValueError("Diagnóstico geométrico nativo incompleto")
    if any(row.get("geometry", {}).get("rings") for row in rows):
        raise ValueError("El formato nativo contiene anillos que faltan en GeoJSON. Revisar la conversión.")


def capture(target):
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    requests = {}
    query = LAYER + "/query"
    with TemporaryDirectory(dir=target.parent) as scratch:
        temporary = Path(scratch) / "source.zip"
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as archive:
            def save(name, response):
                raw, data, requests[name] = response
                archive.writestr(name, raw)
                return data

            def get_inventory(suffix):
                count = save(f"count{suffix}.json", download(query, f="json", where=WHERE,
                                                            returnCountOnly="true"))["count"]
                ids = save(f"ids{suffix}.json", download(query, f="json", where=WHERE, returnIdsOnly="true"))
                return inventory(count, ids)

            layer = save("layer.json", download(LAYER, f="json"))
            fields = {field["name"]: field["type"] for field in layer["fields"]}
            if not set(FIELDS) <= fields.keys() or fields[OID] != "esriFieldTypeOID":
                raise ValueError("La capa municipal cambió sus campos")
            if (layer["geometryType"] != "esriGeometryPolygon"
                    or layer["extent"]["spatialReference"].get("wkid") != 25830):
                raise ValueError("La capa municipal cambió su geometría o CRS")
            service = save("service.json", download(LAYER.rsplit("/", 1)[0], f="json"))
            catalogue = save("catalogue.json", download(CATALOGUE, id="pgou-calificacions-pgou-calificaciones"))
            size = min(BATCH, layer["maxRecordCount"])
            ids = get_inventory("")

            def fetch_page(batch):
                name, expected = batch
                response = download(query, f="geojson", where=WHERE, objectIds=",".join(map(str, expected)),
                                    outFields=",".join(FIELDS), returnGeometry="true", outSR=4326)
                check_page(response[1], expected)
                return name, response

            missing = []
            with ThreadPoolExecutor(max_workers=4) as pool:
                for name, response in pool.map(fetch_page, batches(ids, size)):
                    page = save(name, response)
                    missing.extend(row["properties"][OID] for row in page["features"] if missing_geojson(row))
            for name, expected in batches(sorted(missing), size):
                native = save("native-" + name, download(query, f="json", where=WHERE,
                              objectIds=",".join(map(str, expected)), outFields=OID,
                              returnGeometry="true", outSR=25830))
                check_native(native, expected)
            if get_inventory("-end") != ids:
                raise ValueError("El inventario cambió durante la descarga")
            end = save("layer-end.json", download(LAYER, f="json"))
            if any(end.get(key) != layer.get(key) for key in ("editingInfo", "fields", "extent")):
                raise ValueError("Los metadatos de la capa cambiaron durante la descarga")
            metadata = catalogue["result"]
            reference = {"arcgisVersion": service["currentVersion"], "editingInfo": layer.get("editingInfo"),
                         "catalogueModifiedAt": metadata.get("metadata_modified"),
                         "catalogueLicense": metadata.get("license_title"),
                         "catalogueLicenseUrl": metadata.get("license_url"), "edition": None}
            archive.writestr("capture.json", encode({"layer": LAYER, "where": WHERE, "startedAt": started,
                                                    "reference": reference, "batchSize": size, "requests": requests}))
        temporary.rename(target)


def read_capture(path):
    with ZipFile(path) as archive:
        manifest = json.loads(archive.read("capture.json"))
        if (manifest["layer"], manifest["where"]) != (LAYER, WHERE):
            raise ValueError("La captura pertenece a otra capa o filtro")
        responses = {}
        for name, info in manifest["requests"].items():
            raw = archive.read(name)
            if len(raw) != info["bytes"] or digest(raw) != info["sha256"]:
                raise ValueError(f"Huella incorrecta: {name}")
            responses[name] = json.loads(raw)
        ids = inventory(responses["count.json"]["count"], responses["ids.json"])
        if inventory(responses["count-end.json"]["count"], responses["ids-end.json"]) != ids:
            raise ValueError("Los inventarios difieren")
        features = []
        for name, expected in batches(ids, manifest["batchSize"]):
            features.extend(check_page(responses[name], expected))
        missing = [row["properties"][OID] for row in features if missing_geojson(row)]
        for name, expected in batches(missing, manifest["batchSize"]):
            check_native(responses["native-" + name], expected)
        return manifest, features


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    capture(parser.parse_args().source)
