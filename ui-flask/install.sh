#!/bin/bash
set -e

SERVICE_NAME="raspiplc-ui.service"
BASE_DIR="/home/engineer/RaspiPLC/ui-flask"
VENV_DIR="$BASE_DIR/venv"
SYSTEMD_DIR="/etc/systemd/system"

echo "[install] Installing ui-flask (home-based)..."

# Ensure python + venv
apt-get update
apt-get install -y python3 python3-venv

# Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "[install] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Install deps
echo "[install] Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install flask flask-socketio eventlet

# Install systemd service
cp "$SERVICE_NAME" "$SYSTEMD_DIR/"

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo "[install] Done"
