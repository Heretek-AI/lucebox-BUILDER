#!/usr/bin/env python3
"""
Dynamic Shared Library Resolver for lucebox Binaries.

Runs a compiled binary (e.g. dflash_server) and recursively resolves/copies
missing shared library dependencies from the local ROCm installation directory.
"""

import argparse
import os
import shutil
import subprocess

# Safety cap on probe/copy rounds; a healthy binary converges in a few.
MAX_ROUNDS = 50


def find_libs_in_rocm(libname: str, rocm_dir: str) -> list[str]:
    """Locate a library (and its version-suffix siblings) in the ROCm tree."""
    matches = []
    for root, _, files in os.walk(rocm_dir):
        for f in files:
            # Exact name first; also pick up longer-versioned siblings so the
            # SONAME chain stays intact once rpath points at $ORIGIN.
            if f == libname or f.startswith(libname + "."):
                matches.append(os.path.join(root, f))
    return matches


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gather required shared libraries for lucebox binaries"
    )
    parser.add_argument(
        "--rocm-dir",
        default="/opt/rocm",
        help="Path to ROCm installation directory (default: /opt/rocm)",
    )
    parser.add_argument(
        "--dest-dir",
        default=os.path.join("dist", "bin"),
        help="Destination directory for binaries and libraries (default: dist/bin)",
    )
    parser.add_argument(
        "--binary",
        default="dflash_server",
        help="Binary executable to probe (default: dflash_server)",
    )

    args = parser.parse_args()
    rocm_dir = args.rocm_dir
    dest_dir = args.dest_dir
    binary = os.path.join(dest_dir, args.binary)

    if not os.path.exists(binary):
        raise FileNotFoundError(f"Binary not found: {binary}")

    os.makedirs(dest_dir, exist_ok=True)
    copied: set[str] = set()
    result = subprocess.run(
        [binary],
        capture_output=True,
        text=True,
        env={**os.environ, "LD_LIBRARY_PATH": dest_dir + ":" + os.environ.get("LD_LIBRARY_PATH", "")},
    )

    # Iteratively copy missing shared libraries until the loader succeeds
    rounds = 0
    while "error while loading shared libraries" in result.stderr:
        rounds += 1
        if rounds > MAX_ROUNDS:
            raise RuntimeError(
                f"Did not converge after {MAX_ROUNDS} rounds; last loader error:\n"
                f"{result.stderr.strip()}"
            )
        so_file = result.stderr.split("shared libraries: ")[1].split(": ")[0]
        candidates = find_libs_in_rocm(so_file, rocm_dir)
        if not candidates:
            raise RuntimeError(f"Could not find {so_file} in {rocm_dir}")
        for src in candidates:
            if src in copied:
                continue
            shutil.copy2(src, dest_dir, follow_symlinks=True)
            copied.add(src)
            print(f"Copied {src} -> {dest_dir}")
        result = subprocess.run(
            [binary],
            capture_output=True,
            text=True,
            env={**os.environ, "LD_LIBRARY_PATH": dest_dir + ":" + os.environ.get("LD_LIBRARY_PATH", "")},
        )


if __name__ == "__main__":
    main()
