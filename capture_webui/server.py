#!/usr/bin/env python3
"""Local web UI server for sigrok recordings and manual annotations."""

from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import subprocess
import threading
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "static"
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "annotations.db"
RECORDINGS_DIR = Path(
    os.environ.get("CAPTURE_RECORDINGS_DIR", os.environ.get("SUNDANCE_RECORDINGS_DIR", ROOT_DIR / "recordings"))
)


def now_iso() -> str:
    """Return current UTC timestamp as ISO8601 string."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def safe_name(name: str) -> str:
    """Create a filesystem-safe name from user input."""
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name.strip())
    compact = "-".join(part for part in cleaned.split("-") if part)
    return compact or "recording"


@dataclass
class ActiveJob:
    """Runtime state for an active recording."""

    recording_id: int
    file_path: str
    started_at_iso: str
    started_monotonic: float
    samplerate: str
    channels: str
    simulate: bool
    process: subprocess.Popen[str] | None = None
    stop_event: threading.Event | None = None
    worker: threading.Thread | None = None
    last_error: str | None = None


@dataclass
class AppState:
    """Shared mutable application state guarded by a lock."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    active: ActiveJob | None = None


STATE = AppState()


def ensure_dirs() -> None:
    """Create required directories for database and recordings."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


def db_connect() -> sqlite3.Connection:
    """Open a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database schema if needed."""
    with db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sequence TEXT,
                notes TEXT,
                samplerate TEXT NOT NULL,
                channels TEXT NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER NOT NULL,
                ts_ms INTEGER NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(recording_id) REFERENCES recordings(id)
            )
            """
        )
        conn.commit()

    with db_connect() as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(annotations)").fetchall()}
        if "position" not in columns:
            conn.execute("ALTER TABLE annotations ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
            conn.commit()

    with db_connect() as conn:
        conn.execute(
            "UPDATE annotations SET position = id WHERE COALESCE(position, 0) = 0"
        )
        conn.commit()


def iso_from_timestamp(timestamp: float) -> str:
    """Convert POSIX timestamp to UTC ISO8601 string without microseconds."""
    return datetime.utcfromtimestamp(timestamp).replace(microsecond=0).isoformat() + "Z"


def sync_recordings_from_disk() -> int:
    """Import existing .sr files into DB when no matching recording row exists."""
    with db_connect() as conn:
        existing_rows = conn.execute("SELECT file_path FROM recordings").fetchall()
        known_paths = {str(row["file_path"]) for row in existing_rows}

        imported = 0
        for sr_file in sorted(RECORDINGS_DIR.glob("*.sr")):
            file_path = str(sr_file)
            if file_path in known_paths:
                continue

            measured_at = iso_from_timestamp(sr_file.stat().st_mtime)
            default_name = safe_name(sr_file.stem)
            conn.execute(
                """
                INSERT INTO recordings
                (name, sequence, notes, samplerate, channels, file_path, status, start_time, end_time, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    default_name,
                    "",
                    "Imported from recordings directory",
                    "unknown",
                    "unknown",
                    file_path,
                    "completed",
                    measured_at,
                    measured_at,
                    measured_at,
                ),
            )
            known_paths.add(file_path)
            imported += 1

        conn.commit()

    return imported


def insert_recording(
    name: str,
    sequence: str,
    notes: str,
    samplerate: str,
    channels: str,
    file_path: str,
) -> int:
    """Insert a new recording row and return its ID."""
    created = now_iso()
    with db_connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO recordings
            (name, sequence, notes, samplerate, channels, file_path, status, start_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'recording', ?, ?)
            """,
            (name, sequence, notes, samplerate, channels, file_path, created, created),
        )
        conn.commit()
        return int(cursor.lastrowid)


def finalize_recording(recording_id: int, status: str) -> None:
    """Mark recording as finished."""
    with db_connect() as conn:
        conn.execute(
            "UPDATE recordings SET status=?, end_time=? WHERE id=?",
            (status, now_iso(), recording_id),
        )
        conn.commit()


def add_annotation(recording_id: int, ts_ms: int, kind: str, payload: dict[str, Any]) -> int:
    """Persist one annotation event."""
    with db_connect() as conn:
        position_row = conn.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 AS next_position FROM annotations WHERE recording_id=?",
            (recording_id,),
        ).fetchone()
        next_position = int(position_row["next_position"] if position_row else 1)
        cursor = conn.execute(
            """
            INSERT INTO annotations (recording_id, ts_ms, kind, payload_json, created_at, position)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                recording_id,
                ts_ms,
                kind,
                json.dumps(payload, ensure_ascii=True),
                now_iso(),
                next_position,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def format_annotation_preview_entry(kind: str, payload: Any) -> str:
    """Render a readable annotation preview from the stored payload."""
    if kind == "button_press":
        if isinstance(payload, dict):
            name = payload.get("name") or payload.get("label")
            if name:
                return f"button_press: {name}"
            direction = payload.get("direction")
            if direction:
                return f"button_press: {direction}"
        return "button_press"

    if kind == "display_state":
        if isinstance(payload, dict):
            value = payload.get("value")
            cycle_number = payload.get("cycleNumber")
            symbols = payload.get("symbols")
            if isinstance(symbols, list):
                symbols_text = ",".join(str(item) for item in symbols)
            elif symbols:
                symbols_text = str(symbols)
            else:
                symbols_text = None
            parts = []
            if value:
                parts.append(f"value={value}")
            if cycle_number not in (None, ""):
                parts.append(f"cycle={cycle_number}")
            if symbols_text:
                parts.append(f"symbols={symbols_text}")
            if parts:
                return f"display_state: {'; '.join(parts)}"
            if payload.get("text"):
                return f"display_state: {payload['text']}"
        return "display_state"

    if isinstance(payload, dict) and payload:
        return f"{kind}: {json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
    return kind


def list_recordings(limit: int = 100) -> list[dict[str, Any]]:
    """Return recent recordings with annotation counts."""
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT r.*, COUNT(a.id) AS annotation_count
            FROM recordings r
            LEFT JOIN annotations a ON a.recording_id = r.id
            GROUP BY r.id
            ORDER BY r.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    items = [dict(row) for row in rows]
    for item in items:
        recording_id = int(item["id"])
        annotation_total = int(item.get("annotation_count") or 0)
        item["annotation_preview"] = fetch_annotation_preview(
            recording_id,
            limit=annotation_total if annotation_total > 0 else None,
        )
        item["annotations"] = fetch_annotations(recording_id)
    return items


def recording_download_stem(recording: dict[str, Any], fallback_id: int) -> str:
    """Return a stable base filename used for SR/JSON download pairs."""
    file_path_value = str(recording.get("file_path") or "").strip()
    if file_path_value:
        stem = Path(file_path_value).stem.strip()
        if stem:
            return safe_name(stem)

    name_value = str(recording.get("name") or "").strip()
    if name_value:
        return safe_name(name_value)

    return f"recording_{fallback_id}"


def export_payload(recording_id: int) -> dict[str, Any] | None:
    """Build one recording export payload or return None if missing."""
    recording = fetch_recording(recording_id)
    if recording is None:
        return None
    annotations = fetch_annotations(recording_id)
    return {"recording": recording, "annotations": annotations}


def build_recordings_archive() -> tuple[bytes, str, int]:
    """Create a ZIP archive containing all recordings as paired SR and JSON files."""
    rows = list_recordings(limit=100000)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archive_name = f"recordings_{timestamp}.zip"
    used_stems: set[str] = set()
    exported_count = 0

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            recording_id = int(row["id"])
            payload = export_payload(recording_id)
            if payload is None:
                continue

            recording = payload["recording"]
            stem = recording_download_stem(recording, recording_id)
            if stem in used_stems:
                stem = f"{stem}_{recording_id}"
            used_stems.add(stem)

            sr_path = Path(str(recording.get("file_path") or ""))
            if sr_path.exists() and sr_path.is_file():
                archive.write(sr_path, arcname=f"{stem}.sr")

            json_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            archive.writestr(f"{stem}.json", json_bytes)
            exported_count += 1

    return buffer.getvalue(), archive_name, exported_count


def fetch_recording(recording_id: int) -> dict[str, Any] | None:
    """Return one recording or None if unknown."""
    with db_connect() as conn:
        row = conn.execute(
            "SELECT * FROM recordings WHERE id=?",
            (recording_id,),
        ).fetchone()
    return dict(row) if row else None


def fetch_annotations(recording_id: int) -> list[dict[str, Any]]:
    """Return annotations for one recording."""
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT id, recording_id, ts_ms, kind, payload_json, created_at, position
            FROM annotations
            WHERE recording_id=?
            ORDER BY position ASC, id ASC
            """,
            (recording_id,),
        ).fetchall()
    records: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item.pop("ts_ms", None)
        item["payload"] = json.loads(item.pop("payload_json"))
        records.append(item)
    return records


