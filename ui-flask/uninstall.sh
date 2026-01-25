#!/usr/bin/env bash
set -e

echo "=== RaspiPLC Uninstall ==="

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# ------------------------------------------------------------
# Remove Python venv
# ------------------------------------------------------------

if [ -d "$PROJECT_ROOT/venv" ]; then
    echo "Removing Python virtual environment..."
    rm -rf "$PROJECT_ROOT/venv"
fi

# ------------------------------------------------------------
# QuestDB uninstall (if present)
# ------------------------------------------------------------

if [ -f /etc/systemd/system/questdb.service ]; then
    echo "Stopping and removing QuestDB service..."

    sudo systemctl stop questdb || true
    sudo systemctl disable questdb || true
    sudo rm -f /etc/systemd/system/questdb.service
    sudo systemctl daemon-reload
fi

if [ -d /opt/questdb ]; then
    echo "Removing QuestDB files..."
    sudo rm -rf /opt/questdb
fi

echo "=== Uninstall complete ==="
