#!/bin/bash
set -e

SERVICE_NAME="raspiplc-shm-init.service"
INSTALL_DIR="/opt/raspiplc/shm-core"
SYSTEMD_DIR="/etc/systemd/system"

echo "[install] Installing shm-core..."

# Ensure install directory exists
mkdir -p "$INSTALL_DIR"

# Copy source files
cp shm_layout.py shm_init.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/shm_init.py"

# Copy systemd unit
cp "$SERVICE_NAME" "$SYSTEMD_DIR/"

# Reload systemd and enable service
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo "[install] shm-core installed successfully"
echo "[install] Shared memory will be initialized at next boot"
echo "[install] To run immediately: systemctl start $SERVICE_NAME"
