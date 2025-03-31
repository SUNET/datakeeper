#!/bin/bash

set -e

# Function to remove a directory if it exists
cleanup_dir() {
    local DIR="$1"
    if [ -d "$DIR" ]; then
        echo "Removing existing directory: $DIR"
        rm -rf "$DIR"
    fi
}

# (1) Setup variables, config and default folders

# Default application name
DEFAULT_APP_NAME="datakeeper"
APP_NAME="${1:-$DEFAULT_APP_NAME}"

# Define variables
REPO_URL="https://github.com/SUNET/datakeeper.git"
CLONE_DIR="/tmp/repository" # Temporary directory for cloning
INSTALL_DIR="/usr/local/bin"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
LOG_FILE="/opt/${APP_NAME}/logs/runtime/${APP_NAME}.log"
BINARY_PATH="./${APP_NAME}" # Assuming the binary is in the current directory
CONFIG_FILE="config.ini"

echo "Installing ${APP_NAME} Service..."

if [ -d "$CLONE_DIR" ]; then
    echo "Removing existing repository clone..."
    rm -rf "$CLONE_DIR"
fi

# Remove if exist
cleanup_dir "/opt/${APP_NAME}"
# Create directory
mkdir -p /opt/${APP_NAME}/{database,plugins,logs/system,logs/runtime}

# Remove existing clone directory if it exists
cleanup_dir "$CLONE_DIR"

echo "Cloning repository..."
git clone --depth=1 "$REPO_URL" "$CLONE_DIR"
echo "Copying file to destination..."

sudo cp "$CLONE_DIR/datakeeper/database/init.sql" "/opt/${APP_NAME}/database/"
sudo cp "$CLONE_DIR/datakeeper/config/policy.yaml" "/opt/${APP_NAME}/"
sudo cp -r "$CLONE_DIR/datakeeper/policy_system/plugins/"* "/opt/${APP_NAME}/plugins/"

# Create config.ini if it doesn't exist
cat <<EOF >"/opt/${APP_NAME}/$CONFIG_FILE"
[DATAKEEPER]
LOG_DIRECTORY = /opt/${APP_NAME}/logs/system
PLUGIN_DIR = /opt/${APP_NAME}/plugins
POLICY_PATH = /opt/${APP_NAME}/policy.yaml
DB_PATH = /opt/${APP_NAME}/database/database.sqlite
INIT_FILE_PATH = /opt/${APP_NAME}/database/init.sql
EOF

# (2) Installation

# Ensure the binary exists
if [[ ! -f "$BINARY_PATH" ]]; then
    echo "Error: Binary file '${BINARY_PATH}' not found!" >&2
    exit 1
fi

# Ensure it is executable
chmod +x "$BINARY_PATH"

# Copy binary
sudo cp "$BINARY_PATH" "${INSTALL_DIR}/${APP_NAME}"

# Create systemd service
cat <<EOF | sudo tee "${SERVICE_FILE}"
[Unit]
Description=${APP_NAME} Service Daemon
After=network.target

[Service]
# Then start the service as nobody:nogroup
ExecStart=${INSTALL_DIR}/${APP_NAME} schedule --config /opt/${APP_NAME}/config.ini
Restart=always
#User=${APP_NAME}
#Group=${APP_NAME}
StandardOutput=append:${LOG_FILE}
StandardError=append:${LOG_FILE}

# Set working directory
WorkingDirectory=/opt/${APP_NAME}

# Ensure the service has proper permissions
UMask=0002
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/${APP_NAME}/logs

[Install]
WantedBy=multi-user.target
EOF

# Cleanup
echo "Cleaning up..."
cleanup_dir "$CLONE_DIR"

# Change permissions
# sudo useradd -r -s /bin/false ${APP_NAME}
# sudo chown -R ${APP_NAME}:${APP_NAME} /opt/${APP_NAME}/logs
sudo chmod -R 775 /opt/${APP_NAME}/logs

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
# sudo systemctl stop "${APP_NAME}"
sudo systemctl enable "${APP_NAME}"
sudo systemctl start "${APP_NAME}"

echo "${APP_NAME} service installed and started successfully!"
