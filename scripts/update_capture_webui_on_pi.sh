#!/usr/bin/env bash
set -euo pipefail

DEFAULT_BRANCH="main"
DEFAULT_INSTALL_DIR="/opt/sundance-capture-cockpit"
DEFAULT_SERVICE_USER="capture-webui"
DEFAULT_PORT="8765"
DEFAULT_HOST="0.0.0.0"
DEFAULT_REPO_URL="https://github.com/lmaertin/sundance-capture-cockpit.git"

REPO_URL="${DEFAULT_REPO_URL}"
BRANCH="${DEFAULT_BRANCH}"
INSTALL_DIR="${DEFAULT_INSTALL_DIR}"
SERVICE_USER="${DEFAULT_SERVICE_USER}"
PORT="${DEFAULT_PORT}"
HOST="${DEFAULT_HOST}"
RECORDINGS_DIR=""

usage() {
  cat <<'EOF'
Usage:
  curl -fsSL https://raw.githubusercontent.com/lmaertin/sundance-capture-cockpit/main/scripts/update_capture_webui_on_pi.sh | sudo bash -s -- [options]

Options:
  --repo <url>           Git repository to update from
  --branch <name>        Git branch to update (default: main)
  --install-dir <path>   Installation directory (default: /opt/sundance-capture-cockpit)
  --service-user <name>  System user used for the service (default: capture-webui)
  --port <port>          Web UI port (default: 8765)
  --host <host>          Web UI bind host (default: 0.0.0.0)
  --recordings-dir <dir> Custom recordings directory
  -h, --help             Show this help message

Example:
  curl -fsSL https://raw.githubusercontent.com/lmaertin/sundance-capture-cockpit/main/scripts/update_capture_webui_on_pi.sh | sudo bash -s -- --install-dir /opt/sundance-capture-cockpit
EOF
}

log() {
  echo "[update] $*"
}

warn() {
  echo "[warning] $*" >&2
}

die() {
  echo "[error] $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || die "Missing value for --repo"
      REPO_URL="$2"
      shift 2
      ;;
    --branch)
      [[ $# -ge 2 ]] || die "Missing value for --branch"
      BRANCH="$2"
      shift 2
      ;;
    --install-dir)
      [[ $# -ge 2 ]] || die "Missing value for --install-dir"
      INSTALL_DIR="$2"
      shift 2
      ;;
    --service-user)
      [[ $# -ge 2 ]] || die "Missing value for --service-user"
      SERVICE_USER="$2"
      shift 2
      ;;
    --port)
      [[ $# -ge 2 ]] || die "Missing value for --port"
      PORT="$2"
      shift 2
      ;;
    --host)
      [[ $# -ge 2 ]] || die "Missing value for --host"
      HOST="$2"
      shift 2
      ;;
    --recordings-dir)
      [[ $# -ge 2 ]] || die "Missing value for --recordings-dir"
      RECORDINGS_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  die "This updater must be run with sudo."
fi

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${VERSION_CODENAME:-}" != "trixie" ]]; then
    warn "This updater is validated for Raspberry Pi OS Trixie. Current codename: ${VERSION_CODENAME:-unknown}."
  fi
else
  warn "Could not read /etc/os-release. Proceeding without Raspberry Pi OS detection."
fi

export DEBIAN_FRONTEND=noninteractive

log "Updating package index and installing system dependencies."
apt-get update
apt-get install -y ca-certificates curl git python3 python3-venv python3-pip sigrok-cli

git config --global --add safe.directory "$INSTALL_DIR"

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  die "Install directory is not a Git repository: $INSTALL_DIR"
fi

log "Updating repository in $INSTALL_DIR."
if [[ -n "$(git -C "$INSTALL_DIR" status --porcelain)" ]]; then
  die "Existing repository has local changes. Please clean it before running the updater again."
fi
git -C "$INSTALL_DIR" fetch --prune origin
git -C "$INSTALL_DIR" checkout "$BRANCH"
git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"

log "Refreshing the Python virtual environment."
if [[ ! -d "$INSTALL_DIR/.venv" ]]; then
  python3 -m venv "$INSTALL_DIR/.venv"
fi

"$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip

if [[ -f "$INSTALL_DIR/requirements.txt" ]]; then
  log "Installing Python dependencies from requirements.txt."
  "$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade -r "$INSTALL_DIR/requirements.txt"
else
  log "No requirements.txt found. The application currently uses only the Python standard library."
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

if [[ -n "$RECORDINGS_DIR" ]]; then
  export CAPTURE_RECORDINGS_DIR="$RECORDINGS_DIR"
fi

log "Reinstalling and restarting the systemd service."
"$INSTALL_DIR/scripts/install_capture_webui_service.sh" "$SERVICE_USER" "$INSTALL_DIR" "$PORT" "$HOST"

log "Update complete."
log "Open the web UI at http://${HOST}:${PORT}"
log "Service status: sudo systemctl status capture-webui"