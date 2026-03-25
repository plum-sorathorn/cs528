#!/bin/bash
# 1. Configuration - Hardcoded as required by instructions
PROJECT_ID="cs528-485615"

echo "-----------------------------------------------"
echo "Step 1: Deleting Virtual Machines"
gcloud compute instances delete hw5-web-server hw5-listener-vm \
    --project=$PROJECT_ID \
    --zone=us-central1-a \
    --quiet

echo "-----------------------------------------------"
echo "Step 2: Releasing Static IP"
IP_EXISTS=$(gcloud compute addresses list --project=$PROJECT_ID --filter="name=hw5-static-ip" --format="value(name)")
if [ "$IP_EXISTS" == "hw5-static-ip" ]; then
    gcloud compute addresses delete hw5-static-ip \
        --project=$PROJECT_ID \
        --region=us-central1 \
        --quiet
fi

echo "-----------------------------------------------"
echo "Step 3: Removing Firewall Rules"
FW_EXISTS=$(gcloud compute firewall-rules list --project=$PROJECT_ID --filter="name=allow-http-80" --format="value(name)")
if [ "$FW_EXISTS" == "allow-http-80" ]; then
    gcloud compute firewall-rules delete allow-http-80 \
        --project=$PROJECT_ID \
        --quiet
fi

echo "-----------------------------------------------"
echo "Step 4: Removing Cloud Function & Scheduler"
# Delete these before revoking credentials!
gcloud scheduler jobs delete hourly-db-stop --location=us-central1 --quiet
gcloud functions delete stop-db-function --region=us-central1 --quiet

echo "-----------------------------------------------"
echo "Step 5: Cleaning up Pub/Sub"
# Delete subscription before the topic
gcloud pubsub subscriptions delete hw5-topic-sub --project=$PROJECT_ID --quiet
gcloud pubsub topics delete hw5-topic --project=$PROJECT_ID --quiet

echo "-----------------------------------------------"
echo "Step 6: Stopping Cloud SQL (Billing Prevention)"
# Instructions: Just stop it, do not delete it
gcloud sql instances patch hw5-db-instance \
    --project=$PROJECT_ID \
    --activation-policy=NEVER

echo "-----------------------------------------------"
echo "Step 7: Revoking Credentials"
# Revoke ADC as required
gcloud auth application-default revoke --quiet

echo "-----------------------------------------------"
echo "Cleanup Complete. All billable resources (except the dormant DB) have been removed."