"""Exercise replay, unknown mappings, version comparison and incomplete captures."""

from argparse import ArgumentParser
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from capture_zoning import digest, encode
from generate_zoning import AUDIT, CODE, DATASET, MANIFEST, build, diff, load_rules, normalize_attributes, read


def incomplete_capture(source, target):
    with ZipFile(source) as original, ZipFile(target, "w", compression=ZIP_DEFLATED) as truncated:
        manifest = json.loads(original.read("capture.json"))
        name = "page-00000.json"
        page = json.loads(original.read(name))
        page["features"].pop()
        data = encode(page)
        manifest["requests"][name].update(sha256=digest(data), bytes=len(data))
        for member in original.namelist():
            if member not in (name, "capture.json"):
                truncated.writestr(member, original.read(member))
        truncated.writestr(name, data)
        truncated.writestr("capture.json", encode(manifest))


def check(source, release):
    with TemporaryDirectory(dir=release.parent) as scratch:
        root = Path(scratch)
        replay = root / "replay"
        build(source, replay)
        for name in (DATASET, AUDIT, MANIFEST):
            assert (release / name).read_bytes() == (replay / name).read_bytes(), name
        manifest = read(release / MANIFEST)
        assert all(not entries for key, entries in diff(manifest, read(replay / MANIFEST)).items()
                   if key != "pendingTotals")

        rules, reasons, _, _ = load_rules()
        attrs = dict(clase="SU", uso="ZZZZ", califi="ENS", tipouso=None, origen="PGOU")
        land, use, pending, _ = normalize_attributes(attrs, rules, reasons)
        assert land["class"] == "URBAN" and use["use"] == "UNKNOWN"
        assert pending["use"] == {"field": "uso", "code": "ZZZZ", "origin": "PGOU", "reason": "UNMAPPED_CODE"}
        attrs.update(uso=None, origen="PE2070")
        assert normalize_attributes(attrs, rules, reasons)[2]["use"]["reason"] == "NO_APPLICABLE_RULE"
        attrs["origen"] = "PGOU"
        assert normalize_attributes(attrs, rules, reasons)[1]["subtype"] == "MULTIFAMILY"
        rule = rules["califi", "ENS"][0]
        rules["califi", "ENS"].append(dict(rule, mappingId="conflicting-test-rule"))
        assert normalize_attributes(attrs, rules, reasons)[2]["use"]["reason"] == "AMBIGUOUS_RULE"

        old_area = {"geometry": "before", "classification": ["URBAN"], "use": ["RESIDENTIAL"], "pending": {}}
        new_area = {"geometry": "after", "classification": ["DEVELOPABLE"], "use": ["UNKNOWN"],
                    "pending": {"use": pending["use"]}}
        change = diff({"municipalityCode": CODE, "areas": {"same": old_area, "removed": old_area}},
                      {"municipalityCode": CODE, "areas": {"same": new_area, "added": new_area}})
        assert change["added"] == change["exportedAdded"] == ["added"]
        assert change["removed"] == change["exportedRemoved"] == ["removed"]
        assert all(change[key] == ["same"] for key in ("geometry", "classification", "use", "pending"))
        assert change["pendingTotals"] == {"classification": [0, 0], "use": [0, 2]}

        truncated = root / "incomplete.zip"
        failed_release = root / "failed-release"
        incomplete_capture(source, truncated)
        try:
            build(truncated, failed_release)
        except ValueError as error:
            assert "Página incompleta" in str(error)
        else:
            raise AssertionError("Se aceptó una extracción incompleta")
        assert not failed_release.exists()
        assert read(release / MANIFEST) == manifest
    print("OK: replay, new/ambiguous code, scope, diff, incomplete extraction and prior release preservation")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("release", type=Path)
    args = parser.parse_args()
    check(args.source, args.release)
