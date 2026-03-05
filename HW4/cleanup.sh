#!/bin/bash

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
ZONE="us-central1-a"

echo "Tearing down infrastructure for project: $PROJECT_ID"

gcloud compute instances delete hw4-server-vm hw4-client-vm hw4-listener-vm --zone=$ZONE --quiet
gcloud compute firewall-rules delete allow-http-80 --quiet
gcloud compute addresses delete hw4-static-ip --region=$REGION --quiet
gcloud pubsub subscriptions delete hw4-topic-sub --quiet
gcloud pubsub topics delete hw4-topic --quiet

SERVER_SA_EMAIL="hw4-server-sa@${PROJECT_ID}.iam.gserviceaccount.com"
LISTENER_SA_EMAIL="hw4-listener-sa@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud iam service-accounts delete $SERVER_SA_EMAIL --quiet
gcloud iam service-accounts delete $LISTENER_SA_EMAIL --quiet

gcloud auth application-default revoke --quiet || echo "No ADC found to revoke."
echo "Cleanup complete."