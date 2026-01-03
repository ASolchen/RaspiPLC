#!/bin/bash
set -e

SERVICE_NAME="shm-service.service"
INSTALL_ROOT="/opt/raspiplc/shm-service"

echo "[uninstall] Removing shm-service..."

# Stop service if running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    systemctl stop "$SERVICE_NAME"
fi

# Disable service
if systemctl is-enabled --quiet "$SERVICE_NAME"; then
    systemctl disable "$SERVICE_NAME"
fi

# Remove systemd unit
rm -f "/etc/systemd/system/$SERVICE_NAME"

# Reload systemd
systemctl daemon-reload

# Remove installed files
rm -rf "$INSTALL_ROOT"

echo "[uninstall] shm-service removed."
echo "[uninstall] Shared memory and config files were NOT removed."
