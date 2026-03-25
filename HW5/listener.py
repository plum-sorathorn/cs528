import os
from google.cloud import pubsub_v1

project_id = "cs528-485615"
subscription_id = "hw5-topic-sub"

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

def callback(message):
    log_entry = f"ALERT: {message.data.decode('utf-8')}\n"
    with open("/var/log/listener.log", "a") as f:
        f.write(log_entry)
    message.ack()

print(f"Listening for messages on {subscription_path}...")
streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

try:
    streaming_pull_future.result()
except Exception as e:
    streaming_pull_future.cancel()