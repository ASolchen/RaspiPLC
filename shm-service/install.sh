#!/bin/bash
set -e

SERVICE_NAME="shm-service.service"
INSTALL_ROOT="/opt/raspiplc/shm-service"
ETC_ROOT="/etc/raspiplc"

echo "[install] Installing shm-service..."

# Create directories
mkdir -p "$INSTALL_ROOT"
mkdir -p "$ETC_ROOT"

# Copy service files
cp shm_service.py "$INSTALL_ROOT/"
cp shmctl.py "$INSTALL_ROOT/"
cp tags.example.json "$ETC_ROOT/tags.json"

# Make executables executable
chmod +x "$INSTALL_ROOT/shm_service.py"
chmod +x "$INSTALL_ROOT/shmctl.py"

# Install systemd unit
cp "$SERVICE_NAME" /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable service (do not start yet)
systemctl enable "$SERVICE_NAME"

echo "[install] shm-service installed."
echo "[install] Edit $ETC_ROOT/tags.json before starting."

