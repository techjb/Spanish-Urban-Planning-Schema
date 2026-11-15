"""Publish a validated Zaragoza release with the AWS CLI and verify each object."""
import argparse
from base64 import b64encode
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from generate_zoning import (
    AUDIT, DATASET, INE, MANIFEST, MUNICIPAL_DATASET, NON_URBAN_DATASET, SOURCES, digest, load,
)

BUCKET = "goolzoom-sups-data"
REGION = "eu-west-3"


def publication(directory):
    manifest = load(directory / MANIFEST)
    version = manifest["version"]
    prefix = f"{INE} - Zaragoza/{version}"
    archive = manifest.get("sourceArchive", SOURCES)
    if archive not in {SOURCES, "municipal-sources.zip"}:
        raise ValueError("Unexpected source archive")
    names = (DATASET, AUDIT, archive)
    if "municipalZoningAreas" in manifest:
        names += (MUNICIPAL_DATASET,)
    if "nonUrbanZoningAreas" in manifest:
        names += (NON_URBAN_DATASET,)
    if (manifest["municipalityCode"] != INE or not re.fullmatch(r"\d{8}T\d{6}Z-[a-f0-9]{16}", version)
            or manifest["s3Uri"] != f"s3://{BUCKET}/{prefix}/"
            or set(manifest["objects"]) != set(names)):
        raise ValueError("Invalid release manifest")
    for name, info in manifest["objects"].items():
        body = (directory / name).read_bytes()
        if len(body) != info["bytes"] or digest(body) != info["sha256"]:
            raise ValueError(f"Release checksum mismatch: {name}")
    return prefix, (*names, MANIFEST)


def publish(directory, profile):
    prefix, names = publication(directory)
    cli = ["aws", "--region", REGION, "--no-cli-pager"]
    if profile:
        cli.extend(["--profile", profile])
    with TemporaryDirectory() as scratch:
        downloaded = Path(scratch) / "object"
        for name in names:
            path = directory / name
            checksum = digest(path.read_bytes())
            remote = ["--bucket", BUCKET, "--key", f"{prefix}/{name}"]
            result = subprocess.run(
                [*cli, "s3api", "put-object", *remote, "--body", str(path),
                 "--if-none-match", "*", "--checksum-sha256", b64encode(bytes.fromhex(checksum)).decode(),
                 "--content-type", "application/zip" if path.suffix == ".zip" else "application/json"],
                capture_output=True, text=True,
            )
            if result.returncode and "PreconditionFailed" not in result.stderr:
                raise RuntimeError(result.stderr.strip())
            subprocess.run([*cli, "s3api", "get-object", *remote, str(downloaded)],
                           check=True, stdout=subprocess.DEVNULL)
            if digest(downloaded.read_bytes()) != checksum:
                raise ValueError(f"Remote object differs: {name}")
    print(f"s3://{BUCKET}/{prefix}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("--profile")
    args = parser.parse_args()
    publish(args.release, args.profile)
