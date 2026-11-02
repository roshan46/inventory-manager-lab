#!/bin/bash
set -euo pipefail
dnf install -y docker
systemctl enable --now docker
systemctl enable --now amazon-ssm-agent
install -d -m 700 /opt/inventory
# AL2023 includes AWS CLI. No database credentials are stored in user-data.
test -f /opt/inventory/app-secret || openssl rand -hex 32 > /opt/inventory/app-secret
chmod 600 /opt/inventory/app-secret
touch /opt/inventory/host-ready
