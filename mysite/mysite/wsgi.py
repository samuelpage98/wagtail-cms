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
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from typing import cast
from typing import Any
import json
import os
import logging
import boto3
import time
import random
from django.core.management import call_command
from django.http import JsonResponse

logger = logging.getLogger()
logger.setLevel("INFO")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

application = cast(WSGIApplication, get_wsgi_application())

apig_wsgi_handler = make_lambda_handler(application, binary_support=True)

dynamodb_client = boto3.client('dynamodb')
s3_client = boto3.client('s3')
table_name = os.environ['TABLE_NAME']
bucket_name = os.environ['BUCKET_NAME']

# S3 upload retry constraints
RETRY_DELAY = 0.2 * (1 + random.random())  # seconds
MAX_RETRIES = 5

@csrf_exempt
def migrate(request):
    if request.method == 'POST':
        domain_name = 'example.com' 

        # Get the latest version info
        latest_version_info = get_latest_version(domain_name)
        if latest_version_info:
            s3_version_id = latest_version_info['s3VersionId']
            current_version = latest_version_info['version']
        else:
            # Initialize with a new object if no version exists
            current_version = 0
            s3_version_id = None

        # Download the latest database from S3 using the latest version's version_id
        db_path = download_db_from_s3(s3_version_id)

        # Update the environment variable for SQLite DB path
        os.environ['SQLITE_DB_PATH'] = db_path

        # Ensure Django settings use the updated database path
        settings.DATABASES['default']['NAME'] = db_path

        try:
            # Run Django migrations
            call_command('makemigrations')
            call_command('migrate')

            # Upload the SQLite file back to S3
            new_version = current_version + 1
            retries = 0

            # Could probably do with being its own function
            while retries < MAX_RETRIES:
                try:
                    new_s3_version_id = upload_db_to_s3(db_path)
                    update_version(domain_name, new_version, new_s3_version_id, current_version)
                    return JsonResponse({'message': 'Migrations completed successfully.'}, status=200)
                except Exception as e:
                    logger.error(f'Version update conflict: {str(e)}')
                    retries += 1
                    if retries >= MAX_RETRIES:
                        logger.error('Max retries reached, aborting')
                        return JsonResponse({'message': 'Max retries reached, aborting'}, status=500)
                    time.sleep(RETRY_DELAY)
                    latest_version_info = get_latest_version(domain_name)
                    if latest_version_info:
                        s3_version_id = latest_version_info['s3VersionId']
                        current_version = latest_version_info['version']
                    else:
                        s3_version_id = None
                        current_version = 0
                    db_path = download_db_from_s3(s3_version_id)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=500)

def download_db_from_s3(version_id=None):
    object_key = 'db.sqlite3'
    download_path = '/tmp/db.sqlite3'
    extra_args = {"VersionId": version_id} if version_id else {}
    s3_client.download_file(bucket_name, object_key,
                            download_path, ExtraArgs=extra_args)
    return download_path


def upload_db_to_s3(db_path):
    object_key = 'db.sqlite3'
    s3_client.upload_file(db_path, bucket_name, object_key)
    head_response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
    return head_response['VersionId']


def get_latest_version(domain_name: str) -> dict:
    try:
        response = dynamodb_client.query(
            TableName=table_name,
            KeyConditionExpression='domainName = :domainName',
            ExpressionAttributeValues={
                ':domainName': {'S': domain_name}
            },
            ScanIndexForward=False,
            Limit=1
        )
        items = response.get('Items')
        if items:
            item = items[0]
            logger.debug(f"Latest version item: {item}")
            return {
                'domainName': item['domainName']['S'],
                's3Path': item['s3Path']['S'],
                'version': int(item['version']['N']),
                's3VersionId': item['s3VersionId']['S']
            }
        else:
            logger.debug("No items found")
            return None
    except Exception as e:
        logger.error(f"Error querying DynamoDB: {str(e)}")
        raise


def update_version(domain_name, new_version, s3_version_id, expected_version=None):
    try:
        response = dynamodb_client.put_item(
            TableName=table_name,
            Item={
                'domainName': {'S': domain_name},
                's3Path': {'S': 'db.sqlite3'},
                'version': {'N': str(new_version)},
                's3VersionId': {'S': s3_version_id}
            },
            ConditionExpression='attribute_not_exists(domainName) OR version < :expected_version',
            ExpressionAttributeValues={
                ':expected_version': {'N': str(expected_version)}
            }
        )
        logger.debug(
            f"Updated version: {new_version} for domain: {domain_name}")
        return {
            'domainName': domain_name,
            'version': new_version,
            's3VersionId': s3_version_id
        }
    except dynamodb_client.exceptions.ConditionalCheckFailedException as e:
        logger.error(f"Version conflict: {str(e)}")
        raise Exception('Version conflict, try again.')
    except Exception as e:
        logger.error(f"Error updating DynamoDB: {str(e)}")
        raise


def createSingleLogEvent(event: dict[str, Any], response: dict[str, Any]):
    returnedEvent = {}
    for key in event:
        returnedEvent['event.' + key] = event[key]
    for key in response:
        returnedEvent['response.' + key] = response[key]

    return returnedEvent


def lambda_handler(event: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    domain_name = 'example.com'

    # Get the latest version info
    latest_version_info = get_latest_version(domain_name)
    if latest_version_info:
        s3_version_id = latest_version_info['s3VersionId']
        current_version = latest_version_info['version']
    else:
        # Initialize with a new object if no version exists
        current_version = 0
        s3_version_id = None

    # Download the latest database from S3 using the latest version's version_id
    db_path = download_db_from_s3(s3_version_id)

    # Update the environment variable for SQLite DB path
    os.environ['SQLITE_DB_PATH'] = db_path

    # Ensure Django settings use the updated database path
    settings.DATABASES['default']['NAME'] = db_path

    # Log event and response
    response = apig_wsgi_handler(event, context)
    logger.info(json.dumps(createSingleLogEvent(
        event, response), indent=2, sort_keys=True))

    if event['httpMethod'] in ['POST', 'PUT', 'DELETE']:
        new_version = current_version + 1
        retries = 0

        while retries < MAX_RETRIES:
            try:
                new_s3_version_id = upload_db_to_s3(db_path)
                update_version(domain_name, new_version,
                               new_s3_version_id, current_version)
                break  # Exit loop if successful
            except Exception as e:
                logger.error(f'Version update conflict: {str(e)}')
                retries += 1
                if retries >= MAX_RETRIES:
                    logger.error('Max retries reached, aborting')
                    raise
                time.sleep(RETRY_DELAY)
                latest_version_info = get_latest_version(domain_name)
                if latest_version_info:
                    s3_version_id = latest_version_info['s3VersionId']
                    current_version = latest_version_info['version']
                else:
                    s3_version_id = None
                    current_version = 0
                db_path = download_db_from_s3(s3_version_id)
                response = apig_wsgi_handler(event, context)

    return response
