"""Prepare or publish a validated Barcelona release with immutable S3 keys."""
import argparse
import base64
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile


BUCKET = "goolzoom-sups-data"
REGION = "eu-west-3"
PREFIX = "08019 - Barcelona"
DATASET = "sups-zoning-areas.json"
AUDIT = "zoning-audit.json"
PACKAGE = "barcelona-zoning.zip"
MANIFEST = "manifest.json"


def prepare(package, directory):
    package_data = package.read_bytes()
    with ZipFile(package) as archive:
        manifest = json.loads(archive.read(MANIFEST))
        if manifest["municipalityCode"] != "08019":
            raise ValueError("Expected a Barcelona release")
        payload = {name: archive.read(name) for name in (DATASET, AUDIT)}
        for name, data in payload.items():
            if sha256(data).hexdigest() != manifest["outputs"][name]:
                raise ValueError(f"Manifest checksum mismatch: {name}")
        if sha256(archive.read("amb-source.zip")).hexdigest() != manifest["ambArchiveSha256"]:
            raise ValueError("AMB archive checksum mismatch")
        if "muc" in manifest:
            if sha256(archive.read("muc-source.zip")).hexdigest() != manifest["muc"]["archiveSha256"]:
                raise ValueError("MUC archive checksum mismatch")
        records = json.loads(payload[DATASET])
        ids = {record["areaId"] for record in records}
        if len(records) != len(ids) or ids != manifest["areas"].keys():
            raise ValueError("Dataset and manifest area inventories disagree")
        counts = manifest["counts"]
        if (not ids or len(ids) != counts["exported"]
                or counts["exported"] + counts["geometryRejected"] != counts["downloaded"]):
            raise ValueError("Inconsistent release counts")

    payload[PACKAGE] = package_data
    package_hash = sha256(package_data).hexdigest()
    capture_time = manifest["amb"]["startedAt"]
    version = f"{datetime.fromisoformat(capture_time):%Y%m%dT%H%M%S}-{package_hash[:16]}"
    prefix = f"{PREFIX}/{version}"
    manifest["publication"] = {
        "version": version,
        "s3Uri": f"s3://{BUCKET}/{prefix}/",
        "objects": {name: {"sha256": sha256(data).hexdigest(), "bytes": len(data)}
                    for name, data in payload.items()},
        "attribution": ["Fuente de los datos: Área Metropolitana de Barcelona (AMB)",
                        "Mapa urbanístic de Catalunya, Generalitat de Catalunya"] if "muc" in manifest
                       else ["Fuente de los datos: Área Metropolitana de Barcelona (AMB)"],
    }
    payload[MANIFEST] = (json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n").encode()
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in payload.items():
        (directory / name).write_bytes(data)
    return prefix, tuple(payload)


def publish(prefix, names, directory, profile):
    cli = ["aws", "--region", REGION, "--no-cli-pager"]
    if profile:
        cli.extend(["--profile", profile])
    with TemporaryDirectory() as scratch:
        verified = Path(scratch) / "download"
        for name in names:  # The manifest marks a complete release and goes last.
            path = directory / name
            data_hash = sha256(path.read_bytes()).digest()
            key = f"{prefix}/{name}"
            remote = ["--bucket", BUCKET, "--key", key]
            put = subprocess.run(
                [*cli, "s3api", "put-object", *remote, "--body", str(path), "--if-none-match", "*",
                 "--checksum-sha256", base64.b64encode(data_hash).decode(),
                 "--content-type", "application/zip" if path.suffix == ".zip" else "application/json"],
                capture_output=True, text=True,
            )
            if put.returncode and "PreconditionFailed" not in put.stderr:
                raise RuntimeError(put.stderr.strip() or f"S3 rejected {key}")
            subprocess.run([*cli, "s3api", "get-object", *remote, str(verified)],
                           check=True, stdout=subprocess.DEVNULL)
            if sha256(verified.read_bytes()).digest() != data_hash:
                raise ValueError(f"S3 content differs from validated file: {key}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--profile")
    args = parser.parse_args()
    prefix, names = prepare(args.package, args.directory)
    if args.publish:
        publish(prefix, names, args.directory, args.profile)
    print(f"s3://{BUCKET}/{prefix}/")


if __name__ == "__main__":
    main()
