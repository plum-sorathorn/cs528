import os

# 🔥 Environment Fixes (must be first)
os.environ["GCE_METADATA_HOST"] = "169.254.169.254"
os.environ["GCE_METADATA_IP"] = "169.254.169.254"
os.environ["GCE_METADATA_MTLS_MODE"] = "none"

for var in [
    'http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
    'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE'
]:
    os.environ.pop(var, None)

os.environ["NO_PROXY"] = "169.254.169.254,metadata.google.internal,localhost,127.0.0.1"
os.environ["no_proxy"] = os.environ["NO_PROXY"]

# Imports
import requests
from flask import Flask, request, Response
from google.cloud import storage

app = Flask(__name__)

# Config
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "cs528-485615")
BUCKET_NAME = "cs528-plum-hw2"

BANNED_COUNTRIES = {
    "North Korea", "Iran", "Cuba", "Myanmar",
    "Iraq", "Libya", "Sudan", "Zimbabwe", "Syria"
}

# 🚀 Initialize clients ONCE
print("Initializing storage client...")
try:
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    print("Storage client ready.")
except Exception as e:
    print(f"FATAL: Failed to initialize storage client: {e}")
    storage_client = None
    bucket = None

# Get Zone (fast + safe)
ZONE = "unknown-zone"
try:
    r = requests.get(
        "http://169.254.169.254/computeMetadata/v1/instance/zone",
        headers={"Metadata-Flavor": "Google"},
        timeout=0.5
    )
    if r.status_code == 200:
        ZONE = r.text.split("/")[-1]
except Exception:
    pass

# Routes

@app.route("/health", methods=["GET"])
def health():
    return Response("OK", status=200)


@app.route("/", defaults={"filepath": ""}, methods=["GET"])
@app.route("/<path:filepath>", methods=["GET"])
def handle(filepath):
    # Only allow GET
    if request.method != "GET":
        return Response("Method Not Allowed", status=405)

    # Country filter
    if request.headers.get("X-country", "") in BANNED_COUNTRIES:
        resp = Response("Permission Denied", status=400)
        resp.headers["X-Zone"] = ZONE
        return resp

    # Resolve filename
    filename = request.args.get("filename") or filepath
    filename = filename.strip("/")

    if not filename:
        resp = Response("Missing filename", status=400)
        resp.headers["X-Zone"] = ZONE
        return resp

    if bucket is None:
        resp = Response("Storage not initialized", status=500)
        resp.headers["X-Zone"] = ZONE
        return resp

    # Fetch from GCS (single fast call, no exists())
    try:
        blob = bucket.blob(f"data/{filename}")
        content = blob.download_as_text(timeout=10)

        resp = Response(content, status=200, mimetype="text/html")

    except Exception as e:
        # Treat all failures as 404 (fast + safe)
        print(f"REAL ERROR: {e}", flush=True)
        resp = Response(f"Not Found: {filename}", status=404)

    resp.headers["X-Zone"] = ZONE
    return resp


# Run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)