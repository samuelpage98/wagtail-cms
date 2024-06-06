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
logger = logging.getLogger()
logger.setLevel("DEBUG")


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')


application = cast(  # incomplete hints in django-stubs
    WSGIApplication, get_wsgi_application()
)

apig_wsgi_handler = make_lambda_handler(
    application, binary_support=None)

# non_binary_content_type_prefixes=['image/svg+xml', 'text', 'application/json']

def download_db_from_s3():
    s3_client = boto3.client('s3')
    bucket_name = os.environ['BUCKET_NAME']
    object_key = 'db.sqlite3'
    download_path = '/tmp/db.sqlite3'

    s3_client.download_file(bucket_name, object_key, download_path)
    return download_path

def upload_db_to_s3(db_path):
    s3_client = boto3.client('s3')
    bucket_name = os.environ['BUCKET_NAME']
    object_key = 'db.sqlite3'
    
    s3_client.upload_file(db_path, bucket_name, object_key)
    
def createSingleLogEvent(event: dict[str, Any], response: dict[str, Any]):
    returnedEvent = {}
    for key in event:
        returnedEvent['event.'+key] = event[key]
    for key in response:
        returnedEvent['response.'+key] = response[key]

    return returnedEvent


def lambda_handler(event: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
     # Download the latest SQLite database from S3
    db_path = download_db_from_s3()

    # Update the environment variable for SQLite DB path
    os.environ['SQLITE_DB_PATH'] = db_path

    # Ensure Django settings use the updated database path
    settings.DATABASES['default']['NAME'] = db_path

    
    # logger.info(event['requestContext']['path'])
    # logger.info(json.dumps(event, indent=2, sort_keys=True))
    response = apig_wsgi_handler(event, context)
    logger.info(json.dumps(createSingleLogEvent(
        event, response), indent=2, sort_keys=True))

    upload_db_to_s3(db_path)
    
    return response
