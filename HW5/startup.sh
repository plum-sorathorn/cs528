#!/bin/bash
if [ -f /var/log/startup_already_done ]; then exit 0; fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3-pip python3-dev
pip3 install --break-system-packages flask sqlalchemy pymysql google-cloud-storage "cloud-sql-python-connector[pymysql]" google-cloud-pubsub
export no_proxy=metadata.google.internal,169.254.169.254
export NO_PROXY=metadata.google.internal,169.254.169.254

mkdir -p /home/plum

# --- WRITE THE APP CODE ---
cat <<EOF > /home/plum/app.py
import os, time, sqlalchemy
from flask import Flask, request, Response
from google.cloud import storage, pubsub_v1
from google.cloud.sql.connector import Connector

app = Flask(__name__)
connector = Connector()
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("cs528-485615", "hw5-topic")

def getconn():
    return connector.connect(
        os.environ["INSTANCE_CONNECTION_NAME"], "pymysql",
        user=os.environ["DB_USER"], password=os.environ["DB_PASS"], db="hw5_db"
    )

pool = sqlalchemy.create_engine("mysql+pymysql://", creator=getconn)

def read_gcs_file(filename):
    start = time.perf_counter()
    try:
        from google.cloud import storage
        # This bypasses all authentication and metadata checks
        client = storage.Client.create_anonymous_client() 
        
        # Ensure this matches your HW2 bucket name
        bucket = client.bucket("cs528-plum-hw2") 
        blob = bucket.blob(f"data/{filename}")
        
        content = blob.download_as_text()
        return content, 200, time.perf_counter() - start
    except Exception as e:
        print(f">>> GCS Anonymous Read Error: {str(e)}", flush=True)
        return "File Not Found", 404, time.perf_counter() - start

def process_headers(req):
    start = time.perf_counter()
    country = req.headers.get('X-country', 'Unknown')
    
    # Handle age ranges like "17-25" or "36-45"
    raw_age = req.headers.get('X-age', '0')
    try:
        # Split by hyphen and take the first part, then convert to int
        age = int(str(raw_age).split('-')[0])
    except (ValueError, IndexError, TypeError):
        age = 0

    data = {
        'country': country,
        'ip': req.remote_addr,
        'gender': req.headers.get('X-gender', 'N/A'),
        'age': age,
        'income': req.headers.get('X-income', 'N/A'),
        'is_banned': country == 'North Korea',
        'file': 'index.html' # Overwritten in main()
    }
    
    if data['is_banned']:
        publisher.publish(topic_path, f"Forbidden request from {country}".encode("utf-8"))
    return data, time.perf_counter() - start

def log_to_database(m, code):
    start = time.perf_counter()
    with pool.connect() as conn:
        if code == 200:
            conn.execute(sqlalchemy.text("""
                INSERT INTO request_logs (country, client_ip, gender, age, income, is_banned, requested_file)
                VALUES (:country, :ip, :gender, :age, :income, :is_banned, :file)
            """), m)
        else:
            conn.execute(sqlalchemy.text("""
                INSERT INTO error_logs (requested_file, error_code)
                VALUES (:file, :code)
            """), {"file": m['file'], "code": code})
        conn.commit()
    return time.perf_counter() - start

def build_response(content, code):
    start = time.perf_counter()
    res = Response(content, status=code)
    return res, time.perf_counter() - start

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def main(path):
    print(f">>> Request received for path: {path}", flush=True)

    import os
    if path:
        filename = os.path.basename(path)
    else:
        filename = request.args.get('filename', '0.html')

    m, t1 = process_headers(request)
    m['file'] = filename # Use the stripped filename for GCS and DB logs

    content, code, t2 = read_gcs_file(m['file'])
    t3 = log_to_database(m, code)
    res, t4 = build_response(content, code)
    
    print(f"Metrics: File={filename}, GCS={t2:.4f}s, DB={t3:.4f}s")
    return res

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
EOF

# Fetch metadata and run
export INSTANCE_CONNECTION_NAME=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/INSTANCE_CONNECTION_NAME)
export DB_USER=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_USER)
export DB_PASS=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_PASS)
export DB_NAME=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_NAME)

touch /var/log/app.log && chmod 666 /var/log/app.log
python3 /home/plum/app.py > /var/log/app.log 2>&1 &
touch /var/log/startup_already_done