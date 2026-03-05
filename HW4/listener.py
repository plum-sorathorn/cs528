import os
import time
from google.cloud import pubsub_v1

project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'cs528-485615')
SUBSCRIPTION_ID = "hw4-topic-sub"

def callback(message):
    print(f"Received message: {message.data.decode('utf-8')}")
    message.ack()

def listen_for_messages():
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, SUBSCRIPTION_ID)
    
    print(f"Listening for messages on {subscription_path}...\n")
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    
    with subscriber:
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            streaming_pull_future.cancel()

if __name__ == "__main__":
    listen_for_messages()