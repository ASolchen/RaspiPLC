#!/bin/bash
set -e

SERVICE_NAME="raspiplc-ui.service"
BASE_DIR="/home/engineer/RaspiPLC/ui-flask"
VENV_DIR="$BASE_DIR/venv"
SYSTEMD_DIR="/etc/systemd/system"

echo "[install] Installing RaspiPLC Flask UI with Socket.IO (pinned versions)"

# Ensure python + venv support
apt-get update
apt-get install -y python3 python3-venv

# Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "[install] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo "[install] Activating venv and installing dependencies..."

# Always upgrade pip inside venv
"$VENV_DIR/bin/pip" install --upgrade pip

# Remove incompatible versions if present
"$VENV_DIR/bin/pip" uninstall -y \
    flask-socketio \
    python-socketio \
    python-engineio || true

# Install KNOWN-GOOD compatible versions
"$VENV_DIR/bin/pip" install \
    flask \
    flask-socketio==5.3.6 \
    python-socketio==5.11.1 \
    python-engineio==4.9.1 \
    eventlet==0.35.2

# Install / update systemd service
cp "$SERVICE_NAME" "$SYSTEMD_DIR/"

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo "[install] Done"
echo "[install] Restart with: systemctl restart $SERVICE_NAME"
