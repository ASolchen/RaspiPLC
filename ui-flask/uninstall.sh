#!/bin/bash
set -e

SERVICE_NAME="raspiplc-ui.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "[uninstall] Stopping service..."

systemctl stop "$SERVICE_NAME" || true
systemctl disable "$SERVICE_NAME" || true
rm -f "$SYSTEMD_DIR/$SERVICE_NAME"

systemctl daemon-reexec
systemctl daemon-reload

echo "[uninstall] Service removed"
echo "[uninstall] venv and source files preserved"

