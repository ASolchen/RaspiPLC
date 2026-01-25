#!/bin/bash
set -e

UI_SERVICE="raspiplc-ui.service"
QDB_SERVICE="questdb.service"

BASE_DIR="/home/engineer/RaspiPLC/ui-flask"
VENV_DIR="$BASE_DIR/venv"
SYSTEMD_DIR="/etc/systemd/system"

QUESTDB_DIR="/opt/questdb"
QUESTDB_VERSION="7.4.4"

echo "[install] Installing RaspiPLC UI + QuestDB"

# ------------------------------------------------------------------
# System dependencies
# ------------------------------------------------------------------
echo "[install] Installing system packages..."
apt-get update
apt-get install -y \
    python3 \
    python3-venv \
    curl \
    wget \
    tar \
    ca-certificates

# ------------------------------------------------------------------
# Python virtual environment
# ------------------------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
    echo "[install] Creating Python venv..."
    python3 -m venv "$VENV_DIR"
fi

echo "[install] Upgrading pip..."
"$VENV_DIR/bin/pip" install --upgrade pip

# ------------------------------------------------------------------
# Python dependencies (UI + historian)
# ------------------------------------------------------------------
echo "[install] Installing Python dependencies..."

"$VENV_DIR/bin/pip" uninstall -y \
    flask-socketio \
    python-socketio \
    python-engineio \
    eventlet || true

echo "[install] Installing Python dependencies from requirements.txt..."
"$VENV_DIR/bin/pip" install -r "$BASE_DIR/requirements.txt"

# ------------------------------------------------------------------
# QuestDB binaries (NO service logic here)
# ------------------------------------------------------------------
if [ ! -d "$QUESTDB_DIR" ]; then
    echo "[install] Installing QuestDB ${QUESTDB_VERSION}..."
    mkdir -p "$QUESTDB_DIR"
    cd /tmp

    wget -q https://github.com/questdb/questdb/releases/download/${QUESTDB_VERSION}/questdb-${QUESTDB_VERSION}-no-jre-bin.tar.gz
    tar -xzf questdb-${QUESTDB_VERSION}-no-jre-bin.tar.gz
    cp -r questdb-${QUESTDB_VERSION}-no-jre-bin/* "$QUESTDB_DIR"

    rm -rf questdb-${QUESTDB_VERSION}-no-jre-bin*
else
    echo "[install] QuestDB already installed"
fi

# ------------------------------------------------------------------
# Systemd services
# ------------------------------------------------------------------
echo "[install] Installing systemd service files..."

cp "$BASE_DIR/$UI_SERVICE" "$SYSTEMD_DIR/"
cp "$BASE_DIR/$QDB_SERVICE" "$SYSTEMD_DIR/"

systemctl daemon-reexec
systemctl daemon-reload

systemctl enable "$UI_SERVICE"
systemctl enable "$QDB_SERVICE"

echo
echo "[install] Installation complete"
echo "[install] Start services with:"
echo "  systemctl start questdb"
echo "  systemctl start raspiplc-ui"
