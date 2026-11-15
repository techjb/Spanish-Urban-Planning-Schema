"""Exercise repeatability, unknown keys, and incomplete extraction on a real capture."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from generate_zoning import HERE, compare, digest, encode, generate, load, normalize_attribute


def check(source):
    catalog = load(HERE / "municipal-mappings.json")["layers"]
    new_key = "Clave de prueba sin equivalencia"
    attrs = {"CalificacionPormenorizadaCA": new_key}
    value, reason = normalize_attribute(13, attrs, catalog)
    assert reason == "unmapped_key"
    assert value["use"] == "UNKNOWN" and value["originalCode"] == new_key
    value, reason = normalize_attribute(19, {"CalificacionPormenorizadaCA": "Industrial"}, catalog)
    assert value["use"] == "UNKNOWN" and reason == "unmapped_key"

    with TemporaryDirectory() as work:
        root = Path(work)
        first = generate(source, root / "first")
        second = generate(source, root / "second")
        for path in first.iterdir():
            assert path.read_bytes() == (second / path.name).read_bytes(), path.name
        left = load(first / "manifest.json")
        right = deepcopy(left)
        original, removed, *remaining = left["areas"]
        right["areas"]["ES-48020-test"] = right["areas"].pop(removed)
        right["areas"][original].update(geometry="geometry test", classification="classification test",
                                        use="use test", pending={"use": {"reason": reason}})
        diff = compare(left, right)
        assert diff["added"] == ["ES-48020-test"] and diff["removed"] == [removed]
        assert all(diff[key] == [original] for key in ("geometry", "classification", "use"))
        assert original in diff["pending"]

        incomplete = root / "incomplete.zip"
        with ZipFile(source) as archive, ZipFile(incomplete, "w") as target:
            capture = json.loads(archive.read("capture.json"))
            page = capture["pages"]["1"][0]
            obj = json.loads(archive.read(page))
            obj["features"].pop()
            changed = encode(obj)
            capture["requests"][page]["sha256"] = digest(changed)
            for name in archive.namelist():
                body = encode(capture) if name == "capture.json" else archive.read(name)
                target.writestr(name, changed if name == page else body)
        try:
            generate(incomplete, first.parent)
        except ValueError as error:
            assert "incomplete or duplicate extraction" in str(error), error
        else:
            raise AssertionError("Truncated extraction was accepted")
        assert load(first / "manifest.json") == left
        assert list(first.parent.iterdir()) == [first]
    print("Checksum replay, new key, layer context, version comparison and truncated extraction passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    check(parser.parse_args().source)
