import base64
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

def stop_sql_instance(event, context):
    project = 'cs528-485615'  # Hardcoded as per instructions
    instance = 'hw5-db-instance'

    credentials = GoogleCredentials.get_application_default()
    service = discovery.build('sqladmin', 'v1beta4', credentials=credentials)

    # Patch the instance to move it to a "NEVER" activation policy
    db_instance_resource = {
        "settings": {
            "activationPolicy": "NEVER"
        }
    }

    request = service.instances().patch(
        project=project,
        instance=instance,
        body=db_instance_resource
    )
    
    response = request.execute()
    print(f"Cloud SQL instance {instance} stopping...")
    return f"Status: {response['status']}"