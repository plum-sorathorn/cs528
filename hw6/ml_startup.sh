#!/bin/bash
if [ -f /var/log/startup_already_done ]; then exit 0; fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3-pip

# Install only what Python needs for ML and SQL
pip3 install --break-system-packages pandas scikit-learn sqlalchemy pymysql
pip3 install --break-system-packages "cloud-sql-python-connector[pymysql]"

# Pull the code and DB password
curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/ml-code > /tmp/ml_pipeline.py
export DB_PASS=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/DB_PASS)

# Run the ML pipeline (This will generate /tmp/predictions.txt)
python3 /tmp/ml_pipeline.py

# NEW: Upload the file using native Bash/gsutil
echo "Uploading results to GCS..."
gsutil cp /tmp/predictions.txt gs://cs528-plum-hw2/hw6_results/predictions.txt

touch /var/log/startup_already_done