# Capture WebUI

Local web UI for recording panel traffic with sigrok and annotating interactions.

This project is a non-profit, community-oriented tool created to help bring information from older Sundance Series 880 spas from before 2016 into home automation and monitoring systems. It is not affiliated with Sundance or Jacuzzi, and it exists because those older spas do not offer any kind of smart interface or supported modern control platform.

> Prototype note: the decoder and analysis workflow in the decoder folder are still incomplete and experimental. They are intended for exploratory, local analysis only and should not be treated as finished or authoritative reverse-engineering documentation.

<img width="1253" height="565" alt="image" src="https://github.com/user-attachments/assets/bbe40179-e06b-4485-8bd3-bd5fd179a34b" />
<img width="1249" height="807" alt="image" src="https://github.com/user-attachments/assets/456e1db3-0186-4a66-bdee-e6af12c4e7c2" />
<img width="1228" height="360" alt="image" src="https://github.com/user-attachments/assets/42b0d955-3a2f-49f1-9daa-8cd0d6880b9c" />

## Features

- Start and stop recordings from the browser
- Save raw captures as `.sr`
- Download raw `.sr` files per recording
- Export recording metadata and annotations as JSON
- Annotate panel button events and display states
- Reorder annotations later with drag-and-drop in the recording details view
- View recordings with timestamp, duration, and annotation preview
- Driver dropdown with `fx2lafw` as default and optional custom driver
- Channels as checkboxes (`D1`..`D8`), default `D4,D5,D6,D7`
- Sigrok command log panel showing the exact command sent to sigrok-cli

## Project Layout

- Server: `capture_webui/server.py`
- Static UI: `capture_webui/static/`
- Recordings: `capture_webui/recordings/`
- SQLite database: `capture_webui/data/annotations.db`
- Decoder prototype: `decoder/README.md`

## Cross-Platform Setup (macOS, Linux, Windows)

## Raspberry Pi Setup

Use Raspberry Pi OS Lite and install the project with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/lmaertin/sundance-capture-cockpit/main/scripts/install_capture_webui_on_pi.sh | sudo bash -s --
```

The one-click installer:

- installs the required packages
- installs `sigrok-cli` for capture support
- clones or updates the repository
- creates the Python virtual environment
- installs and enables the systemd service
- starts the service automatically

To update an existing Pi install later, use the matching updater:

```bash
curl -fsSL https://raw.githubusercontent.com/lmaertin/sundance-capture-cockpit/main/scripts/update_capture_webui_on_pi.sh | sudo bash -s --
```

After installation, the web UI runs as a headless service on the Pi and is available on your LAN.

## Manual Install

### Prerequisites for Manual Install

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

1. Enable Simulate without hardware for first tests (default is disabled).
1. Start recording, click panel buttons, stop recording.
1. Verify new row appears in Recordings.
1. Test Download .sr, Export JSON, and Download all.
1. Verify the Sigrok Command Log shows the command line for each run.

## Recording Modes

1. Simulation mode

- Enable `Simulate without hardware`
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

The JSON export uses the same base name as the `.sr` file. Example:

- `20260727_233022_panel-session.sr`
- `20260727_233022_panel-session.json`

Direct API route:

- `GET /api/recordings/<id>/file`

Example:

```bash
curl -L "http://127.0.0.1:8765/api/recordings/12/file" -o recording_12.sr
```

## How To Download All Recordings

Use the `Download all` button in the `Recordings` section.

Direct API route:

- `GET /api/recordings/download-all`

Example:

```bash
curl -L "http://127.0.0.1:8765/api/recordings/download-all" -o recordings.zip
```

The ZIP archive contains one `.sr` and one `.json` file per recording with matching base names.

## Migration Guide For Old Recordings (Default Paths)

Use this when older `.sr` files are not yet visible in the Web UI.

```bash
# 1) Ensure the default recordings directory exists
sudo mkdir -p /opt/sundance-capture-cockpit/capture_webui/recordings
sudo chown -R capture-webui:capture-webui /opt/sundance-capture-cockpit/capture_webui/recordings

