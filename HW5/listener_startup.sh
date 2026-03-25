#!/bin/bash
if [ -f /var/log/startup_already_done ]; then
    exit 0
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3-pip

# 1. Install dependencies with the bypass flag
pip3 install --break-system-packages google-cloud-pubsub

export no_proxy=metadata.google.internal,169.254.169.254
export NO_PROXY=metadata.google.internal,169.254.169.254

mkdir -p /home/plum

# 2. Write the listener code directly to the file
cat <<EOF > /home/plum/listener.py
import os
from google.cloud import pubsub_v1

project_id = "cs528-485615"
subscription_id = "hw5-topic-sub"

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

def callback(message):
    log_entry = f"ALERT: {message.data.decode('utf-8')}\n"
    # Ensure the script can write to this file
    try:
        with open("/var/log/listener.log", "a") as f:
            f.write(log_entry)
        message.ack()
    except Exception as e:
        print(f"Error writing to log: {e}")

print(f"Listening for messages on {subscription_path}...")
streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

try:
    streaming_pull_future.result()
except Exception as e:
    streaming_pull_future.cancel()
EOF

# 3. Fix permissions for the log files
touch /var/log/listener.log
touch /var/log/listener_service.log
chmod 666 /var/log/listener.log
chmod 666 /var/log/listener_service.log

# 4. Start the listener in the background
python3 /home/plum/listener.py > /var/log/listener_service.log 2>&1 &

touch /var/log/startup_already_done