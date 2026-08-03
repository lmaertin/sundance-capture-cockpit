import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from capture_webui.importer import normalize_annotation_payload, parse_capture_summary
from capture_webui.server import (
    format_annotation_preview_entry,
    probe_signal_analyzer,
    reorder_annotations,
    update_annotation,
)
from decoder.decode_sr import summarize_annotation_bundle


class CaptureImportTests(unittest.TestCase):
    def test_parse_capture_summary_reads_logic_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            capture_path = Path(temp_dir) / "26-27_capture.sr"
            with zipfile.ZipFile(capture_path, "w") as archive:
                archive.writestr("logic-1", b"\x00\x03\x0f\xff\xaa")

            summary = parse_capture_summary(capture_path)

            self.assertEqual(summary["name"], capture_path.name)
            self.assertEqual(summary["step"]["from_temp"], 26)
            self.assertEqual(summary["step"]["to_temp"], 27)
            self.assertGreaterEqual(summary["stats"][0]["transitions"], 0)
            self.assertGreaterEqual(summary["stats"][0]["ones_ratio"], 0.0)

    def test_normalize_annotation_payload_translates_common_labels(self) -> None:
        payload = {"text": "Startaufnahme", "label": "Panel-Tasten"}

        normalized = normalize_annotation_payload(payload)

        self.assertEqual(normalized["text"], "Recording started")
        self.assertEqual(normalized["label"], "Panel buttons")

    def test_parse_capture_summary_accepts_filenames_without_temperature_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            capture_path = Path(temp_dir) / "sample_capture.sr"
            with zipfile.ZipFile(capture_path, "w") as archive:
                archive.writestr("logic-1", b"\x01\x02\x03")

            summary = parse_capture_summary(capture_path)

            self.assertEqual(summary["step"]["from_temp"], 0)
            self.assertEqual(summary["step"]["to_temp"], 0)

    def test_summarize_annotation_bundle_counts_display_and_button_events(self) -> None:
        bundle = {
            "annotations": [
                {"kind": "display_state", "payload": {"text": "12:00"}},
                {"kind": "button_press", "payload": {}},
                {"kind": "display_state", "payload": {"text": "8:00"}},
            ]
        }

        summary = summarize_annotation_bundle(bundle)

        self.assertEqual(summary["annotation_count"], 3)
        self.assertEqual(summary["display_state_count"], 2)
        self.assertEqual(summary["button_press_count"], 1)

    def test_format_annotation_preview_entry_uses_names_for_button_presses(self) -> None:
        button_preview = format_annotation_preview_entry(
            "button_press",
            {"name": "Select Button"},
        )
        warmer_preview = format_annotation_preview_entry(
            "button_press",
            {"name": "Warmer", "direction": "warmer"},
        )
        display_preview = format_annotation_preview_entry(
            "display_state",
            {"value": "29.9C", "cycleNumber": 1, "symbols": ["heat", "fan"]},
        )

        self.assertEqual(button_preview, "button_press: Select Button")
        self.assertEqual(warmer_preview, "button_press: Warmer")
        self.assertEqual(display_preview, "display_state: value=29.9C; cycle=1; symbols=heat,fan")

    def test_update_annotation_changes_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "annotations.db"
            with patch("capture_webui.server.DB_PATH", db_path):
                from capture_webui.server import ensure_dirs, init_db

                ensure_dirs()
                init_db()
                from capture_webui.server import add_annotation, fetch_annotations

                recording_id = 1
                with patch("capture_webui.server.insert_recording", return_value=recording_id):
                    pass

                with patch("capture_webui.server.db_connect") as db_connect_mock:
                    import sqlite3

                    conn = sqlite3.connect(db_path)
                    conn.execute(
                        "INSERT INTO recordings (id, name, samplerate, channels, file_path, status, start_time, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (recording_id, "demo", "24MHz", "D4", "demo.sr", "finished", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
                    )
                    conn.commit()
                    conn.close()

                annotation_id = add_annotation(recording_id, 0, "button_press", {"button": "A"})
                result = update_annotation(annotation_id, "button_press", {"button": "B", "name": "Select"})

                self.assertTrue(result["ok"])
                self.assertEqual(result["annotation"]["payload"]["button"], "B")
                self.assertEqual(result["annotation"]["payload"]["name"], "Select")

    def test_reorder_annotations_updates_positions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "annotations.db"
            with patch("capture_webui.server.DB_PATH", db_path):
                from capture_webui.server import ensure_dirs, init_db

                ensure_dirs()
                init_db()
                from capture_webui.server import add_annotation, fetch_annotations

                recording_id = 1
                with patch("capture_webui.server.insert_recording", return_value=recording_id):
                    pass

                with patch("capture_webui.server.db_connect") as db_connect_mock:
                    import sqlite3

                    conn = sqlite3.connect(db_path)
                    conn.execute(
                        "INSERT INTO recordings (id, name, samplerate, channels, file_path, status, start_time, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (recording_id, "demo", "24MHz", "D4", "demo.sr", "finished", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
                    )
                    conn.commit()
                    conn.close()

                first_id = add_annotation(recording_id, 0, "display_state", {"value": "A"})
                second_id = add_annotation(recording_id, 1, "display_state", {"value": "B"})

                result = reorder_annotations(recording_id, [second_id, first_id])

                self.assertTrue(result["ok"])
                ordered = fetch_annotations(recording_id)
                self.assertEqual([entry["id"] for entry in ordered], [second_id, first_id])

    def test_probe_signal_analyzer_reports_missing_hardware(self) -> None:
        completed = type(
            "CompletedProcess",
            (),
            {
                "returncode": 0,
                "stdout": "",
                "stderr": "No devices found.\n",
            },
        )

        with patch("capture_webui.server.subprocess.run", return_value=completed):
            result = probe_signal_analyzer("fx2lafw")

        self.assertFalse(result["ok"])
        self.assertIn("No signal analyzer hardware detected", result["error"])

    def test_probe_signal_analyzer_accepts_device_scan_output(self) -> None:
        completed = type(
            "CompletedProcess",
            (),
            {
                "returncode": 0,
                "stdout": "Found 1 device\n",
                "stderr": "",
            },
        )

        with patch("capture_webui.server.subprocess.run", return_value=completed):
            result = probe_signal_analyzer("fx2lafw")

        self.assertTrue(result["ok"])
        self.assertEqual(result["command"], ["sigrok-cli", "--scan", "-d", "fx2lafw"])

    def test_probe_signal_analyzer_reports_firmware_upload_failure(self) -> None:
        completed = type(
            "CompletedProcess",
            (),
            {
                "returncode": 0,
                "stdout": "The following devices were found:\nfx2lafw - Saleae Logic with 8 channels: D0 D1 D2 D3 D4 D5 D6 D7\n",
                "stderr": "sr: resource: Failed to open resource 'fx2lafw-saleae-logic.fw'\nsr: fx2lafw: Firmware upload failed for device 1.2 (logical), name fx2lafw-saleae-logic.fw.\n",
            },
        )

        with patch("capture_webui.server.subprocess.run", return_value=completed):
            result = probe_signal_analyzer("fx2lafw")

        self.assertFalse(result["ok"])
        self.assertIn("Signal analyzer detected", result["error"])


if __name__ == "__main__":
    unittest.main()
