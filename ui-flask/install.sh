#!/usr/bin/env bash
set -e

echo "=== RaspiPLC Install ==="

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# ------------------------------------------------------------
# Python virtual environment
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
# QuestDB (ARM / Raspberry Pi only)
# ------------------------------------------------------------

install_questdb() {
    echo "Installing QuestDB (Java 21 compatible)..."

    # --------------------------------------------------------
    # Java (Debian trixie = Java 21)
    # --------------------------------------------------------
    if ! command -v java >/dev/null 2>&1; then
        echo "Installing Java runtime..."
        sudo apt update
        sudo apt install -y default-jre
    fi

    JAVA_BIN="$(readlink -f /usr/bin/java)"
    JAVA_HOME="$(dirname "$(dirname "$JAVA_BIN")")"

    echo "Detected JAVA_HOME=$JAVA_HOME"

    # --------------------------------------------------------
    # QuestDB install
    # --------------------------------------------------------
    QUESTDB_VERSION="7.4.4"
    QUESTDB_DIR="/opt/questdb"

    echo "Installing QuestDB $QUESTDB_VERSION..."

    sudo rm -rf "$QUESTDB_DIR"
    sudo mkdir -p "$QUESTDB_DIR"
    sudo chown "$USER":"$USER" "$QUESTDB_DIR"

    wget -q https://github.com/questdb/questdb/releases/download/${QUESTDB_VERSION}/questdb-${QUESTDB_VERSION}-no-jre-bin.tar.gz
    tar xzf questdb-${QUESTDB_VERSION}-no-jre-bin.tar.gz -C "$QUESTDB_DIR" --strip-components=1
    rm questdb-${QUESTDB_VERSION}-no-jre-bin.tar.gz

    # --------------------------------------------------------
    # Runtime directories
    # --------------------------------------------------------
    mkdir -p "$QUESTDB_DIR/db" "$QUESTDB_DIR/log"

    # --------------------------------------------------------
    # env.sh (QuestDB REQUIRES THIS)
    # --------------------------------------------------------
    cat > "$QUESTDB_DIR/env.sh" <<EOF
#!/usr/bin/env bash
export JAVA_HOME=$JAVA_HOME
export JAVA_OPTS="-Xms128m -Xmx512m"
EOF

    chmod +x "$QUESTDB_DIR/env.sh"

    sudo chown -R "$USER":"$USER" "$QUESTDB_DIR"

    # --------------------------------------------------------
    # systemd service (legacy launcher model)
    # --------------------------------------------------------
    sudo tee /etc/systemd/system/questdb.service >/dev/null <<EOF
[Unit]
Description=QuestDB
After=network.target

[Service]
Type=forking
User=$USER
WorkingDirectory=/opt/questdb
EnvironmentFile=/opt/questdb/env.sh
ExecStart=/opt/questdb/questdb.sh start
ExecStop=/opt/questdb/questdb.sh stop
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable questdb
    sudo systemctl restart questdb
}

# ------------------------------------------------------------
# Architecture gate
# ------------------------------------------------------------

ARCH="$(uname -m)"

if [[ "$ARCH" == arm* || "$ARCH" == aarch64 ]]; then
    install_questdb
else
    echo "Skipping QuestDB install (non-ARM system)"
fi

echo "=== Install complete ==="
