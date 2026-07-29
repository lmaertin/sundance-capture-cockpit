#!/usr/bin/env python3
"""Collect remaining UNKNOWN signature pairs from auto-decoder output."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import subprocess
import sys
from typing import DefaultDict

ProfileName = str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect UNKNOWN signatures from panel96_auto_decode runs."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Input files or directories with .sr captures",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="Max candidate count per profile",
    )
    parser.add_argument(
        "--python",
        default="/Users/lukas/sundance/.venv/bin/python",
        help="Python interpreter used to run panel96_auto_decode.py",
    )
    return parser.parse_args()


def expand_inputs(paths: list[Path]) -> list[Path]:
    """Expand directories recursively and return sorted .sr files."""
    files: list[Path] = []
    for item in paths:
        if item.is_dir():
            files.extend(sorted(item.rglob("*.sr")))
        elif item.suffix.lower() == ".sr":
            files.append(item)

    unique: list[Path] = []
    seen: set[Path] = set()
    for file_path in files:
        resolved = file_path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(file_path)
    return sorted(unique)


def detect_profile(path: Path) -> ProfileName:
    """Mirror profile selection logic from panel96_auto_decode."""
    lowered = path.as_posix().lower()
    name = path.name.lower()
    if "/boot/" in lowered or name.startswith("boot"):
        return "boot"
    if "/alt/" in lowered and name.startswith("pool_"):
        return "alt"
    return "global"


def extract_unknown_pairs(output_text: str) -> list[str]:
    """Extract signature rows that directly follow UNKNOWN value rows."""
    pairs: list[str] = []
    last_was_unknown = False

    for line in output_text.splitlines():
        if not line.startswith("panel96_values-1: "):
            continue
        value = line.split(": ", 1)[1].strip()

        is_value_row = (
            "count=" not in value and "|" not in value and not value.startswith("0x")
        )
        if is_value_row:
            last_was_unknown = value.startswith("UNKNOWN")
            continue

        if last_was_unknown:
            pairs.append(value)
            last_was_unknown = False

    return pairs


def main() -> int:
    """Entry point."""
    args = parse_args()
    files = expand_inputs(args.inputs)
    if not files:
        print("No .sr inputs found.")
        return 1

    runner = Path(__file__).resolve().parent / "panel96_auto_decode.py"
    if not runner.exists():
        print(f"Missing runner: {runner}", file=sys.stderr)
        return 2

    by_profile: DefaultDict[ProfileName, Counter[str]] = defaultdict(Counter)
    by_file: dict[Path, Counter[str]] = {}

    for file_path in files:
        cmd = [args.python, str(runner), str(file_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            print(f"WARN decode failed: {file_path} (rc={proc.returncode})", file=sys.stderr)
            continue

        unknown_pairs = extract_unknown_pairs(proc.stdout)
        if not unknown_pairs:
            continue

        counts = Counter(unknown_pairs)
        by_file[file_path] = counts

        profile = detect_profile(file_path)
        by_profile[profile].update(counts)

    print("=== UNKNOWN summary by profile ===")
    for profile in sorted(by_profile):
        total = sum(by_profile[profile].values())
        unique = len(by_profile[profile])
        print(f"{profile}: total={total} unique={unique}")

    print("\n=== Top UNKNOWN pairs per profile ===")
    for profile in sorted(by_profile):
        print(f"[{profile}]")
        for pair, count in by_profile[profile].most_common(args.top):
            print(f"  {count:5d} {pair}")

    print("\n=== Candidate anchors to add ===")
    for profile in sorted(by_profile):
        prefix = "UNK"
        if profile == "alt":
            prefix = "ALTX"
        elif profile == "boot":
            prefix = "BOOTX"
        elif profile == "global":
            prefix = "STX"

        anchors: list[str] = []
        for index, (pair, _) in enumerate(by_profile[profile].most_common(args.top), start=1):
            if "|" not in pair:
                continue
            anchors.append(f"{prefix}{index}={pair}")
        print(f"{profile}: {';'.join(anchors)}")

    print("\n=== Files with UNKNOWN pairs ===")
    for file_path in sorted(by_file):
        total = sum(by_file[file_path].values())
        unique = len(by_file[file_path])
        top = by_file[file_path].most_common(3)
        top_text = ", ".join([f"{count}x {pair}" for pair, count in top])
        print(f"{file_path}: total={total} unique={unique} top={top_text}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())