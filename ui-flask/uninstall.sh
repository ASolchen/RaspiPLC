#!/bin/bash
set -e

SERVICE_NAME="raspiplc-ui.service"
INSTALL_DIR="/opt/raspiplc/ui-flask"
SYSTEMD_DIR="/etc/systemd/system"

echo "[uninstall] Stopping service if running..."

if systemctl is-active --quiet "$SERVICE_NAME"; then
    systemctl stop "$SERVICE_NAME"
fi

if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    systemctl disable "$SERVICE_NAME"
    rm -f "$SYSTEMD_DIR/$SERVICE_NAME"
fi

# Reload systemd
systemctl daemon-reexec
systemctl daemon-reload

# Remove installed files
rm -rf "$INSTALL_DIR"

# Remove Python dependencies
echo "[uninstall] Removing Python dependencies..."
pip3 uninstall -y flask-socketio eventlet

echo "[uninstall] ui-flask removed"
echo "[uninstall] NOTE: Shared memory regions remain untouched"

