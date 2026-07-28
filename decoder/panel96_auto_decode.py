#!/usr/bin/env python3
"""Auto-select anchor sets for Panel96 captures and run sigrok-cli decode."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Literal

ProfileName = Literal["global", "alt", "boot"]
LabelMode = Literal["semantic", "state"]

GLOBAL_ANCHORS_STATE = (
    "ST1=0x000004040060393FBF4F|0xFFFFFBFBFFFFC6C040B0;"
    "ST2=0x000006040062397D864F|0xFFFFF9FBFFFDC68279B0;"
    "ST3=0x0000040400603906EF5B|0xFFFFFBFBFFFFC6F910A4;"
    "DISPLAY_F1L=0x00000400006000380671|0xFFFFFBFFFFFFFFC7F98E;"
    "ST5=0x000000040064396FEF5B|0xFFFFFFFBFFFBC69010A4;"
    "ST6=0x400800000064ED665B06|0xBFF7FFFFFFFB1299A4F9;"
    "DISPLAY_U=0x00000400006000003E00|0xFFFFFBFFFFFFFFFFC1FF;"
    "DISPLAY_CIRC=0x00000400806039500439|0xFFFFFBFF7FFFC6AFFBC6;"
    "ST9=0x7FFFFBF7FFFF40C0A4F9|0x800004080060BF3F5B06;"
    "ST10=0x000004040060395BEF5B|0xFFFFFBFBFFFFC6A410A4;"
    "ST11=0x0000000000607706DB00|0xFFFFFFFFFFFF11F249FF;"
    "ST12=0x0000040400605B7DB00F|0xFFFFFBFBFFFFA4824FF0;"
    "ST13=0x000004100060BF3FFF00|0xFFFFFBEFFFFF40C000FF;"
    "ST14=0x0000080800C072CD0C9F|0xFFFFFBFBFFFFC69979B0;"
    "ST15=0xFFFFF9FBFFFDC68279B0|0xFFFFF9FBFFFDC682F9B0;"
    "ST16=0xFFFFFBFBFFFFC6C040B0|0xFFFFFBFBFFFFC6C0C0B0;"
    "ST17=0x0000000000C0EE0DB601|0xFFFFFFFFFFFF88F924FF;"
    "ST18=0xFFFFFFFFFFFF11F249FF|0xFFFFFFFFFFFF88F924FF"
)

GLOBAL_ANCHORS_SEMANTIC = (
    "ST1=0x000004040060393FBF4F|0xFFFFFBFBFFFFC6C040B0;"
    "ST2=0x000006040062397D864F|0xFFFFF9FBFFFDC68279B0;"
    "ST3=0x0000040400603906EF5B|0xFFFFFBFBFFFFC6F910A4;"
    "DISPLAY_F1L=0x00000400006000380671|0xFFFFFBFFFFFFFFC7F98E;"
    "TEMP_29_9C=0x000000040064396FEF5B|0xFFFFFFFBFFFBC69010A4;"
    "TIME_12_45=0x400800000064ED665B06|0xBFF7FFFFFFFB1299A4F9;"
    "DISPLAY_U=0x00000400006000003E00|0xFFFFFBFFFFFFFFFFC1FF;"
    "DISPLAY_CIRC=0x00000400806039500439|0xFFFFFBFF7FFFC6AFFBC6;"
    "TIME_12_00=0x7FFFFBF7FFFF40C0A4F9|0x800004080060BF3F5B06;"
    "ST10=0x000004040060395BEF5B|0xFFFFFBFBFFFFC6A410A4;"
    "ST11=0x0000000000607706DB00|0xFFFFFFFFFFFF11F249FF;"
    "ST12=0x0000040400605B7DB00F|0xFFFFFBFBFFFFA4824FF0;"
    "TIME_8_00=0x000004100060BF3FFF00|0xFFFFFBEFFFFF40C000FF;"
    "ST14=0x0000080800C072CD0C9F|0xFFFFFBFBFFFFC69979B0;"
    "ST15=0xFFFFF9FBFFFDC68279B0|0xFFFFF9FBFFFDC682F9B0;"
    "ST16=0xFFFFFBFBFFFFC6C040B0|0xFFFFFBFBFFFFC6C0C0B0;"
    "ST17=0x0000000000C0EE0DB601|0xFFFFFFFFFFFF88F924FF;"
    "ST18=0xFFFFFFFFFFFF11F249FF|0xFFFFFFFFFFFF88F924FF"
)

ALT_ANCHORS = (
    "ALT1=0x000004050060393FEF5B|0xFFFFF7F5FFFF8D802149;"
    "ALT2=0x0000080A00C0727F7E9F|0xFFFFFBFAFFFFC6C040B0;"
    "ALT3=0x00000C0F00C07B7FFFFF|0xFFFFFBFAFFFFC6C000A4;"
    "ALT4=0x000004050060393FEF5B|0xFFFFFFFFFFFFCFC031ED;"
    "ALT5=0x0000040500E0393FFF5B|0xFFFFFBFAFFFFC6C000A4;"
    "ALT6=0x000004050060393FEF5B|0x0000040500E0393FEF5B;"
    "ALT7=0xFFFFF7F5FFFF8D800149|0xFFFFFBFAFFFFC6C000A4;"
    "ALT8=0x0000080800C072DBCC9F|0xFFFFFBFBFFFFC69219B0;"
    "ALT9=0x000004050060393FA75B|0xFFFFFBFBFFFFC7C059A5;"
    "ALT10=0x000004040060396DE64F|0xFFFFF7F7FFFF8D243361;"
    "ALT11=0x00000C0C00C07BFFEEDF|0xFFFFFBFBFFFFC69219B0;"
    "ALT12=0xFFFFFBFBFFFFC69219B0|0xFFFFFBFBFFFFC79219B1;"
    "ALT13=0xFFFFFBFAFFFFC6C000A4|0xFFFFFBFBFFFFC7C001A5;"
    "ALT14=0xFFFFFBFAFFFFC6C010A4|0xFFFFFBFBFFFFC7C011A5;"
    "ALT15=0xFFFFFBFAFFFFC6C040B0|0xFFFFFBFBFFFFC7C041B1"
)

BOOT_ANCHORS = (
    "BOOT1=0x0000000000607706DB00|0xFFFFFFFFFFFF11F249FF;"
    "BOOT2=0x0000040400603966864F|0xFFFFF7F7FFFF8D32F361;"
    "BOOT3=0x0000080800C072CD0C9F|0xFFFFFBFBFFFFC69979B0;"
    "BOOT4=0x0000000000C0EE0DB601|0xFFFFFFFFFFFF88F924FF;"
    "BOOT5=0x0000080800C0727F7ECD|0xFFFFFBFBFFFFC6C04099;"
    "BOOT6=0x0000040400603966864F|0xFFFFFFFFFFFFCFBBFBF1;"
    "BOOT7=0x000004040060393FBF66|0xFFFFF7F7FFFF8D808133;"
    "BOOT8=0x000004040060395BE64F|0xFFFFF7F7FFFF8D483361;"
    "BOOT9=0x00000C0C00C07BEF8EDF|0xFFFFFBFBFFFFC69979B0;"
    "BOOT10=0xFFFFFFFFFFFF11F249FF|0xFFFFFFFFFFFF88F924FF;"
    "BOOT11=0xFFFFF7F7FFFF8D32F361|0xFFFFFBFBFFFFC69979B0;"
    "BOOT12=0x0000080800C072B7CC9F|0xFFFFFBFBFFFFC6A419B0;"
    "BOOT13=0x0000080800C0720C4E9F|0xFFFFFBFBFFFFC6F958B0;"
    "BOOT14=0xFFFFFBFBFFFFC69979B0|0xFFFFFBFBFFFFC79979B1;"
    "BOOT15=0x0000000000607706DB00|0xFFFFFFFFFFFF89F925FF;"
    "BOOT16=0x0000040400E03967864F|0xFFFFFBFBFFFFC69979B0;"
    "BOOT17=0xFFFFF7F7FFFF8D808133|0xFFFFFBFBFFFFC6C04099;"
    "BOOT18=0x0000040400603966864F|0x00000C0C00C07BEF8EDF"
)

ANCHORS_BY_PROFILE_STATE: dict[ProfileName, str] = {
    "global": GLOBAL_ANCHORS_STATE,
    "alt": ALT_ANCHORS,
    "boot": BOOT_ANCHORS,
}

ANCHORS_BY_PROFILE_SEMANTIC: dict[ProfileName, str] = {
    "global": GLOBAL_ANCHORS_SEMANTIC,
    "alt": ALT_ANCHORS,
    "boot": BOOT_ANCHORS,
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Auto-select Panel96 semantic anchors and run sigrok-cli."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Input .sr files")
    parser.add_argument("--clk", default="D7", help="Clock channel")
    parser.add_argument("--latch", default="D6", help="Latch channel")
    parser.add_argument("--data", default="D4", help="Primary data channel")
    parser.add_argument(
        "--profile",
        choices=("auto", "global", "alt", "boot"),
        default="auto",
        help="Force profile or auto-select by file path",
    )
    parser.add_argument(
        "--sigrokdecode-dir",
        type=Path,
        default=None,
        help="Optional SIGROKDECODE_DIR override",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print command and selected profile without executing",
    )
    parser.add_argument(
        "--label-mode",
        choices=("semantic", "state"),
        default="semantic",
        help="Use semantic labels for known values or raw state labels",
    )
    return parser.parse_args()


def detect_profile(input_path: Path) -> ProfileName:
    """Choose profile from capture path patterns."""
    lowered = input_path.as_posix().lower()
    name = input_path.name.lower()

    if "/boot/" in lowered or name.startswith("boot"):
        return "boot"

    if "/alt/" in lowered and name.startswith("pool_"):
        return "alt"

    return "global"


def resolve_sigrokdecode_dir(cli_value: Path | None) -> Path:
    """Resolve decoder path used by SIGROKDECODE_DIR."""
    if cli_value is not None:
        return cli_value.resolve()

    workspace_dir = Path(__file__).resolve().parent.parent
    return (workspace_dir / "sigrok-decoders").resolve()


def build_protocol_chain(
    clk: str,
    latch: str,
    data: str,
    anchors: str,
) -> str:
    """Build the stacked sigrok decoder chain string."""
    return (
        "panel96:"
        f"clk={clk}:latch={latch}:data={data},"
        "panel96_values:"
        "profile=none:"
        "mapping=none:"
        "autolearn=no:"
        "phase_aware=yes:"
        "semantic_guess=yes:"
        f"semantic_anchors={anchors}"
    )


def run_decode(
    input_path: Path,
    profile: ProfileName,
    protocol_chain: str,
    sigrokdecode_dir: Path,
    preview_only: bool,
) -> int:
    """Execute one sigrok-cli decode run."""
    command = [
        "sigrok-cli",
        "-i",
        str(input_path),
        "-P",
        protocol_chain,
        "-A",
        "panel96_values",
    ]

    print(f"=== {input_path} | profile={profile} ===")
    print("CMD:", " ".join(command))

    if preview_only:
        return 0

    env = os.environ.copy()
    env["SIGROKDECODE_DIR"] = str(sigrokdecode_dir)
    completed = subprocess.run(command, env=env, check=False)
    return int(completed.returncode)


def main() -> int:
    """Run auto decode for all provided inputs."""
    args = parse_args()
    sigrokdecode_dir = resolve_sigrokdecode_dir(args.sigrokdecode_dir)

    if not sigrokdecode_dir.exists():
        print(f"Decoder path not found: {sigrokdecode_dir}", file=sys.stderr)
        return 2

    if args.label_mode == "semantic":
        anchors_by_profile = ANCHORS_BY_PROFILE_SEMANTIC
    else:
        anchors_by_profile = ANCHORS_BY_PROFILE_STATE

    total_exit_code = 0
    for input_path in args.inputs:
        if not input_path.exists():
            print(f"Missing file: {input_path}", file=sys.stderr)
            total_exit_code = 1
            continue

        if args.profile == "auto":
            profile = detect_profile(input_path)
        else:
            profile = args.profile

        anchors = anchors_by_profile[profile]
        chain = build_protocol_chain(
            clk=args.clk,
            latch=args.latch,
            data=args.data,
            anchors=anchors,
        )
        exit_code = run_decode(
            input_path=input_path,
            profile=profile,
            protocol_chain=chain,
            sigrokdecode_dir=sigrokdecode_dir,
            preview_only=args.preview,
        )
        if exit_code != 0:
            total_exit_code = exit_code

    return total_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