# 2) If old files are in the former default folder, copy them over
# (this runs only when the source directory exists)
if [ -d /opt/sundance-capture-cockpit/recordings ]; then
  sudo rsync -avh --ignore-existing /opt/sundance-capture-cockpit/recordings/*.sr /opt/sundance-capture-cockpit/capture_webui/recordings/
fi

# 3) Ensure ownership for service access
sudo chown -R capture-webui:capture-webui /opt/sundance-capture-cockpit/capture_webui/recordings

# 4) Restart the service to trigger automatic import into SQLite
sudo systemctl restart capture-webui
sudo systemctl status capture-webui --no-pager

# 5) Verify imported recordings via API
curl -s http://sundance-decoder:8765/api/recordings
```

Notes:

- Existing `.sr` files are not deleted by this migration.
- Import is triggered on server startup and adds only recordings that are missing in the database.
- The service path is configured through `CAPTURE_RECORDINGS_DIR`; when unset, it defaults to `/opt/sundance-capture-cockpit/capture_webui/recordings`.

## API Endpoints

- `GET /api/config`
- `GET /api/status`
- `GET /api/recordings?limit=60`
- `GET /api/recordings/<id>/export`
- `GET /api/recordings/<id>/export?download=1`
- `GET /api/recordings/<id>/file`
- `GET /api/recordings/download-all`
- `POST /api/recordings/start`
- `POST /api/recordings/stop`
- `POST /api/recordings/update`
- `POST /api/recordings/delete`
- `POST /api/recordings/delete-all`
- `POST /api/annotations`
- `POST /api/annotations/reorder`

## How-To: From Pool to Protocol Decoder

This project is meant to be used as a practical workflow from the hardware side to the first decoder ideas. The idea is not to jump straight to a finished protocol specification, but to build one step by step from real captures.

### 1. Connect the pool and prepare the capture setup

1. Connect the logic analyzer or capture device to the panel bus and power lines.
2. Start the local web UI and open the interface in the browser.
3. Choose a realistic samplerate and channel set. For first experiments, keep the setup simple and capture only the lines that look relevant.
4. If hardware access is not available yet, use simulation mode to test the full workflow.

The web UI is the entry point for this process. It stores each recording together with metadata and annotations so that the raw capture stays connected to the human observations.

### 2. Capture a real interaction

1. Start a recording in the UI.
2. Operate the spa panel once, for example by pressing one button or changing a display state.
3. Stop the recording.
4. Save the `.sr` file and inspect it in the recordings list.

The important goal in this step is to create a clean, reproducible capture. A good capture usually has:

- one clear action
- one stable starting state
- a short and understandable duration

### 3. Annotate what happened

After the capture is saved, add annotations that describe the visible behavior:

- which button was pressed
- whether the display changed
- what state the panel appeared to enter
- whether the result was expected or surprising

These annotations are not proof of the protocol, but they are extremely useful for comparing the observed behavior with the decoded signal. They turn a raw waveform into a small traceable experiment.

### 4. Export and inspect the raw data

From the recording view, export the recording bundle and inspect the resulting files:

- the raw Sigrok `.sr` capture
- the annotation JSON export

The first analysis should focus on the shape of the signal rather than on immediate decoding success. The question is: what changed, where, and how often?

### 5. Use the decoder prototype on the capture

The decoder folder contains an experimental prototype that can load a `.sr` file and compare it with the annotation JSON. This is the bridge between raw capture and early protocol reasoning.

If you want to start from example data first, look at the files in the `examples/` directory. These provide a simple reference for how a capture and its annotation bundle can look before you work with your own pool recordings.

A typical flow is:

```bash
python3 decoder/decode_sr.py measurements/your_capture.sr
```

If you have a matching annotation file, provide it explicitly:

```bash
python3 decoder/decode_sr.py measurements/your_capture.sr --annotation-json measurements/your_capture.json
```

The output helps you see:

- which bus layout the prototype inferred
- which decode variants look plausible
- whether the observed display states and button presses line up with the decoded bursts

### 6. Compare hypotheses with real observations

This is the central step toward a real protocol decoder.

For each capture, compare:

- the raw burst structure
- the inferred bit patterns
- the human annotation of the panel action
- the visible display change

If one candidate produces a stable, repeatable pattern across several captures, that candidate becomes more interesting. If the pattern changes between runs, the decoder assumptions need to be revised.

### 7. Build the protocol decoder incrementally

The workflow should stay iterative:

1. Collect a small set of well-annotated captures.
2. Compare them against each other.
3. Identify recurring word patterns or field layouts.
4. Turn the most promising pattern into a more specific decoder rule.
5. Re-test the rule on new captures.

This is how the project moves from a rough signal explorer to something closer to a real protocol decoder: one observed interaction at a time.

### 8. What counts as progress

Real progress looks like this:

- several captures show the same burst structure
- a field appears in the same position across captures
- button presses and display changes correlate with known words or states
- a decoder rule can explain a new capture without extra guesswork

That is the point where the prototype becomes valuable as a foundation for a more serious decoder.

### 9. Keep the workflow honest

The decoder and analysis code in this repository are still experimental. They are useful for local exploration and documentation of panel behavior, but they are not yet a complete or authoritative protocol implementation.

The right attitude is:

- collect data carefully
- annotate deliberately
- keep hypotheses explicit
- improve the decoder only when the evidence supports it

That is the path from a captured pool interaction to a real protocol understanding.

## Operational Notes

- Keep regular backups of `capture_webui/data/annotations.db`.
- Implement retention for old `.sr` files if disk space is limited.
- Restart the service after backend code updates.