def fetch_annotation_preview(recording_id: int, limit: int | None = 3) -> list[str]:
    """Return ordered annotation preview strings including payload details for one recording."""
    with db_connect() as conn:
        if limit is None:
            rows = conn.execute(
                """
                SELECT kind, payload_json
                FROM annotations
                WHERE recording_id=?
                ORDER BY position ASC, id ASC
                """,
                (recording_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT kind, payload_json
                FROM annotations
                WHERE recording_id=?
                ORDER BY position ASC, id ASC
                LIMIT ?
                """,
                (recording_id, limit),
            ).fetchall()
    preview: list[str] = []
    for row in rows:
        kind = str(row["kind"])
        payload = json.loads(row["payload_json"] or "{}")
        preview.append(format_annotation_preview_entry(kind, payload))
    return preview


def update_recording(
    recording_id: int,
    name: str | None,
    notes: str | None,
    sequence: str | None,
) -> dict[str, Any]:
    """Update mutable recording fields (rudimentary edit support)."""
    with STATE.lock:
        active = STATE.active
    if active and active.recording_id == recording_id:
        return {
            "ok": False,
            "status": 409,
            "error": "Cannot edit active recording",
        }

    current = fetch_recording(recording_id)
    if current is None:
        return {"ok": False, "status": 404, "error": "Recording not found"}

    new_name = name.strip() if isinstance(name, str) and name.strip() else current["name"]
    new_notes = notes if isinstance(notes, str) else current.get("notes", "")
    new_sequence = sequence if isinstance(sequence, str) else current.get("sequence", "")

    with db_connect() as conn:
        conn.execute(
            """
            UPDATE recordings
            SET name=?, notes=?, sequence=?
            WHERE id=?
            """,
            (new_name, new_notes, new_sequence, recording_id),
        )
        conn.commit()

    updated = fetch_recording(recording_id)
    return {"ok": True, "recording": updated}


def update_annotation(annotation_id: int, kind: str | None, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Update a single annotation after recording completion."""
    with STATE.lock:
        active = STATE.active
    if active is not None:
        with db_connect() as conn:
            row = conn.execute(
                "SELECT recording_id FROM annotations WHERE id=?",
                (annotation_id,),
            ).fetchone()
        if row and int(row["recording_id"]) == active.recording_id:
            return {"ok": False, "status": 409, "error": "Cannot edit annotations for active recording"}

    with db_connect() as conn:
        existing = conn.execute(
            "SELECT id, recording_id, kind, payload_json FROM annotations WHERE id=?",
            (annotation_id,),
        ).fetchone()
    if existing is None:
        return {"ok": False, "status": 404, "error": "Annotation not found"}

    new_kind = kind if isinstance(kind, str) and kind.strip() else existing["kind"]
    new_payload = payload if isinstance(payload, dict) else json.loads(existing["payload_json"] or "{}")

    with db_connect() as conn:
        conn.execute(
            "UPDATE annotations SET kind=?, payload_json=? WHERE id=?",
            (new_kind, json.dumps(new_payload, ensure_ascii=True), annotation_id),
        )
        conn.commit()

    return {"ok": True, "annotation": {"id": annotation_id, "kind": new_kind, "payload": new_payload}}


def reorder_annotations(recording_id: int, annotation_ids: list[int]) -> dict[str, Any]:
    """Persist a custom ordering for a recording's annotations."""
    with STATE.lock:
        active = STATE.active
    if active and active.recording_id == recording_id:
        return {"ok": False, "status": 409, "error": "Cannot reorder annotations for active recording"}

    with db_connect() as conn:
        existing_rows = conn.execute(
            "SELECT id FROM annotations WHERE recording_id=?",
            (recording_id,),
        ).fetchall()
    existing_ids = [int(row["id"]) for row in existing_rows]
    if not existing_ids:
        return {"ok": True, "recordingId": recording_id, "annotationIds": []}

    normalized_ids: list[int] = []
    seen: set[int] = set()
    for annotation_id in annotation_ids:
        annotation_id_int = int(annotation_id)
        if annotation_id_int in existing_ids and annotation_id_int not in seen:
            normalized_ids.append(annotation_id_int)
            seen.add(annotation_id_int)

    for existing_id in existing_ids:
        if existing_id not in seen:
            normalized_ids.append(existing_id)

    with db_connect() as conn:
        for position, annotation_id in enumerate(normalized_ids, start=1):
            conn.execute(
                "UPDATE annotations SET position=? WHERE id=? AND recording_id=?",
                (position, annotation_id, recording_id),
            )
        conn.commit()

    return {"ok": True, "recordingId": recording_id, "annotationIds": normalized_ids}


def delete_recording(recording_id: int) -> dict[str, Any]:
    """Delete one recording including related annotations and file if present."""
    with STATE.lock:
        active = STATE.active
    if active and active.recording_id == recording_id:
        return {"ok": False, "status": 409, "error": "Cannot delete active recording"}

    recording = fetch_recording(recording_id)
    if recording is None:
        return {"ok": False, "status": 404, "error": "Recording not found"}

    with db_connect() as conn:
        ann_deleted = conn.execute(
            "DELETE FROM annotations WHERE recording_id=?",
            (recording_id,),
        ).rowcount
        rec_deleted = conn.execute(
            "DELETE FROM recordings WHERE id=?",
            (recording_id,),
        ).rowcount
        conn.commit()

    file_deleted = False
    file_path = Path(recording["file_path"]) if recording.get("file_path") else None
    if file_path and file_path.exists():
        try:
            file_path.unlink()
            file_deleted = True
        except OSError:
            file_deleted = False

    return {
        "ok": True,
        "recordingId": recording_id,
        "deleted": bool(rec_deleted),
        "annotationsDeleted": int(ann_deleted or 0),
        "fileDeleted": file_deleted,
    }


def delete_all_recordings() -> dict[str, Any]:
    """Delete all recordings, related annotations, and capture files."""
    with STATE.lock:
        active = STATE.active
    if active is not None:
        return {
            "ok": False,
            "status": 409,
            "error": "Cannot delete all while a recording is active",
        }

    rows = list_recordings(limit=100000)
    total = len(rows)
    deleted = 0
    annotations_deleted = 0
    files_deleted = 0

    for row in rows:
        result = delete_recording(int(row["id"]))
        if result.get("ok"):
            deleted += 1
            annotations_deleted += int(result.get("annotationsDeleted", 0))
            if result.get("fileDeleted"):
                files_deleted += 1

    return {
        "ok": True,
        "deleted": deleted,
        "requested": total,
        "annotationsDeleted": annotations_deleted,
        "filesDeleted": files_deleted,
    }


def probe_signal_analyzer(driver: str) -> dict[str, Any]:
    """Check whether sigrok-cli can see a matching analyzer device."""

    command = ["sigrok-cli", "--scan", "-d", driver]
    try:
        completed = subprocess.run(  # pylint: disable=subprocess-run-check
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "ok": False,
            "command": command,
            "error": f"Could not test sigrok-cli: {error}",
        }

    output = "\n".join(
        part.strip() for part in [completed.stdout, completed.stderr] if part and part.strip()
    ).strip()
    lower_output = output.lower()
    no_device_markers = (
        "no devices found",
        "no supported devices found",
        "no device found",
    )
    firmware_failure_markers = (
        "firmware upload failed",
        "failed to open resource",
        "could not load firmware",
    )

    def build_failure_message() -> str:
        if any(marker in lower_output for marker in firmware_failure_markers):
            return (
                "Signal analyzer detected, but firmware upload failed. "
                "Check the probe firmware, USB connection, and device support for the selected driver."
            )
        if any(marker in lower_output for marker in no_device_markers):
            return f"No signal analyzer hardware detected for driver {driver}"
        return output or "No signal analyzer hardware detected"

    if (
        completed.returncode != 0
        or not output
        or any(marker in lower_output for marker in no_device_markers)
        or any(marker in lower_output for marker in firmware_failure_markers)
    ):
        message = build_failure_message()
        return {
            "ok": False,
            "command": command,
            "returncode": completed.returncode,
            "output": output,
            "error": message,
        }

    return {
        "ok": True,
        "command": command,
        "returncode": completed.returncode,
        "output": output,
    }


def trigger_system_shutdown() -> dict[str, Any]:
    """Schedule host shutdown and return immediate status."""

    run_prefix: list[str] = []
    if os.geteuid() != 0:
        run_prefix = ["sudo", "-n"]

    preferred_commands = [
        ["/usr/bin/systemctl", "poweroff"],
        ["/usr/sbin/shutdown", "-h", "now"],
        ["/usr/bin/shutdown", "-h", "now"],
    ]

    chosen_command: list[str] | None = None
    last_error: str | None = None

    for command in preferred_commands:
        if not os.path.exists(command[0]):
            continue

        try:
            if run_prefix:
                probe = subprocess.run(  # pylint: disable=subprocess-run-check
                    ["sudo", "-n", "-l", *command],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if probe.returncode == 0:
                    chosen_command = run_prefix + command
                    break

                stderr = (probe.stderr or "").strip()
                stdout = (probe.stdout or "").strip()
                last_error = stderr or stdout or f"exit code {probe.returncode}"
                if probe.returncode in (1, 126):
                    last_error = (
                        "Shutdown requires sudoers permission for the service user "
                        "(sudo -n systemctl poweroff / shutdown -h now)."
                    )
                continue

            chosen_command = command
            break

        except (OSError, subprocess.TimeoutExpired) as error:
            last_error = str(error)

    if chosen_command is None:
        return {
            "ok": False,
            "error": f"Shutdown command not available or not permitted: {last_error or 'unknown error'}",
        }

    def worker() -> None:
        # Give the HTTP response enough time to flush before poweroff is requested.
        time.sleep(0.3)
        try:
            subprocess.run(  # pylint: disable=subprocess-run-check
                chosen_command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

    threading.Thread(target=worker, daemon=True).start()

    return {
        "ok": True,
        "message": "Shutdown requested",
        "command": chosen_command,
    }


def start_simulated_job(job: ActiveJob, duration_s: int) -> None:
    """Run a simulated recording without hardware for local UI testing."""

    if job.stop_event is None:
        job.stop_event = threading.Event()

    def worker() -> None:
        end_time = time.monotonic() + max(1, duration_s)
        while time.monotonic() < end_time:
            if job.stop_event and job.stop_event.is_set():
                finalize_recording(job.recording_id, "completed")
                return
            time.sleep(0.1)
        Path(job.file_path).touch(exist_ok=True)
        finalize_recording(job.recording_id, "completed")
        with STATE.lock:
            if STATE.active and STATE.active.recording_id == job.recording_id:
                STATE.active = None

    job.worker = threading.Thread(target=worker, daemon=True)
    job.worker.start()


def stop_active_job() -> dict[str, Any]:
    """Stop active recording process and update database status."""
    with STATE.lock:
        active = STATE.active
        STATE.active = None

    if active is None:
        return {"stopped": False, "message": "No active recording"}

    status = "completed"
    if active.simulate:
        if active.stop_event:
            active.stop_event.set()
    else:
        process = active.process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        if process is not None and process.returncode not in (0, None, -15):
            status = "failed"
    finalize_recording(active.recording_id, status)

    elapsed_ms = int((time.monotonic() - active.started_monotonic) * 1000)
    return {
        "stopped": True,
        "recordingId": active.recording_id,
        "elapsedMs": elapsed_ms,
        "status": status,
        "filePath": active.file_path,
    }


class CaptureHandler(BaseHTTPRequestHandler):
    """HTTP API and static file serving."""

    server_version = "CaptureWebUI/0.1"

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _serve_static(self, rel_path: str) -> None:
        target = (STATIC_DIR / rel_path).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if target.is_dir():
            target = target / "index.html"
        content = target.read_bytes()
        content_type = "text/plain; charset=utf-8"
        if target.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif target.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_download_bytes(
        self,
        content: bytes,
        download_name: str,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Serve raw bytes as attachment download."""
        download_file_name = download_name.replace('"', "")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{download_file_name}"')
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_download_file(self, file_path: Path, download_name: str) -> None:
        """Serve a local file as attachment download."""
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content = file_path.read_bytes()
        self._serve_download_bytes(content, download_name)

    def do_GET(self) -> None:  # pylint: disable=invalid-name
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_static("index.html")
            return

        if path.startswith("/static/"):
            self._serve_static(path.removeprefix("/static/"))
            return

        if path == "/api/status":
            with STATE.lock:
                active = STATE.active
            if active is None:
                self._send_json({"active": False})
                return
            elapsed_ms = int((time.monotonic() - active.started_monotonic) * 1000)
            self._send_json(
                {
                    "active": True,
                    "recordingId": active.recording_id,
                    "filePath": active.file_path,
                    "startedAt": active.started_at_iso,
                    "elapsedMs": elapsed_ms,
                    "samplerate": active.samplerate,
                    "channels": active.channels,
                    "simulate": active.simulate,
                }
            )
            return

        if path == "/api/config":
            self._send_json(
                {
                    "defaults": {
                        "samplerate": "24MHz",
                        "channels": "D4,D5,D6,D7",
                        "driver": "fx2lafw",
                        "durationSeconds": 10,
                        "simulate": False,
                    },
                    "recordingsDir": str(RECORDINGS_DIR),
                }
            )
            return

        if path == "/api/recordings":
            query = parse_qs(parsed.query)
            limit = int(query.get("limit", ["100"])[0])
            self._send_json({"items": list_recordings(limit=limit)})
            return

        if path == "/api/recordings/download-all":
            archive_bytes, archive_name, exported_count = build_recordings_archive()
            if exported_count <= 0:
                self._send_json({"error": "No recordings available"}, status=404)
                return
            self._serve_download_bytes(archive_bytes, archive_name, "application/zip")
            return

        if path.startswith("/api/recordings/") and path.endswith("/export"):
            parts = path.strip("/").split("/")
            try:
                recording_id = int(parts[2])
            except (IndexError, ValueError):
                self._send_json({"error": "Invalid recording id"}, status=400)
                return

            payload = export_payload(recording_id)
            if payload is None:
                self._send_json({"error": "Recording not found"}, status=404)
                return

            query = parse_qs(parsed.query)
            download_mode = query.get("download", ["0"])[0].lower() in {"1", "true", "yes"}
            if download_mode:
                recording = payload["recording"]
                stem = recording_download_stem(recording, recording_id)
                content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                self._serve_download_bytes(content, f"{stem}.json", "application/json; charset=utf-8")
                return

            self._send_json(payload)
            return

        if path.startswith("/api/recordings/") and path.endswith("/file"):
            parts = path.strip("/").split("/")
            try:
                recording_id = int(parts[2])
            except (IndexError, ValueError):
                self._send_json({"error": "Invalid recording id"}, status=400)
                return

            recording = fetch_recording(recording_id)
            if recording is None:
                self._send_json({"error": "Recording not found"}, status=404)
                return

            file_path = Path(str(recording.get("file_path", "")))
            if not str(file_path.resolve()).startswith(str(RECORDINGS_DIR.resolve())):
                self._send_json({"error": "Invalid recording file path"}, status=400)
                return

            base_name = file_path.name if file_path.suffix == ".sr" else f"recording_{recording_id}.sr"
            self._serve_download_file(file_path, base_name)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # pylint: disable=invalid-name
        """Handle POST requests."""
        path = urlparse(self.path).path

        if path == "/api/recordings/start":
            payload = self._read_json_body()
            with STATE.lock:
                if STATE.active is not None:
                    self._send_json(
                        {"error": "Recording already active", "active": True},
                        status=409,
                    )
                    return

            name = safe_name(str(payload.get("name", "session")))
            sequence = str(payload.get("sequence", ""))
            notes = str(payload.get("notes", ""))
            samplerate = str(payload.get("samplerate", "24MHz"))
            channels = str(payload.get("channels", "D4,D5,D6,D7"))
            driver = str(payload.get("driver", "fx2lafw"))
            duration_seconds = int(payload.get("durationSeconds", 20))
            simulate = bool(payload.get("simulate", False))

            if not simulate:
                probe_result = probe_signal_analyzer(driver)
                if not probe_result.get("ok"):
                    self._send_json(
                        {
                            "error": probe_result.get("error", "Signal analyzer test failed"),
                            "command": probe_result.get("command", []),
                            "output": probe_result.get("output", ""),
                            "simulate": False,
                        },
                        status=503,
                    )
                    return

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_name = f"{timestamp}_{name}.sr"
            file_path = str(RECORDINGS_DIR / file_name)
            recording_id = insert_recording(name, sequence, notes, samplerate, channels, file_path)

            job = ActiveJob(
                recording_id=recording_id,
                file_path=file_path,
                started_at_iso=now_iso(),
                started_monotonic=time.monotonic(),
                samplerate=samplerate,
                channels=channels,
                simulate=simulate,
            )

            if simulate:
                job.stop_event = threading.Event()
                with STATE.lock:
                    STATE.active = job
                start_simulated_job(job, duration_s=duration_seconds)
                self._send_json(
                    {
                        "ok": True,
                        "simulate": True,
                        "recordingId": recording_id,
                        "filePath": file_path,
                        "message": "Simulation recording started",
                    }
                )
                return

            command = [
                "sigrok-cli",
                "-d",
                driver,
                "--config",
                f"samplerate={samplerate}",
                "--channels",
                channels,
                "--time",
                str(max(1, duration_seconds) * 1000),
                "-o",
                file_path,
            ]

            try:
                process = subprocess.Popen(  # pylint: disable=consider-using-with
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except OSError as error:
                finalize_recording(recording_id, "failed")
                self._send_json({"error": f"Could not start sigrok-cli: {error}"}, status=500)
                return

            job.process = process
            with STATE.lock:
                STATE.active = job

            self._send_json(
                {
                    "ok": True,
                    "simulate": False,
                    "recordingId": recording_id,
                    "filePath": file_path,
                    "command": command,
                }
            )
            return

        if path == "/api/analyzer/test":
            payload = self._read_json_body()
            driver = str(payload.get("driver", "fx2lafw"))
            result = probe_signal_analyzer(driver)
            status = 200 if result.get("ok") else 503
            self._send_json(result, status=status)
            return

        if path == "/api/system/shutdown":
            result = trigger_system_shutdown()
            status = 200 if result.get("ok") else 500
            self._send_json(result, status=status)
            return

        if path == "/api/recordings/stop":
            result = stop_active_job()
            self._send_json(result)
            return

        if path == "/api/recordings/delete":
            payload = self._read_json_body()
            recording_id = int(payload.get("recordingId", 0))
            if recording_id <= 0:
                self._send_json({"error": "recordingId is required"}, status=400)
                return

            result = delete_recording(recording_id)
            if not result.get("ok"):
                self._send_json(
                    {"error": result.get("error", "Delete failed")},
                    status=int(result.get("status", 500)),
                )
                return

            self._send_json(result)
            return

        if path == "/api/recordings/delete-all":
            result = delete_all_recordings()
            if not result.get("ok"):
                self._send_json(
                    {"error": result.get("error", "Delete all failed")},
                    status=int(result.get("status", 500)),
                )
                return
            self._send_json(result)
            return

        if path == "/api/recordings/update":
            payload = self._read_json_body()
            recording_id = int(payload.get("recordingId", 0))
            if recording_id <= 0:
                self._send_json({"error": "recordingId is required"}, status=400)
                return

            result = update_recording(
                recording_id=recording_id,
                name=payload.get("name") if isinstance(payload.get("name"), str) else None,
                notes=payload.get("notes") if isinstance(payload.get("notes"), str) else None,
                sequence=payload.get("sequence") if isinstance(payload.get("sequence"), str) else None,
            )
            if not result.get("ok"):
                self._send_json(
                    {"error": result.get("error", "Update failed")},
                    status=int(result.get("status", 500)),
                )
                return

            self._send_json(result)
            return

        if path == "/api/annotations":
            payload = self._read_json_body()
            recording_id = int(payload.get("recordingId", 0))
            kind = str(payload.get("kind", "event"))
            item_payload = payload.get("payload", {})

            if recording_id <= 0:
                self._send_json({"error": "recordingId is required"}, status=400)
                return
            if not isinstance(item_payload, dict):
                self._send_json({"error": "payload must be an object"}, status=400)
                return

            annotation_id = add_annotation(
                recording_id=recording_id,
                ts_ms=0,
                kind=kind,
                payload=item_payload,
            )
            self._send_json({"ok": True, "annotationId": annotation_id})
            return

        if path == "/api/annotations/update":
            payload = self._read_json_body()
            annotation_id = int(payload.get("annotationId", 0))
            kind = payload.get("kind")
            item_payload = payload.get("payload")

            if annotation_id <= 0:
                self._send_json({"error": "annotationId is required"}, status=400)
                return
            if item_payload is not None and not isinstance(item_payload, dict):
                self._send_json({"error": "payload must be an object"}, status=400)
                return

            result = update_annotation(annotation_id=annotation_id, kind=kind, payload=item_payload)
            if not result.get("ok"):
                self._send_json(
                    {"error": result.get("error", "Update failed")},
                    status=int(result.get("status", 500)),
                )
                return
            self._send_json(result)
            return

        if path == "/api/annotations/reorder":
            payload = self._read_json_body()
            recording_id = int(payload.get("recordingId", 0))
            annotation_ids = payload.get("annotationIds", [])

            if recording_id <= 0:
                self._send_json({"error": "recordingId is required"}, status=400)
                return
            if not isinstance(annotation_ids, list):
                self._send_json({"error": "annotationIds must be a list"}, status=400)
                return

            try:
                cleaned_ids = [int(annotation_id) for annotation_id in annotation_ids]
            except (TypeError, ValueError):
                self._send_json({"error": "annotationIds must contain integers"}, status=400)
                return

            result = reorder_annotations(recording_id=recording_id, annotation_ids=cleaned_ids)
            if not result.get("ok"):
                self._send_json(
                    {"error": result.get("error", "Reorder failed")},
                    status=int(result.get("status", 500)),
                )
                return
            self._send_json(result)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:  # pylint: disable=invalid-name
        """Handle DELETE requests."""
        path = urlparse(self.path).path

        if path.startswith("/api/recordings/"):
            parts = path.strip("/").split("/")
            try:
                recording_id = int(parts[2])
            except (IndexError, ValueError):
                self._send_json({"error": "Invalid recording id"}, status=400)
                return

            result = delete_recording(recording_id)
            if not result.get("ok"):
                self._send_json({"error": result.get("error", "Delete failed")}, status=int(result.get("status", 500)))
                return

            self._send_json(result)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format_str: str, *args: Any) -> None:
        """Print concise access logs."""
        message = format_str % args
        print(f"[{now_iso()}] {self.address_string()} {message}")


def parse_args() -> argparse.Namespace:
    """Build command-line parser."""
    parser = argparse.ArgumentParser(description="Sigrok recorder web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Listen host")
    parser.add_argument("--port", default=8765, type=int, help="Listen port")
    return parser.parse_args()


def main() -> None:
    """Server entry point."""
    args = parse_args()
    ensure_dirs()
    init_db()
    imported_count = sync_recordings_from_disk()
    server = ThreadingHTTPServer((args.host, args.port), CaptureHandler)
    print(f"Server running on http://{args.host}:{args.port}")
    if imported_count > 0:
        print(f"Imported {imported_count} existing .sr files from {RECORDINGS_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down")
    finally:
        stop_active_job()
        server.server_close()


if __name__ == "__main__":
    main()
