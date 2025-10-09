#!/bin/bash

SERVICE_NAME="Uvicorn Server - Bledot"
SERVICE_FILENAME="bledot-server.service"
INSTALL_DIR="$(dirname $(pwd))"
UVICORN_EXEC="$INSTALL_DIR/bledot-env/bin/uvicorn"

# Ensure the script is run with root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use 'sudo')."
    exit 1
fi

# Ensure the Uvicorn executable exists
if [ ! -f "$UVICORN_EXEC" ]; then
    echo "Error: Uvicorn executable not found at '$UVICORN_EXEC'."
    echo "Please ensure the virtual environment ('bledot-env') is created and Uvicorn is installed (pip install uvicorn)."
    exit 1
fi


SERVICE_FILE="/etc/systemd/system/$SERVICE_FILENAME"

echo "Creating systemd service file: $SERVICE_FILE"
cat << EOF > "$SERVICE_FILE"
    [Unit]
    Description=Uvicorn server - Bledot
    After=network.target

    [Service]
    Type=simple
    User=root
    Group=root
    WorkingDirectory=$INSTALL_DIR
    ExecStart=$INSTALL_DIR/bledot-env/bin/uvicorn main:app
    ExecReload=/bin/kill -s SIGHUP $MAINPID
    ExecStop=/bin/kill -s SIGINT $MAINPID
    TimeoutStartSec=30
    Restart=on-failure
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
EOF

echo "Service file created successfully."

# Reload the systemd manager configuration to load the new service file
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable the service (sets it to start automatically on boot)
echo "Enabling service to start on boot..."
sudo systemctl enable "$SERVICE_FILENAME"

echo "$SERVICE_NAME installed successfully."

