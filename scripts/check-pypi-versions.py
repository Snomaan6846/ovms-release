#!/usr/bin/env python3
"""check-pypi-versions.py — Check if dependencies in requirements.txt have newer versions on PyPI.

Used in Phase 0 pre-flight to alert about potentially outdated Python deps.
"""

import json
import sys
import urllib.request
from pathlib import Path


PYPI_URL = "https://pypi.org/pypi/{package}/json"

COMMON_DEPS = [
    "numpy",
    "grpcio",
    "protobuf",
    "opencv-python",
]


def get_pypi_latest(package: str) -> str | None:
    """Fetch latest version from PyPI."""
    try:
        url = PYPI_URL.format(package=package)
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            return data["info"]["version"]
    except Exception:
        return None


def parse_requirements(path: Path) -> dict[str, str]:
    """Parse requirements.txt into {name: version_spec}."""
    deps = {}
    if not path.exists():
        return deps
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for sep in ["==", ">=", "<=", "~="]:
            if sep in line:
                name, ver = line.split(sep, 1)
                deps[name.strip().lower()] = ver.strip()
                break
        else:
            deps[line.lower()] = ""
    return deps


def main():
    # Try to find requirements.txt in the current repo
    req_paths = [
        Path("requirements.txt"),
        Path("src/requirements.txt"),
    ]

    deps_found = {}
    for p in req_paths:
        deps_found.update(parse_requirements(p))

    if not deps_found:
        deps_found = {d: "" for d in COMMON_DEPS}
        print("  (no requirements.txt found — checking common OVMS deps)")

    print("  Package                  Pinned      Latest")
    print("  " + "-" * 50)

    for pkg, pinned_ver in sorted(deps_found.items()):
        latest = get_pypi_latest(pkg)
        if latest is None:
            status = "?"
        elif not pinned_ver:
            status = latest
        elif pinned_ver == latest:
            status = f"{latest} (OK)"
        else:
            status = f"{latest} (UPDATE)"
        print(f"  {pkg:<25} {pinned_ver or '-':<11} {status}")


if __name__ == "__main__":
    main()
