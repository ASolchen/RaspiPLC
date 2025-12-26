#!/bin/bash
set -e

SERVICE_NAME="raspiplc-ui.service"
INSTALL_DIR="/opt/raspiplc/ui-flask"
SYSTEMD_DIR="/etc/systemd/system"

echo "[install] Installing ui-flask..."

# Ensure python + pip exist
echo "[install] Ensuring python3 and pip are installed..."
apt-get update
apt-get install -y python3 python3-pip

# Install required Python libraries
echo "[install] Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install flask flask-socketio eventlet

# Install application files
mkdir -p "$INSTALL_DIR"

cp app.py "$INSTALL_DIR/"
cp -r templates static "$INSTALL_DIR/"

# Install systemd service
cp "$SERVICE_NAME" "$SYSTEMD_DIR/"

# Reload systemd and enable service
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo "[install] ui-flask installed"
echo "[install] Start with: systemctl start $SERVICE_NAME"
