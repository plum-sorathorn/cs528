#!/bin/bash
if [ -f /var/log/startup_already_done ]; then
    echo "Startup script already ran once. Skipping."
    exit 0
fi

apt-get update
apt-get install -y python3-pip python3-venv

mkdir -p /app
python3 -m venv /app/venv
/app/venv/bin/pip install google-cloud-pubsub

PROJECT_ID=$(curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/project/project-id")
echo "export GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" >> /etc/profile.d/gcp_env.sh
source /etc/profile.d/gcp_env.sh

curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/attributes/listener-script" > /app/listener.py

# Unbuffered execution
nohup /app/venv/bin/python -u /app/listener.py > /app/listener.log 2>&1 &

touch /var/log/startup_already_done