#!/usr/bin/env bash
set -e

echo "=== RaspiPLC Install ==="

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# ------------------------------------------------------------
# Python venv + deps
# ------------------------------------------------------------

if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$PROJECT_ROOT/venv"
fi

source "$PROJECT_ROOT/venv/bin/activate"

echo "Installing Python requirements..."
pip install --upgrade pip
pip install -r "$PROJECT_ROOT/requirements.txt"

deactivate

# ------------------------------------------------------------
# QuestDB install (ARM only)
# ------------------------------------------------------------

install_questdb() {
    echo "Installing QuestDB..."

    # --------------------------------------------------------
    # Java runtime (QuestDB REQUIRES JAVA_HOME)
    # --------------------------------------------------------
    if ! command -v java >/dev/null 2>&1; then
        echo "Installing Java runtime..."
        sudo apt update
        sudo apt install -y default-jre
    fi

    # Detect JAVA_HOME dynamically
    JAVA_BIN="$(readlink -f /usr/bin/java)"
    JAVA_HOME="$(dirname "$(dirname "$JAVA_BIN")")"

    echo "Detected JAVA_HOME=$JAVA_HOME"

    # --------------------------------------------------------
    # QuestDB files
    # --------------------------------------------------------
    QUESTDB_VERSION="7.3.1"
    QUESTDB_DIR="/opt/questdb"

    if [ ! -d "$QUESTDB_DIR" ]; then
        echo "Downloading QuestDB..."
        sudo mkdir -p "$QUESTDB_DIR"
        sudo chown "$USER":"$USER" "$QUESTDB_DIR"

        wget -q https://github.com/questdb/questdb/releases/download/${QUESTDB_VERSION}/questdb-${QUESTDB_VERSION}-no-jre-bin.tar.gz
        tar xzf questdb-${QUESTDB_VERSION}-no-jre-bin.tar.gz -C "$QUESTDB_DIR" --strip-components=1
        rm questdb-${QUESTDB_VERSION}-no-jre-bin.tar.gz
    else
        echo "QuestDB already installed"
    fi

    # --------------------------------------------------------
    # Write env.sh (CRITICAL for QuestDB)
    # --------------------------------------------------------
    cat > "$QUESTDB_DIR/env.sh" <<EOF
#!/usr/bin/env bash
export JAVA_HOME=$JAVA_HOME
export JAVA_OPTS="-Xms128m -Xmx512m"
EOF

    chmod +x "$QUESTDB_DIR/env.sh"

    # --------------------------------------------------------
    # systemd service (foreground mode)
    # --------------------------------------------------------
    if [ ! -f /etc/systemd/system/questdb.service ]; then
        echo "Installing QuestDB systemd service..."

        sudo tee /etc/systemd/system/questdb.service >/dev/null <<EOF
[Unit]
Description=QuestDB
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/questdb
ExecStart=/usr/bin/env bash -c 'source /opt/questdb/env.sh && exec /opt/questdb/questdb.sh start -f'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    else
        echo "QuestDB systemd service already exists"
    fi

    sudo systemctl daemon-reload
    sudo systemctl enable questdb
    sudo systemctl restart questdb
}

# ------------------------------------------------------------
# Architecture gate (only install QuestDB on Pi / ARM)
# ------------------------------------------------------------

ARCH="$(uname -m)"

if [[ "$ARCH" == arm* || "$ARCH" == aarch64 ]]; then
    install_questdb
else
    echo "Skipping QuestDB install (non-ARM system)"
fi

echo "=== Install complete ==="
