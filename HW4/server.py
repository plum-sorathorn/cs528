import os
from flask import Flask, request, Response
from google.cloud import storage, pubsub_v1, logging as cloud_logging

app = Flask(__name__)

project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'cs528-485615')
storage_client = storage.Client(project=project_id)
pubsub_publisher = pubsub_v1.PublisherClient()
logging_client = cloud_logging.Client(project=project_id)
logger = logging_client.logger("hw4-web-server-log")

BUCKET_NAME = "cs528-plum-hw2"
TOPIC_ID = "hw4-topic"
BANNED_COUNTRIES = ["North Korea", "Iran", "Cuba", "Myanmar", "Iraq", "Libya", "Sudan", "Zimbabwe", "Syria"]

# Catch-all routes to handle BOTH path variables (/11568.html) and query strings (/?filename=0.html)
@app.route('/<path:filepath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH'])
@app.route('/', defaults={'filepath': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH'])
def handle_request(filepath):
    if request.method != 'GET':
        log_message = f"Method {request.method} not allowed"
        logger.log_text(log_message, severity="WARNING")
        return Response(log_message, status=501)

    country_header = request.headers.get('X-country', '')
    if country_header in BANNED_COUNTRIES:
        log_message = f"Forbidden request from {country_header}"
        logger.log_text(log_message, severity="CRITICAL")
        topic_path = pubsub_publisher.topic_path(project_id, TOPIC_ID)
        pubsub_publisher.publish(topic_path, log_message.encode("utf-8"))
        return Response("Permission Denied", status=400)

    filename = request.args.get('filename') or filepath
    
    filename = filename.replace('hw3-function/', '').replace('none/', '').strip('/')

    if not filename:
        return Response("Bad Request: Missing filename", status=400)

    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"data/{filename}")

    if not blob.exists():
        log_message = f"File data/{filename} not found"
        logger.log_text(log_message, severity="WARNING")
        return Response(log_message, status=404)

    content = blob.download_as_text()
    return Response(content, status=200, mimetype='text/html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)