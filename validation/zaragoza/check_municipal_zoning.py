"""Verify the primary municipal release and its handling of source changes."""
import argparse
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from jsonschema import Draft202012Validator

from capture_zoning import encode
from generate_municipal_zoning import CLASS_CATALOG, REGIONAL_BASELINE, ROOT, generate, source_records
from generate_zoning import AUDIT, MANIFEST, digest, load
from municipal_qualification import CLASS_LAYER, read_snapshot
from publish_zoning import publication


def check(release):
    _, names = publication(release)
    manifest = load(release / MANIFEST)
    with TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        with ZipFile(release / manifest["sourceArchive"]) as archive:
            assert archive.testzip() is None
            archive.extractall(scratch)
        generate(scratch / "classification", scratch / "urban", scratch / "non-urban",
                 scratch / REGIONAL_BASELINE, scratch / "replay")
        replay = scratch / "replay" / manifest["version"]
        for name in names:
            assert (replay / name).read_bytes() == (release / name).read_bytes()

        directory = scratch / "classification"
        _, features = read_snapshot(directory, CLASS_LAYER)
        original = next(feature for feature in features if feature["properties"]["clasificacion"] == "SU")
        changed = deepcopy(original)
        changed["properties"]["clasificacion"] = "TEST-NEW-CLASS"
        spec = load(CLASS_CATALOG)
        validator = Draft202012Validator(load(ROOT / "schemas/v1/zoning-area.schema.json"))
        records, inventory, _ = source_records([changed], CLASS_LAYER, spec, validator, {})
        assert records[0]["landClassification"]["class"] == "UNKNOWN"
        assert records[0]["landClassification"]["originalCode"] == "TEST-NEW-CLASS"
        assert inventory["counts"]["pendingAreas"] == 1

        data_path = directory / "features.json"
        data = load(data_path)
        data["features"].pop()
        data["numberReturned"] -= 1
        body = encode(data)
        data_path.write_bytes(body)
        capture_path = directory / "capture.json"
        capture = load(capture_path)
        capture["files"]["features.json"].update(sha256=digest(body), bytes=len(body))
        capture_path.write_bytes(encode(capture))
        try:
            read_snapshot(directory, CLASS_LAYER)
        except ValueError as error:
            assert "Incomplete municipal qualification response" in str(error)
        else:
            raise AssertionError("Accepted incomplete municipal classification")

    classification = load(release / AUDIT)["classification"]
    for area_id, duplicate in classification["duplicateGeometries"].items():
        if duplicate["conflictingAttributes"]:
            assert manifest["areas"][area_id]["classification"]["class"] == "UNKNOWN"
    print("Byte-identical archive replay; unknown key, conflicting duplicate and incomplete capture checked.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    check(parser.parse_args().release)
