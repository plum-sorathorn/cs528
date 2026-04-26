import os
from flask import Flask, request, Response
from google.cloud import storage, pubsub_v1, logging as cloud_logging

# CRITICAL FIX for GKE mTLS issue with metadata server
os.environ["GCE_METADATA_MTLS_MODE"] = "none"
if "http_proxy" in os.environ:
    del os.environ["http_proxy"]
if "https_proxy" in os.environ:
    del os.environ["https_proxy"]

app = Flask(__name__)

project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'cs528-485615')
storage_client = storage.Client(project=project_id)
pubsub_publisher = pubsub_v1.PublisherClient()
logging_client = cloud_logging.Client(project=project_id)
logger = logging_client.logger("hw9-web-server-log")

BUCKET_NAME = "cs528-plum-hw2"
TOPIC_ID = "hw4-topic"
BANNED_COUNTRIES = ["North Korea", "Iran", "Cuba", "Myanmar", "Iraq", "Libya", "Sudan", "Zimbabwe", "Syria"]

@app.route('/<path:filepath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH'])
@app.route('/', defaults={'filepath': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH'])
def handle_request(filepath):
    # 3. 501 Not Implemented for non-GET methods
    if request.method != 'GET':
        log_message = f"501 Not Implemented: Method {request.method} used for {request.path}"
        logger.log_text(log_message, severity="ERROR")
        return Response(log_message, status=501)

    # 7. Banned country detection
    country_header = request.headers.get('X-country', '')
    if country_header in BANNED_COUNTRIES:
        log_message = f"Forbidden request from banned country: {country_header}"
        logger.log_text(log_message, severity="CRITICAL")
        
        # Route to second app via Pub/Sub
        topic_path = pubsub_publisher.topic_path(project_id, TOPIC_ID)
        future = pubsub_publisher.publish(topic_path, log_message.encode("utf-8"))
        print(f"Published message to {TOPIC_ID}: {log_message}")
        future.result() # Wait for publish to succeed
        
        return Response("Permission Denied: Banned Country", status=403)

    # Determine filename
    filename = request.args.get('filename') or filepath
    if not filename:
        return Response("Bad Request: Missing filename", status=400)

    # 2. 404 Not Found for non-existent files
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"data/{filename}")

    if not blob.exists():
        log_message = f"404 Not Found: File data/{filename} does not exist"
        logger.log_text(log_message, severity="ERROR")
        return Response(log_message, status=404)

    # Success case
    content = blob.download_as_text()
    return Response(content, status=200, mimetype='text/html')

if __name__ == '__main__':
    # Running on port 8080 as it's common for containers, 
    # but the service will map it to port 80.
    app.run(host='0.0.0.0', port=8080)
