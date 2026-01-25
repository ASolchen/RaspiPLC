#!/usr/bin/env bash
set -e

echo "=== RaspiPLC install.sh ==="

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------

QUESTDB_VERSION="7.4.0"
INSTALL_USER="${SUDO_USER:-$USER}"
INSTALL_HOME=$(eval echo "~$INSTALL_USER")
SDKMAN_DIR="$INSTALL_HOME/.sdkman"
JAVA_VERSION="17.0.17-tem"
QUESTDB_DIR="/opt/questdb"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

log() {
  echo -e "\n==> $1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 1
  }
}

# ------------------------------------------------------------
# Preconditions
# ------------------------------------------------------------

require_cmd curl
require_cmd tar
require_cmd systemctl

log "Installing system packages"
sudo apt update
sudo apt install -y curl unzip tar ca-certificates

# ------------------------------------------------------------
# SDKMAN + Java 17
# ------------------------------------------------------------

if [ ! -d "$SDKMAN_DIR" ]; then
  log "Installing SDKMAN"
  sudo -u "$INSTALL_USER" bash -c \
    "curl -s https://get.sdkman.io | bash"
else
  log "SDKMAN already installed"
fi

log "Loading SDKMAN"
# shellcheck disable=SC1090
source "$SDKMAN_DIR/bin/sdkman-init.sh"

if ! sdk list java | grep -q "$JAVA_VERSION"; then
  echo "ERROR: Java version $JAVA_VERSION not found via SDKMAN"
  exit 1
fi

if ! sdk current java | grep -q "$JAVA_VERSION"; then
  log "Installing Java $JAVA_VERSION"
  sudo -u "$INSTALL_USER" bash -c \
    "source $SDKMAN_DIR/bin/sdkman-init.sh && sdk install java $JAVA_VERSION"
else
  log "Java $JAVA_VERSION already active"
fi

JAVA_HOME="$SDKMAN_DIR/candidates/java/$JAVA_VERSION"

log "Using JAVA_HOME=$JAVA_HOME"

# ------------------------------------------------------------
# QuestDB install
# ------------------------------------------------------------

log "Installing QuestDB $QUESTDB_VERSION"

sudo mkdir -p "$QUESTDB_DIR"
sudo chown "$INSTALL_USER:$INSTALL_USER" "$QUESTDB_DIR"

cd "$QUESTDB_DIR"

if [ ! -f questdb.jar ]; then
  curl -L \
    "https://github.com/questdb/questdb/releases/download/${QUESTDB_VERSION}/questdb-${QUESTDB_VERSION}-no-jre-bin.tar.gz" \
    -o questdb.tar.gz

  tar xzf questdb.tar.gz --strip-components=1
  rm questdb.tar.gz
else
  log "QuestDB already present"
fi

mkdir -p db log

sudo chown -R "$INSTALL_USER:$INSTALL_USER" "$QUESTDB_DIR"

# ------------------------------------------------------------
# systemd service (NO questdb.sh)
# ------------------------------------------------------------

log "Installing systemd service for QuestDB"

sudo tee /etc/systemd/system/questdb.service >/dev/null <<EOF
[Unit]
Description=QuestDB
After=network.target

[Service]
Type=simple
User=$INSTALL_USER
WorkingDirectory=$QUESTDB_DIR
Environment=JAVA_HOME=$JAVA_HOME
ExecStart=$JAVA_HOME/bin/java -Xms128m -Xmx512m -jar $QUESTDB_DIR/questdb.jar -d $QUESTDB_DIR/db
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable questdb
sudo systemctl restart questdb

# ------------------------------------------------------------
# Final verification
# ------------------------------------------------------------

log "QuestDB status"
systemctl status questdb --no-pager || true

log "Install complete"
echo "QuestDB UI should be available at: http://localhost:9000"
