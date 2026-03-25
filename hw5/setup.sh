#!/bin/bash
# 1. Configuration - Hardcoded as required by instructions
PROJECT_ID="cs528-485615" 
REGION="us-central1"
ZONE="us-central1-a"
INSTANCE_NAME="hw5-db-instance"
SERVICE_ACCOUNT="hw3-service-account@$PROJECT_ID.iam.gserviceaccount.com"
DB_PASS='usHY09tQGzRbPO^)'

# Install libraries needed for setup_schema.py to run locally in Cloud Shell
echo "Installing Cloud Shell dependencies..."
pip3 install --user --break-system-packages -q sqlalchemy pymysql "cloud-sql-python-connector[pymysql]"

echo "-----------------------------------------------"
echo "Step 1: Preparing Cloud SQL"
# Check if instance exists
EXISTS=$(gcloud sql instances list --project=$PROJECT_ID --filter="name=$INSTANCE_NAME" --format="value(name)")

if [ "$EXISTS" == "$INSTANCE_NAME" ]; then
    echo "Instance exists. Ensuring it is started..."
    gcloud sql instances patch $INSTANCE_NAME --project=$PROJECT_ID --activation-policy=ALWAYS --async
else
    echo "Creating new instance (this will take ~15 mins)..."
    gcloud sql instances create $INSTANCE_NAME --project=$PROJECT_ID --database-version=MYSQL_8_0 --tier=db-f1-micro --region=$REGION --root-password=$DB_PASS
    
    echo "Creating hw5_db database..."
    gcloud sql databases create hw5_db --instance=$INSTANCE_NAME --project=$PROJECT_ID
    
    echo "Running schema setup..."
    export DB_PASS="$DB_PASS"
    python3 setup_schema.py
fi

echo "-----------------------------------------------"
echo "Step 2: Static IP Allocation"
IP_EXISTS=$(gcloud compute addresses list --project=$PROJECT_ID --filter="name=hw5-static-ip" --format="value(name)")

if [ "$IP_EXISTS" != "hw5-static-ip" ]; then
    gcloud compute addresses create hw5-static-ip --project=$PROJECT_ID --region=$REGION
fi

STATIC_IP=$(gcloud compute addresses describe hw5-static-ip --project=$PROJECT_ID --region=$REGION --format='value(address)')
echo "Using Static IP: $STATIC_IP"

echo "-----------------------------------------------"
echo "Step 3: Firewall Configuration"
# Create firewall rule if it doesn't exist to allow port 80 traffic
FW_EXISTS=$(gcloud compute firewall-rules list --project=$PROJECT_ID --filter="name=allow-http-80" --format="value(name)")

if [ "$FW_EXISTS" != "allow-http-80" ]; then
    echo "Creating firewall rule to allow port 80 traffic..."
    gcloud compute firewall-rules create allow-http-80 \
        --project=$PROJECT_ID \
        --allow tcp:80 \
        --target-tags=http-server \
        --description="Allow HTTP traffic for HW5"
else
    echo "Firewall rule 'allow-http-80' already exists."
fi

echo "-----------------------------------------------"
echo "Step 3.5: Pub/Sub Setup"
# Create Topic if missing
gcloud pubsub topics create hw5-topic --project=$PROJECT_ID || echo "Topic exists"
# Create Subscription if missing
gcloud pubsub subscriptions create hw5-topic-sub --topic=hw5-topic --project=$PROJECT_ID || echo "Sub exists"

echo "-----------------------------------------------"
echo "Step 4: Provisioning VMs"

# Create Web Server VM (Idempotent check)
VM1_EXISTS=$(gcloud compute instances list --project=$PROJECT_ID --filter="name=hw5-web-server" --format="value(name)")
if [ "$VM1_EXISTS" != "hw5-web-server" ]; then
    gcloud compute instances create hw5-web-server \
        --project=$PROJECT_ID \
        --zone=$ZONE \
        --machine-type=e2-micro \
        --address=$STATIC_IP \
        --service-account=$SERVICE_ACCOUNT \
        --scopes=https://www.googleapis.com/auth/cloud-platform \
        --metadata-from-file startup-script=startup.sh \
        --metadata="INSTANCE_CONNECTION_NAME=$PROJECT_ID:us-central1:$INSTANCE_NAME,DB_USER=root,DB_PASS=$DB_PASS,DB_NAME=hw5_db" \
        --tags=http-server
else
    echo "VM hw5-web-server already exists."
fi

# Create Listener VM (Forbidden country reporting service)
VM2_EXISTS=$(gcloud compute instances list --project=$PROJECT_ID --filter="name=hw5-listener-vm" --format="value(name)")
if [ "$VM2_EXISTS" != "hw5-listener-vm" ]; then
    gcloud compute instances create hw5-listener-vm \
        --project=$PROJECT_ID \
        --zone=$ZONE \
        --machine-type=e2-micro \
        --service-account=$SERVICE_ACCOUNT \
        --scopes=https://www.googleapis.com/auth/cloud-platform \
        --metadata="ROLE=listener" \
        --metadata-from-file startup-script=listener_startup.sh
else
    echo "VM hw5-listener-vm already exists."
fi

# deploy database hourly stopper
gcloud functions deploy stop-db-function \
    --runtime python311 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point stop_sql_instance \
    --region us-central1

# create the hourly schedule
gcloud scheduler jobs create http hourly-db-stop \
    --schedule="0 * * * *" \
    --uri="https://us-central1-cs528-485615.cloudfunctions.net/stop-db-function" \
    --http-method=GET \
    --location=us-central1

echo "-----------------------------------------------"
echo "Setup Complete. Waiting 2-3 minutes for startup.sh to finish inside the VM..."