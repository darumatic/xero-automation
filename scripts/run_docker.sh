set -ex
docker run --env-file .env -e VALIDATION_EXCEPTIONS=$VALIDATION_EXCEPTIONS -e GITLAB_PRIVATE_TOKEN=$GITLAB_PRIVATE_TOKEN -e CI_PROJECT_ID=$CI_PROJECT_ID --rm $CI_REGISTRY_IMAGE:latest /usr/bin/python /opt/xero_automation/xero_report.py validation --client-id=$CLIENT_ID --client-secret=$CLIENT_SECRET --refresh-token=$REFRESH_TOKEN --tenant-id=$TENANT_ID
