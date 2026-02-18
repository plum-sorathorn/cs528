import os
from google.cloud import pubsub_v1
from google.cloud import storage
import time

# AUTHENTICATION
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

# CONFIG
PROJECT_ID = "cs528-485615"
SUBSCRIPTION_ID = "hw3-topic-sub" 
BUCKET_NAME = "cs528-plum-hw2" 

def callback(message):
    decoded_msg = message.data.decode('utf-8')
    print(f"Received message: {decoded_msg}")
    
    # Write to bucket in 'forbidden_logs' directory
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    
    # Create unique filename using timestamp
    timestamp = str(int(time.time()))
    blob_name = f"forbidden_logs/log_{timestamp}.txt"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(decoded_msg)
    
    print(f"Logged to GCS: {blob_name}")
    message.ack()

def main():
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

    print(f"Listening for messages on {subscription_path}...\n")
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()

if __name__ == "__main__":
    main()