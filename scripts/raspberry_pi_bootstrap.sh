#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "Project directory not found: $PROJECT_DIR" >&2
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run with sudo on Raspberry Pi OS Trixie." >&2
  exit 1
fi

apt update
apt install -y python3 python3-venv python3-pip sigrok-cli sigrok-firmware-fx2lafw git

if [[ ! -d "$PROJECT_DIR/.venv" ]]; then
  python3 -m venv "$PROJECT_DIR/.venv"
fi

"$PROJECT_DIR/.venv/bin/python" -m pip install --upgrade pip

echo "Bootstrap complete."
echo "Next step: run scripts/install_capture_webui_service.sh with the service user and project directory."