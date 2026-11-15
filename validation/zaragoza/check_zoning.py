"""Replay the Zaragoza capture and exercise new keys and incomplete extraction."""
import argparse
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory

from capture_zoning import encode
from generate_zoning import DATASET, HERE, MANIFEST, compare, digest, generate, load


def check(source, release, municipal=None):
    catalog = HERE / "municipal-mappings.json"
    with TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        replay = generate(source, scratch / "replay", catalog, municipal)
        actual, expected = load(replay / MANIFEST), load(release / MANIFEST)
        assert actual == expected
        for name, info in expected["objects"].items():
            assert (replay / name).read_bytes() == (release / name).read_bytes()
            assert digest((release / name).read_bytes()) == info["sha256"]
        assert not any(compare(expected, actual)["changed"].values())

        edited = scratch / "edited"
        copytree(source, edited)
        capture_path = edited / "capture.json"
        capture = load(capture_path)
        page_path = edited / capture["layers"]["usoglobal"]["pages"][0]["file"]
        page = load(page_path)
        feature = next(feature for feature in page["features"]
                       if feature["properties"]["uso_glob"] in {"R", "I"})
        area = f'50297:SIUa:{feature["properties"]["objectid"]}'
        feature["properties"]["uso_glob"] = "TEST-NEW-KEY"

        def save_page():
            data = encode(page)
            page_path.write_bytes(data)
            capture["files"][page_path.name].update(sha256=digest(data), bytes=len(data))
            capture_path.write_bytes(encode(capture))

        save_page()
        update = generate(edited, scratch / "updated", catalog, municipal)
        updated = load(update / MANIFEST)
        diff = compare(expected, updated)
        assert updated["areas"][area]["use"]["originalCode"] == "TEST-NEW-KEY"
        assert updated["areas"][area]["use"]["use"] == "UNKNOWN"
        assert updated["areas"][area]["pending"]["use"] == "Clave nueva sin equivalencia"
        assert diff["changed"] == {"geometry": [], "classification": [], "use": [area], "pending": [area]}
        assert diff["added"] == diff["removed"] == []

        page["features"].pop()
        page["numberReturned"] -= 1
        save_page()
        failed_output = scratch / "failed"
        try:
            generate(edited, failed_output, catalog, municipal)
        except ValueError as error:
            assert "incomplete page" in str(error)
        else:
            raise AssertionError("Accepted an incomplete extraction")
        assert not failed_output.exists()
        assert digest((release / DATASET).read_bytes()) == expected["objects"][DATASET]["sha256"]
        if municipal:
            truncated = scratch / "municipal-truncated"
            copytree(municipal, truncated)
            features_path = truncated / "features.json"
            features = load(features_path)
            features["features"].pop()
            features["numberReturned"] -= 1
            body = encode(features)
            features_path.write_bytes(body)
            metadata_path = truncated / "capture.json"
            metadata = load(metadata_path)
            metadata["files"]["features.json"].update(sha256=digest(body), bytes=len(body))
            metadata_path.write_bytes(encode(metadata))
            try:
                generate(source, failed_output, catalog, truncated)
            except ValueError as error:
                assert "Incomplete municipal qualification" in str(error)
            else:
                raise AssertionError("Accepted an incomplete municipal extraction")
            assert not failed_output.exists()
    print("Identical replay, new key recorded, incomplete extraction rejected, prior release intact.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("release", type=Path)
    parser.add_argument("--municipal", type=Path)
    args = parser.parse_args()
    check(args.capture, args.release, args.municipal)
