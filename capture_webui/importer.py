from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from decoder.sr_reader import bit_statistics, load_capture


_TRANSLATIONS = {
    "Startaufnahme": "Recording started",
    "Stopaufnahme": "Recording stopped",
    "Panel-Tasten": "Panel buttons",
    "Display und Symbole": "Display and symbols",
    "Tasten fuer waermer/kaelter": "Warmer/Cooler buttons",
    "Symbole": "Symbols",
    "Annotationen": "Annotations",
    "keine": "none",
    "Keine": "None",
    "Aufnahme": "Recording",
    "aufgenommen": "recorded",
    "aktiv": "active",
    "Start": "Start",
    "Stopp": "Stop",
}


def normalize_annotation_payload(payload: dict[str, Any] | list[Any] | str | None) -> Any:
    """Translate common German labels from imported annotation payloads to English."""
    if isinstance(payload, dict):
        return {key: normalize_annotation_payload(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [normalize_annotation_payload(item) for item in payload]
    if isinstance(payload, str):
        return _translate_text(payload)
    return payload


def _translate_text(text: str) -> str:
    translated = text
    for source, target in _TRANSLATIONS.items():
        translated = translated.replace(source, target)
    return translated


def parse_capture_summary(path: str | Path) -> dict[str, Any]:
    """Read a .sr capture and return a JSON-serializable summary for import workflows."""
    capture_path = Path(path)
    capture = load_capture(capture_path)
    bit_stats = bit_statistics(capture.samples)
    stats = [
        {
            "bit": index,
            "ones_ratio": round(stat.ones_ratio, 6),
            "transitions": int(stat.transitions),
        }
        for index, stat in enumerate(bit_stats)
    ]

    return {
        "name": capture.name,
        "path": str(capture_path),
        "step": {
            "from_temp": capture.step.from_temp,
            "to_temp": capture.step.to_temp,
        },
        "sample_count": len(capture.samples),
        "stats": stats,
    }


def import_recording_bundle(recording_path: str | Path, annotations_path: str | Path | None = None) -> dict[str, Any]:
    """Import a capture and optional annotation JSON into a normalized structure."""
    capture_summary = parse_capture_summary(recording_path)
    annotations: list[dict[str, Any]] = []

    if annotations_path is not None:
        annotations_path = Path(annotations_path)
        if annotations_path.exists():
            with annotations_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                for item in payload.get("annotations", []) or []:
                    annotation = dict(item)
                    if "payload" in annotation:
                        annotation["payload"] = normalize_annotation_payload(annotation["payload"])
                    annotations.append(annotation)
            elif isinstance(payload, list):
                annotations = [
                    {"payload": normalize_annotation_payload(item)} if isinstance(item, dict) else item
                    for item in payload
                ]

    return {
        "capture": capture_summary,
        "annotations": annotations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a Sigrok capture and optional annotation JSON")
    parser.add_argument("recording", type=Path, help="Path to a .sr recording")
    parser.add_argument("annotations", nargs="?", type=Path, help="Optional path to a JSON annotation file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = import_recording_bundle(args.recording, args.annotations)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
