"""Publish an immutable Bilbao release and compare each downloaded object with its local bytes."""
import argparse
from base64 import b64encode
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from generate_zoning import BUCKET, INE, OUTPUTS, PREFIX, digest, load, validate


REGION = "eu-west-3"
NAMES = (*OUTPUTS, "manifest.json")


def verify_release(directory):
    manifest = load(directory / "manifest.json")
    version = manifest["version"]
    prefix = f"{PREFIX}/{version}"
    if (manifest["municipalityCode"] != INE
            or not re.fullmatch(r"\d{8}T\d{6}Z-[a-f0-9]{16}", version)
            or set(manifest["objects"]) != set(OUTPUTS)
            or manifest["s3Uri"] != f"s3://{BUCKET}/{prefix}/"):
        raise ValueError("Invalid release manifest")
    for name in OUTPUTS:
        body = (directory / name).read_bytes()
        if manifest["objects"][name] != {"bytes": len(body), "sha256": digest(body)}:
            raise ValueError(f"Checksum or size differs: {name}")
    records = load(directory / OUTPUTS[0])
    ids = {record["areaId"] for record in records}
    counts = manifest["counts"]
    if (not ids or len(ids) != len(records) or ids != manifest["areas"].keys()
            or counts["exported"] != len(ids)
            or counts["downloaded"] != len(ids) + counts["geometryRejected"]):
        raise ValueError("Records and release inventory disagree")
    validate(records)
    return prefix


def content_type(name):
    return "application/zip" if name.endswith(".zip") else "application/json"


def put_cli(directory, prefix, profile):
    cli = ["aws", "--no-cli-pager", "--region", REGION]
    if profile:
        cli.extend(["--profile", profile])
    with TemporaryDirectory() as work:
        for name in NAMES:
            source = directory / name
            body = source.read_bytes()
            args = ["--bucket", BUCKET, "--key", f"{prefix}/{name}"]
            action = subprocess.run(
                [*cli, "s3api", "put-object", *args, "--body", str(source),
                 "--checksum-sha256", b64encode(bytes.fromhex(digest(body))).decode(),
                 "--content-type", content_type(name), "--if-none-match", "*"],
                text=True, capture_output=True)
            if action.returncode and "PreconditionFailed" not in action.stderr:
                raise RuntimeError(action.stderr.strip())
            target = Path(work) / name
            subprocess.run([*cli, "s3api", "get-object", *args, str(target)],
                           check=True, stdout=subprocess.DEVNULL)
            if target.read_bytes() != body:
                raise ValueError(f"S3 content differs: {name}")
            print(f"Verified {name} {digest(body)}", flush=True)


def put_presigned(directory, links):
    if set(links) != set(NAMES):
        raise ValueError("Expected paired PUT and GET URLs for every release object")
    for name in NAMES:  # A verified manifest is the completion marker.
        body = (directory / name).read_bytes()
        headers = {"If-None-Match": "*", "Content-Type": content_type(name)}
        try:
            request = Request(links[name]["upload"], data=body, method="PUT", headers=headers)
            with urlopen(request, timeout=120) as result:
                print(f"PUT {name}: {result.status}", flush=True)
        except HTTPError as error:
            if error.code != 412:
                raise RuntimeError(f"S3 PUT {name}: HTTP {error.code}") from None
        try:
            with urlopen(links[name]["download"], timeout=120) as result:
                if result.read() != body:
                    raise ValueError(f"S3 content differs: {name}")
        except HTTPError as error:
            raise RuntimeError(f"S3 GET {name}: HTTP {error.code}") from None
        print(f"Verified {name} {digest(body)}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--presigned-stdin", action="store_true")
    args = parser.parse_args()
    prefix = verify_release(args.directory)
    if args.presigned_stdin:
        put_presigned(args.directory, json.loads(sys.stdin.readline()))
    elif not args.verify_only:
        put_cli(args.directory, prefix, args.profile)
    print(f"s3://{BUCKET}/{prefix}/")
