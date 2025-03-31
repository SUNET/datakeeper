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

# (1) Setup variables, config, and default folders

# Default application name
DEFAULT_APP_NAME="datakeeper"
APP_NAME="${1:-$DEFAULT_APP_NAME}"

# Define variables
INSTALL_DIR="/usr/local/bin"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
LOG_FILE="/opt/${APP_NAME}/logs/runtime/${APP_NAME}.log"
CONFIG_FILE="/opt/${APP_NAME}/config.ini"
CLONE_DIR="/tmp/repository" # Temporary directory for cloning

# (2) Uninstallation

echo "Uninstalling ${APP_NAME} Service..."

# Stop the service
echo "Stopping systemd service..."
sudo systemctl stop "${APP_NAME}" || true

# Disable the systemd service
echo "Disabling systemd service..."
sudo systemctl disable "${APP_NAME}" || true

# Remove the systemd service file
echo "Removing systemd service file..."
cleanup_dir "${SERVICE_FILE}"

# Remove the application binary
echo "Removing application binary..."
cleanup_dir "${INSTALL_DIR}/${APP_NAME}"

# Remove application files and directories
echo "Removing application files and directories..."
cleanup_dir "/opt/${APP_NAME}"

# Remove the temporary repository clone
cleanup_dir "$CLONE_DIR"

# Remove the logs directory (optional)
echo "Removing log files..."
cleanup_dir "/opt/${APP_NAME}/logs"

# Optionally, remove the configuration file
echo "Removing configuration file..."
cleanup_dir "$CONFIG_FILE"

# Reload systemd daemon to reflect the changes
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "${APP_NAME} has been uninstalled successfully."
