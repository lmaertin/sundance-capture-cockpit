#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  sudo scripts/install_capture_webui_service.sh <service-user> [project-dir] [port] [host]

Examples:
  sudo scripts/install_capture_webui_service.sh pi /opt/sundance-capture-cockpit 8765 0.0.0.0
  sudo scripts/install_capture_webui_service.sh pi
EOF
}

SERVICE_USER="${1:-}"
PROJECT_DIR="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PORT="${3:-8765}"
HOST="${4:-0.0.0.0}"
SERVICE_NAME="capture-webui"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
RECORDINGS_DIR="${CAPTURE_RECORDINGS_DIR:-${PROJECT_DIR}/capture_webui/recordings}"
SUDOERS_PATH="/etc/sudoers.d/${SERVICE_NAME}-shutdown"

if [[ -z "$SERVICE_USER" ]]; then
  usage
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run with sudo." >&2
  exit 1
fi

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "Project directory not found: $PROJECT_DIR" >&2
  exit 1
fi

if [[ ! -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  echo "Missing virtual environment at $PROJECT_DIR/.venv. Run the bootstrap script or the one-click installer first." >&2
  exit 1
fi

mkdir -p "$PROJECT_DIR/capture_webui/data"
mkdir -p "$RECORDINGS_DIR"
chown "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR/capture_webui/data" "$RECORDINGS_DIR"

cat > "$SUDOERS_PATH" <<EOF
# Allow ${SERVICE_USER} to request system poweroff from Capture WebUI.
${SERVICE_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff
${SERVICE_USER} ALL=(root) NOPASSWD: /usr/sbin/shutdown -h now
${SERVICE_USER} ALL=(root) NOPASSWD: /usr/bin/shutdown -h now
EOF
chmod 440 "$SUDOERS_PATH"
if ! visudo -c -f "$SUDOERS_PATH" >/dev/null; then
  echo "Invalid sudoers rule generated at $SUDOERS_PATH" >&2
  rm -f "$SUDOERS_PATH"
  exit 1
fi

cat > "$UNIT_PATH" <<EOF
[Unit]
Description=Capture WebUI
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=CAPTURE_RECORDINGS_DIR=${RECORDINGS_DIR}
ExecStart=${PROJECT_DIR}/.venv/bin/python ${PROJECT_DIR}/capture_webui/server.py --host ${HOST} --port ${PORT}
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "Installed and started ${SERVICE_NAME}."
echo "Check status with: sudo systemctl status ${SERVICE_NAME}"