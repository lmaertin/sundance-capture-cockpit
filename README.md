# Capture WebUI

Local web UI for recording panel traffic with sigrok and annotating interactions.

This project is a non-profit, community-oriented tool created to help bring information from older Sundance Series 880 spas from before 2016 into home automation and monitoring systems. It is not affiliated with Sundance or Jacuzzi, and it exists because those older spas do not offer any kind of smart interface or supported modern control platform.

<img width="1253" height="565" alt="image" src="https://github.com/user-attachments/assets/bbe40179-e06b-4485-8bd3-bd5fd179a34b" />
<img width="1227" height="814" alt="image" src="https://github.com/user-attachments/assets/1f86127b-3372-4b44-9030-d9ff6860617b" />

## Features

- Start and stop recordings from the browser
- Save raw captures as `.sr`
- Download raw `.sr` files per recording
- Export recording metadata and annotations as JSON
- Annotate panel button events and display states
- View recordings with timestamp, duration, and annotation preview
- Driver dropdown with `fx2lafw` as default and optional custom driver
- Channels as checkboxes (`D1`..`D8`), default `D4,D5,D6,D7`
- Sigrok command log panel showing the exact command sent to sigrok-cli

## Project Layout

- Server: `capture_webui/server.py`
- Static UI: `capture_webui/static/`
- Recordings: `capture_webui/recordings/`
- SQLite database: `capture_webui/data/annotations.db`

## Cross-Platform Setup (macOS, Linux, Windows)

This section helps you test locally before moving to Raspberry Pi.

### Prerequisites

- Python 3.10+
- sigrok-cli (required for real hardware captures)
- Git

### macOS Setup

1. Install dependencies:

```bash
brew update
brew install python sigrok-cli git
```

1. Create virtual environment and start server:

```bash
cd <PROJECT_DIR>
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python capture_webui/server.py --host 127.0.0.1 --port 8765
```

1. Open:

- <http://127.0.0.1:8765>

### Linux Setup

For Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip sigrok-cli git
cd <PROJECT_DIR>
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python capture_webui/server.py --host 127.0.0.1 --port 8765
```

For Fedora:

```bash
sudo dnf install -y python3 python3-pip sigrok-cli git
cd <PROJECT_DIR>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python capture_webui/server.py --host 127.0.0.1 --port 8765
```

### Windows Setup (PowerShell)

1. Install dependencies (example with winget):

```powershell
winget install Python.Python.3.12
winget install Git.Git
```

Install sigrok-cli using your preferred method (for example Scoop/Chocolatey/manual package).

1. Create virtual environment and run:

```powershell
cd <PROJECT_DIR>
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python capture_webui\server.py --host 127.0.0.1 --port 8765
```

1. Open:

- <http://127.0.0.1:8765>

### Local Test Flow (all platforms)

1. Keep Simulate without hardware enabled for first tests.
1. Start recording, click panel buttons, stop recording.
1. Verify new row appears in Recordings.
1. Test Download .sr and Export JSON.
1. Verify the Sigrok Command Log shows the command line for each run.

## Recording Modes

1. Simulation mode

- Keep `Simulate without hardware` enabled
- Useful for validating UI flows and annotation handling

1. Real hardware mode

- Disable simulation
- Set `driver`, `samplerate`, and `channels` to your logic analyzer setup
- Driver UI defaults to `fx2lafw` and supports custom driver IDs
- Capture command used by the backend:

```bash
sigrok-cli -d <driver> --config samplerate=<samplerate> --channels <channels> --time <duration_ms> -o <output.sr>
```

Notes:

- `duration_ms` is computed from the UI duration in seconds.
- Annotation exports intentionally omit event timestamps (no `ts_ms` field).

## How To Download `.sr`

Use the `Download .sr` button in the `Recordings` table.

Direct API route:

- `GET /api/recordings/<id>/file`

Example:

```bash
curl -L "http://127.0.0.1:8765/api/recordings/12/file" -o recording_12.sr
```

## API Endpoints

- `GET /api/config`
- `GET /api/status`
- `GET /api/recordings?limit=60`
- `GET /api/recordings/<id>/export`
- `GET /api/recordings/<id>/file`
- `POST /api/recordings/start`
- `POST /api/recordings/stop`
- `POST /api/recordings/update`
- `POST /api/recordings/delete`
- `POST /api/recordings/delete-all`
- `POST /api/annotations`

## Raspberry Pi Setup

These steps target Raspberry Pi OS (Bookworm/Bullseye).

### 1. Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip sigrok-cli git
```

If your analyzer needs udev rules, also install:

```bash
sudo apt install -y libsigrok libsigrokdecode
```

### 2. Clone and prepare environment

```bash
git clone <your-repo-url> <PROJECT_DIR>
cd <PROJECT_DIR>
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
```

This project currently uses the Python standard library for the web server, so no extra Python package install is required for `capture_webui/server.py`.

### 3. Test interactive startup

```bash
cd <PROJECT_DIR>
.venv/bin/python capture_webui/server.py --host 0.0.0.0 --port 8765
```

Open from another machine in your LAN:

- `http://<raspberry-pi-ip>:8765`

### 4. Create a systemd service

Create a systemd service file named `capture-webui.service` in your systemd unit directory:

```ini
[Unit]
Description=Capture WebUI
After=network.target

[Service]
Type=simple
User=<SERVICE_USER>
WorkingDirectory=<PROJECT_DIR>
ExecStart=<PROJECT_DIR>/.venv/bin/python <PROJECT_DIR>/capture_webui/server.py --host 0.0.0.0 --port 8765
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable capture-webui
sudo systemctl start capture-webui
sudo systemctl status capture-webui
```

### 5. Optional: custom recordings directory

You can set a dedicated storage path with environment variable `CAPTURE_RECORDINGS_DIR` (the older `SUNDANCE_RECORDINGS_DIR` name is still accepted for compatibility).

For systemd, add under `[Service]`:

```ini
Environment=CAPTURE_RECORDINGS_DIR=/mnt/data/capture-recordings
```

Then reload and restart the service.

## Final Raspberry Pi Deployment (Decentralized)

This setup keeps everything local in your network without cloud dependency.

### Deployment goals

- Pi runs capture service 24/7
- Browser clients on LAN access UI directly
- Data stays local on Pi storage
- Service auto-recovers after reboot/power loss

### Recommended production checklist

1. Network identity

- Assign a static DHCP lease to the Pi in your router.
- Optional mDNS hostname usage: `http://<pi-hostname>.local:8765`

1. Service hardening

- Keep systemd Restart=always enabled.
- Add a non-root service user if you do not use the default pi user.
- Limit write paths to project folders and recordings mount.

1. Storage strategy

- Move recordings to dedicated storage with SUNDANCE_RECORDINGS_DIR.
- Use a larger SSD/USB disk for long capture sessions.
- Add cleanup policy for old .sr files (age- or size-based).

1. Backup strategy

- Back up capture_webui/data/annotations.db daily.
- Optionally sync selected .sr files to NAS on schedule.

1. Observability and maintenance

- Check service logs with journalctl -u capture-webui.
- Keep OS updated: sudo apt update && sudo apt upgrade.
- Reboot test after updates to verify auto-start behavior.

### Optional remote access pattern

If you want access from outside the LAN, place a VPN in front (for example Tailscale or WireGuard) rather than exposing port 8765 directly to the internet.

## Operational Notes

- Keep regular backups of `capture_webui/data/annotations.db`.
- Implement retention for old `.sr` files if disk space is limited.
- Restart the service after backend code updates.
