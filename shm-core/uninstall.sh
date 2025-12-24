#!/bin/bash
set -e

SERVICE_NAME="raspiplc-shm-init.service"
INSTALL_DIR="/opt/raspiplc/shm-core"
SYSTEMD_DIR="/etc/systemd/system"

echo "[uninstall] Removing shm-core..."

# Stop and disable service if present
if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    systemctl stop "$SERVICE_NAME" || true
    systemctl disable "$SERVICE_NAME"
    rm -f "$SYSTEMD_DIR/$SERVICE_NAME"
fi

# Reload systemd
systemctl daemon-reexec
systemctl daemon-reload

# Remove installed files
rm -rf "$INSTALL_DIR"

echo "[uninstall] shm-core removed"
echo "[uninstall] NOTE: Shared memory regions in /dev/shm are NOT deleted"
