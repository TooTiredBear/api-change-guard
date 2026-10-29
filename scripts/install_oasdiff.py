"""Install the pinned upstream executable after checking its published SHA-256."""

import argparse
import hashlib
import io
import platform
import tarfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "1.34.1"
RELEASE = f"https://github.com/oasdiff/oasdiff/releases/download/v{VERSION}"


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "api-change-guard-installer"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def install(destination: Path) -> Path:
    systems = {"Windows": "windows", "Linux": "linux", "Darwin": "darwin"}
    machines = {"AMD64": "amd64", "x86_64": "amd64", "arm64": "arm64", "aarch64": "arm64"}
    system = systems.get(platform.system())
    machine = machines.get(platform.machine())
    if system is None or machine is None:
        raise ValueError("Unsupported platform; install oasdiff from its upstream releases.")
    archive_name = f"oasdiff_{VERSION}_{system}_{'all' if system == 'darwin' else machine}.tar.gz"
    checksums = download(f"{RELEASE}/checksums.txt").decode("utf-8")
    expected = None
    for line in checksums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == archive_name:
            expected = parts[0]
            break
    if expected is None:
        raise ValueError(f"No published checksum for {archive_name}.")
    archive = download(f"{RELEASE}/{archive_name}")
    if hashlib.sha256(archive).hexdigest() != expected:
        raise ValueError("Upstream archive checksum mismatch; refusing installation.")
    executable = "oasdiff.exe" if system == "windows" else "oasdiff"
    if zipfile.is_zipfile(io.BytesIO(archive)):
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            payload = bundle.read(executable)
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            member = bundle.extractfile(executable)
            if member is None:
                raise ValueError("Executable missing from upstream archive.")
            payload = member.read()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / executable
    with target.open("xb") as output:
        output.write(payload)
    target.chmod(0o755)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(".tools"))
    args = parser.parse_args()
    try:
        target = install(args.directory)
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as error:
        parser.exit(2, f"Installation failed: {error}\n")
    print(f"Installed oasdiff v{VERSION}: {target.resolve()}")


if __name__ == "__main__":
    main()