#!/bin/bash
: <<'COMMENT'
Usage:
- Default (no build, use `./datakeeper`):
  ./install.sh
  
- With build (use `./output/datakeeper`):
  ./install.sh --with-build=true

- Custom app name with build:
  ./install.sh --app-name=myapp --with-build=true
COMMENT

set -e

# Function to remove a directory if it exists
cleanup_dir() {
    local DIR="$1"
    if [ -d "$DIR" ]; then
        echo "Removing existing directory: $DIR"
        rm -rf "$DIR"
    fi
}

# (1) Parse input arguments
DEFAULT_APP_NAME="datakeeper"
APP_NAME="$DEFAULT_APP_NAME"
WITH_BUILD=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --app-name=*)
            APP_NAME="${arg#*=}"
            shift
            ;;
        --with-build=true)
            WITH_BUILD=true
            shift
            ;;
        --with-build=false)
            WITH_BUILD=false
            shift
            ;;
        *)
            echo "Unknown option: $arg"
            exit 1
            ;;
    esac
done

# Select binary path based on WITH_BUILD flag
if [ "$WITH_BUILD" = true ]; then
    BINARY_PATH="./output/${APP_NAME}"
else
    wget https://github.com/SUNET/datakeeper/releases/download/v0.1.7/datakeeper
    BINARY_PATH="./${APP_NAME}"
fi

# (2) Conditionally run Docker Compose build
if [ "$WITH_BUILD" = true ]; then
    echo "Building the binary using Docker Compose..."
    docker compose up --build
fi

# (3) Setup variables, config, and default folders
REPO_URL="https://github.com/SUNET/datakeeper.git"
CLONE_DIR="/tmp/repository" # Temporary directory for cloning
INSTALL_DIR="/usr/local/bin"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
LOG_FILE="/opt/${APP_NAME}/logs/runtime/${APP_NAME}.log"
CONFIG_FILE="config.ini"

echo "Installing ${APP_NAME} Service..."

cleanup_dir "/opt/${APP_NAME}"
mkdir -p /opt/${APP_NAME}/{database,plugins,logs/system,logs/runtime}

cleanup_dir "$CLONE_DIR"

echo "Cloning repository..."
git clone --depth=1 "$REPO_URL" "$CLONE_DIR"
echo "Copying files to destination..."

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

# (4) Installation

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
sudo chmod -R 775 /opt/${APP_NAME}/logs

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable "${APP_NAME}"
sudo systemctl start "${APP_NAME}"

echo "${APP_NAME} service installed and started successfully!"
