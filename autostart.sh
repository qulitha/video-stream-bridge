#!/bin/bash
# Sets up VideoStreamBridge as a systemd service that starts on boot.
# Run once with: sudo bash scripts/autostart.sh

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_USER="${SUDO_USER:-pi}"
SERVICE_FILE="/etc/systemd/system/videostreambridge.service"

if [ "$EUID" -ne 0 ]; then
  echo "Run this with sudo."
  exit 1
fi

echo "Project dir: $PROJECT_DIR"
echo "Service will run as user: $SERVICE_USER"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=VideoStreamBridge - AI overlay HDMI pipeline
After=multi-user.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/main.py --config $PROJECT_DIR/config.yaml
Restart=on-failure
RestartSec=2
# kmssink needs access to the DRM device
SupplementaryGroups=video render

[Install]
WantedBy=multi-user.target
EOF

echo "Wrote $SERVICE_FILE"

systemctl daemon-reload
systemctl enable videostreambridge.service

echo "Done. Service is enabled and will start on next boot."
echo "To start it now:   sudo systemctl start videostreambridge"
echo "To check status:   sudo systemctl status videostreambridge"
echo "To see logs:       journalctl -u videostreambridge -f"
