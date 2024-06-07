"""
WSGI config for mysite project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""
from __future__ import annotations
from django.core.wsgi import get_wsgi_application
from apig_wsgi import make_lambda_handler
from apig_wsgi.compat import WSGIApplication
from django.conf import settings
from typing import cast
from typing import Any
import json
import os
import logging
import boto3
import requests

logger = logging.getLogger()
logger.setLevel("DEBUG")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

application = cast(  # incomplete hints in django-stubs
    WSGIApplication, get_wsgi_application()
)

apig_wsgi_handler = make_lambda_handler(
    application, binary_support=True)

def download_db_from_s3(object_key):
    s3_client = boto3.client('s3')
    bucket_name = os.environ['BUCKET_NAME']
    download_path = '/tmp/db.sqlite3'

    s3_client.download_file(bucket_name, object_key, download_path)
    return download_path

def upload_db_to_s3(db_path, object_key):
    s3_client = boto3.client('s3')
    bucket_name = os.environ['BUCKET_NAME']
    
    s3_client.upload_file(db_path, bucket_name, object_key)

def get_latest_version(domain_name: str) -> dict:
    query = '''
    query GetLatestVersion($domainName: String!) {
      getLatestVersion(domainName: $domainName) {
        domainName
        s3Path
        version
      }
    }
    '''
    response = requests.post(
        url=os.environ['DATASTORE_API_URL'],
        json={'query': query, 'variables': {'domainName': domain_name}},
        headers={'x-api-key': os.environ['DATASTORE_API_KEY']}
    )
    data = response.json().get('data', {})
    if 'errors' in data:
        logger.error(f"Error fetching latest version: {data['errors']}")
        raise Exception(f"Error fetching latest version: {data['errors']}")
    return data.get('getLatestVersion', None)

def update_version(domain_name: str, s3_path: str) -> dict:
    mutation = '''
    mutation UpdateVersion($domainName: String!, $s3Path: String!) {
      updateVersion(domainName: $domainName, s3Path: $s3Path) {
        domainName
        s3Path
        version
      }
    }
    '''
    response = requests.post(
        url=os.environ['DATASTORE_API_URL'],
        json={'query': mutation, 'variables': {'domainName': domain_name, 's3Path': s3_path}},
        headers={'x-api-key': os.environ['DATASTORE_API_KEY']}
    )
    data = response.json()
    if 'errors' in data:
        logger.error(f"Error updating version: {data['errors']}")
        raise Exception(f"Error updating version: {data['errors']}")
    return data['data']['updateVersion']

def createSingleLogEvent(event: dict[str, Any], response: dict[str, Any]):
    returnedEvent = {}
    for key in event:
        returnedEvent['event.'+key] = event[key]
    for key in response:
        returnedEvent['response.'+key] = response[key]

    return returnedEvent

def lambda_handler(event: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    domain_name = 'example.com'
    
    # Get the latest version info
    latest_version_info = get_latest_version(domain_name)
    if latest_version_info:
        s3_path = latest_version_info['s3Path']
    else:
        s3_path = 'db.sqlite3'  # Default path for initial setup

    # Download the latest database from S3 using the latest version's s3_path
    db_path = download_db_from_s3(s3_path)

    # Update the environment variable for SQLite DB path
    os.environ['SQLITE_DB_PATH'] = db_path

    # Ensure Django settings use the updated database path
    settings.DATABASES['default']['NAME'] = db_path

    # Log event and response
    response = apig_wsgi_handler(event, context)
    logger.info(json.dumps(createSingleLogEvent(event, response), indent=2, sort_keys=True))

    if event['httpMethod'] in ['POST', 'PUT', 'DELETE']:
        new_s3_path = f'{context.aws_request_id}-db.sqlite3'
        upload_db_to_s3(db_path, new_s3_path)

        try:
            update_version(domain_name, new_s3_path)
        except Exception as e:
            logger.error(f'Version update conflict: {str(e)}')
            latest_version_info = get_latest_version(domain_name)
            if latest_version_info:
                s3_path = latest_version_info['s3Path']
            else:
                s3_path = 'db.sqlite3'  # Default path for initial setup
            db_path = download_db_from_s3(s3_path)  # Ensure we use the correct path
            response = apig_wsgi_handler(event, context)
            upload_db_to_s3(db_path, new_s3_path)
            update_version(domain_name, new_s3_path)

    return response