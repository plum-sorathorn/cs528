import os
import time
from google.cloud import pubsub_v1

os.environ["GCE_METADATA_MTLS_MODE"] = "none"
if "http_proxy" in os.environ:
    del os.environ["http_proxy"]
if "https_proxy" in os.environ:
    del os.environ["https_proxy"]

project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'cs528-485615')
SUBSCRIPTION_ID = "hw4-topic-sub"

def callback(message):
    print(f"BANNED COUNTRY ALERT: {message.data.decode('utf-8')}")
    message.ack()

def listen_for_messages():
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, SUBSCRIPTION_ID)
    
    print(f"Second App: Listening for banned country logs on {subscription_path}...\n")
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    
    with subscriber:
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            streaming_pull_future.cancel()

if __name__ == "__main__":
    listen_for_messages()
