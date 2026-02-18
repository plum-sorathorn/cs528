import functions_framework
from google.cloud import storage
from google.cloud import pubsub_v1
from google.cloud import logging
import json

# CONFIGURATION
BUCKET_NAME = "cs528-plum-hw2" 
PROJECT_ID = "cs528-485615"
TOPIC_ID = "hw3-topic"

# Setup Clients
storage_client = storage.Client()
publisher = pubsub_v1.PublisherClient()
logging_client = logging.Client()
logger = logging_client.logger("hw3-structured-log")

FORBIDDEN_COUNTRIES = [
    "North Korea", "Iran", "Cuba", "Myanmar", "Iraq", 
    "Libya", "Sudan", "Zimbabwe", "Syria"
]

@functions_framework.http
def handle_request(request):
    # Check for 501 Not Implemented (Method check)
    if request.method != 'GET':
        msg = f"Method {request.method} not allowed"
        print(msg) 
        logger.log_text(msg, severity="ERROR") 
        return (msg, 501)

    # Check X-country header
    country = request.headers.get('X-country')
    if country in FORBIDDEN_COUNTRIES:
        error_msg = f"Forbidden request from {country}"
        
        # Publish to Pub/Sub
        topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
        data = error_msg.encode("utf-8")
        future = publisher.publish(topic_path, data)
        future.result() 
        
        return ("Permission Denied", 400)

    # Handle File Retrieval
    filename = request.args.get('filename')

    if not filename:
        # If no query param, clean up the path
        # request.path might look like "/hw3-function/0.html"
        path = request.path.lstrip('/')
        
        # Remove the function name prefix if it exists
        if path.startswith("hw3-function"):
            path = path.replace("hw3-function", "", 1).lstrip('/')
            
        filename = path

    if not filename:
        return ("Filename not specified", 400)

    if not filename.startswith("data/"):
        blob_name = f"data/{filename}"
    else:
        blob_name = filename

    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)

    if not blob.exists():
        msg = f"File {blob_name} not found"
        print(msg)
        logger.log_text(msg, severity="ERROR")
        return (msg, 404)

    # Return file content
    content = blob.download_as_text()
    return (content, 200)