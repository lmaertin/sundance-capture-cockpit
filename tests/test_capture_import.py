import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from capture_webui.importer import normalize_annotation_payload, parse_capture_summary
from capture_webui.server import probe_signal_analyzer
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
        self.assertIn("No devices found", result["error"])

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


if __name__ == "__main__":
    unittest.main()
