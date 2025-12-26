#!/bin/bash
set -e

SERVICE_NAME="raspiplc-ui.service"
BASE_DIR="/home/engineer/RaspiPLC/ui-flask"
SYSTEMD_DIR="/etc/systemd/system"

echo "[uninstall] Stopping RaspiPLC UI service..."

systemctl stop "$SERVICE_NAME" || true
systemctl disable "$SERVICE_NAME" || true
rm -f "$SYSTEMD_DIR/$SERVICE_NAME"

systemctl daemon-reexec
systemctl daemon-reload

echo "[uninstall] Service removed"
echo "[uninstall] Source code and venv preserved at:"
echo "            $BASE_DIR"
