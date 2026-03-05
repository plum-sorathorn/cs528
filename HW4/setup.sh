#!/bin/bash

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
ZONE="us-central1-a"

echo "Setting up infrastructure for project: $PROJECT_ID"

gcloud pubsub topics create hw4-topic
gcloud pubsub subscriptions create hw4-topic-sub --topic=hw4-topic

SERVER_SA="hw4-server-sa"
LISTENER_SA="hw4-listener-sa"
gcloud iam service-accounts create $SERVER_SA --display-name="HW4 Server SA"
gcloud iam service-accounts create $LISTENER_SA --display-name="HW4 Listener SA"

SERVER_SA_EMAIL="${SERVER_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
LISTENER_SA_EMAIL="${LISTENER_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${SERVER_SA_EMAIL}" --role="roles/storage.objectViewer"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${SERVER_SA_EMAIL}" --role="roles/logging.logWriter"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${SERVER_SA_EMAIL}" --role="roles/pubsub.publisher"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${LISTENER_SA_EMAIL}" --role="roles/pubsub.subscriber"

gcloud compute addresses create hw4-static-ip --region=$REGION
STATIC_IP=$(gcloud compute addresses describe hw4-static-ip --region=$REGION --format="value(address)")
echo "Reserved Static IP: $STATIC_IP"

gcloud compute firewall-rules create allow-http-80 --allow tcp:80 --source-ranges 0.0.0.0/0 --target-tags http-server

echo "Creating VM 1 (Web Server)..."
gcloud compute instances create hw4-server-vm --zone=$ZONE --machine-type=e2-micro --address=$STATIC_IP --service-account=$SERVER_SA_EMAIL --scopes=cloud-platform --tags=http-server --metadata-from-file=startup-script=startup-server.sh,server-script=server.py

echo "Creating VM 2 (Client Stress Tester - Ubuntu 24.04)..."
gcloud compute instances create hw4-client-vm --zone=$ZONE --machine-type=e2-micro --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud --scopes=cloud-platform

echo "Creating VM 3 (Listener)..."
gcloud compute instances create hw4-listener-vm --zone=$ZONE --machine-type=e2-micro --service-account=$LISTENER_SA_EMAIL --scopes=cloud-platform --metadata-from-file=startup-script=startup-listener.sh,listener-script=listener.py

echo "Setup complete! The web server is starting up at http://$STATIC_IP/"