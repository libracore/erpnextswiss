"""Verify built Python distributions retain the app, not the separate PHP gateway."""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile


RUNTIME_SUFFIXES = {
    ".py", ".json", ".js", ".css", ".html", ".csv", ".txt", ".md", ".svg", ".png", ".ico",
    ".xsd", ".sql", ".woff", ".wasm", ".xlsx", ".sh",
}


def digest(content):
    return hashlib.sha256(content).hexdigest()


def wheel_files(path):
    with zipfile.ZipFile(path) as archive:
        names = [info.filename for info in archive.infolist() if not info.is_dir()]
        if len(names) != len(set(names)):
            raise AssertionError("Duplicate wheel members")
        for name in names:
            parts = PurePosixPath(name).parts
            if not parts or name.startswith("/") or ".." in parts or "\\" in name:
                raise AssertionError("Unsafe wheel member")
            if parts[0] != "erpnextswiss" and not re.fullmatch(r"erpnextswiss-[a-zA-Z0-9._+!-]+\.dist-info", parts[0]):
                raise AssertionError(f"Unintended top-level wheel content: {parts[0]}")
        return {name: digest(archive.read(name)) for name in names if name.startswith("erpnextswiss/")}


def source_archive_files(path):
    with tarfile.open(path, "r:gz") as archive:
        files = {}
        roots = set()
        for member in archive.getmembers():
            parts = PurePosixPath(member.name).parts
            if not parts or member.name.startswith("/") or ".." in parts or "\\" in member.name:
                raise AssertionError("Unsafe source archive member")
            roots.add(parts[0])
            relative = "/".join(parts[1:])
            if relative.startswith("gateway/"):
                raise AssertionError("Gateway must be built separately, not distributed as a Python package")
            if relative.startswith("erpnextswiss/") and not member.isdir():
                if not member.isfile() or relative in files:
                    raise AssertionError("Linked or duplicate app resource")
                files[relative] = digest(archive.extractfile(member).read())
        if len(roots) != 1:
            raise AssertionError("Expected a single source archive root")
        return files


def verify(source, wheel, sdist, baseline_wheel=None):
    paths = [path for path in (source / "erpnextswiss").rglob("*")
             if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}]
    unknown = sorted(path.relative_to(source).as_posix() for path in paths if path.suffix.lower() not in RUNTIME_SUFFIXES)
    if unknown:
        raise AssertionError(f"New resource formats require an explicit packaging decision: {unknown}")
    expected = {
        path.relative_to(source).as_posix(): digest(path.read_bytes())
        for path in paths
    }
    if not expected:
        raise AssertionError("No app sources found")
    artifacts = {"wheel": wheel_files(wheel), "sdist": source_archive_files(sdist)}
    for kind, content in artifacts.items():
        missing = sorted(set(expected) - set(content))
        changed = sorted(name for name in expected.keys() & content.keys() if expected[name] != content[name])
        if missing or changed:
            raise AssertionError(f"{kind}: missing={missing}; changed={changed}")
    if baseline_wheel:
        baseline = wheel_files(baseline_wheel)
        changed = sorted(name for name, value in baseline.items() if artifacts["wheel"].get(name) != value)
        if changed:
            raise AssertionError(f"Existing packaged app content changed or removed: {changed}")
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument("--baseline-wheel", type=Path)
    args = parser.parse_args()
    count = verify(args.source, args.wheel, args.sdist, args.baseline_wheel)
    print(f"PASS {count} byte-identical app resources in wheel and sdist; separate gateway excluded")


if __name__ == "__main__":
    main()
