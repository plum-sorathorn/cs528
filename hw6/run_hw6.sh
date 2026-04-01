#!/bin/bash
PROJECT_ID="cs528-485615"
INSTANCE_NAME="hw5-db-instance"
DB_NAME="hw5_db"
VM_NAME="hw6-ml-vm"
ZONE="us-central1-c"
BUCKET="cs528-plum-hw2"

echo "-----------------------------------------------"
echo "Step 1: Starting Database Instance"
gcloud sql instances patch $INSTANCE_NAME --activation-policy=ALWAYS --project=$PROJECT_ID

echo "-----------------------------------------------"
echo "Step 2: Provisioning ML VM..."

# In Step 2: Delete both files
gsutil rm gs://$BUCKET/hw6_results/model1_predictions.txt || true 
gsutil rm gs://$BUCKET/hw6_results/model2_predictions.txt || true 

gcloud compute instances create $VM_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=e2-standard-2 \
    --service-account="hw3-service-account@$PROJECT_ID.iam.gserviceaccount.com" \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --metadata-from-file startup-script=ml_startup.sh,ml-code=ml_pipeline.py \
    --metadata="DB_PASS=usHY09tQGzRbPO^)"

echo "-----------------------------------------------"
echo "Step 3: Waiting for ML results in GCS..."
until gsutil ls gs://$BUCKET/hw6_results/model2_predictions.txt >/dev/null 2>&1; do
  echo "VM is training models... (checking GCS every 20s)"
  sleep 20
done

echo "-----------------------------------------------"
echo "Step 4: Displaying Final Results"
gsutil cat gs://$BUCKET/hw6_results/model1_predictions.txt
echo ""
gsutil cat gs://$BUCKET/hw6_results/model2_predictions.txt

echo "-----------------------------------------------"
echo "Step 5: Cleanup"
gcloud compute instances delete $VM_NAME --zone=$ZONE --quiet
gcloud sql instances patch $INSTANCE_NAME --activation-policy=NEVER --quiet
echo "HW6 Complete!"