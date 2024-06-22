from __future__ import annotations
import sys
from django.core.wsgi import get_wsgi_application
from apig_wsgi import make_lambda_handler
from apig_wsgi.compat import WSGIApplication
from django.conf import settings
from typing import cast
from typing import Any
import os
import logging
import boto3
import time
import hashlib
from django.core.management import call_command

import django


logger = logging.getLogger()
logger.setLevel("INFO")


os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'

# Ensure the settings module is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(sys.path)


application = cast(WSGIApplication, get_wsgi_application())

django.setup()


def download_db_from_s3(version_id=None):
    s3_client = boto3.client('s3')
    bucket_name = os.environ['BUCKET_NAME']
    object_key = 'db.sqlite3'
    download_path = '/tmp/db.sqlite3'
    extra_args = {"VersionId": version_id} if version_id else {}

    print(
        f"Downloading {object_key} from S3 bucket {bucket_name} to {download_path}")
    print(f"Extra args: {extra_args}")
    try:
        print(s3_client.download_file(bucket_name, object_key,
                                      download_path, ExtraArgs=extra_args))
        print('Successfully downloaded')
        return True
    except Exception:
        print('Failed to download')
        return False


def delete_s3_version(version_id):
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.environ['BUCKET_NAME']
        object_key = 'db.sqlite3'
        # Delete the specific version of the object
        response = s3_client.delete_object(
            Bucket=bucket_name,
            Key=object_key,
            VersionId=version_id
        )
        print(
            f"Successfully deleted version {version_id} of {object_key} from bucket {bucket_name}.")
        return response

    except NoCredentialsError:
        print("Error: AWS credentials not found.")
    except PartialCredentialsError:
        print("Error: Incomplete AWS credentials.")
    except ClientError as e:
        print(f"An error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def upload_db_to_s3(db_path='/tmp/db.sqlite3'):
    s3_client = boto3.client('s3')
    bucket_name = os.environ['BUCKET_NAME']
    object_key = 'db.sqlite3'
    s3_client.upload_file(db_path, bucket_name, object_key)
    head_response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
    return head_response['VersionId']


def get_latest_version(domain_name: str) -> dict:
    try:

        dynamodb_client = boto3.client('dynamodb')
        table_name = os.environ['TABLE_NAME']
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

        dynamodb_client = boto3.client('dynamodb')
        table_name = os.environ['TABLE_NAME']
        dynamodb_client.put_item(
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


def clear_version_table():
    dynamodb = boto3.resource('dynamodb')
    dynamodb_client = boto3.client('dynamodb')
    table_name = os.environ['TABLE_NAME']
    try:
        # Scan the table to get all the items
        response = dynamodb_client.scan(TableName=table_name)
        data = response.get('Items', [])
        table = dynamodb.Table(table_name)
        # Keep scanning until all the items are retrieved
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response.get('Items', []))

        # Delete each item
        with table.batch_writer() as batch:
            for item in data:
                batch.delete_item(
                    Key={
                        # Replace with your table's primary key
                        'domainName': item['domainName'],
                        'version': item['version']
                        # Include additional key attributes if your table uses a composite primary key
                    }
                )

        print(f"All items have been deleted from the table {table_name}.")
    except Exception as e:
        print(f"Error deleting items from the table: {e}")
        print(e)


def createSingleLogEvent(event: dict[str, Any], response: dict[str, Any]):
    returnedEvent = {}
    for key in event:
        returnedEvent['event.' + key] = event[key]
    for key in response:
        returnedEvent['response.' + key] = response[key]

    return returnedEvent


def lambda_handler(event: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:

    domain_name = 'example.com'

    force_write = False
    #
    #  At the end of this we will have a new db or have fetched the latest
    #
    print('Getting latest version')
    latest_version_info = get_latest_version(domain_name)

    current_version = latest_version_info['version'] if latest_version_info else 0
    s3_version_id = latest_version_info['s3VersionId'] if latest_version_info else None
    new_version = current_version + 1
    if not download_db_from_s3(s3_version_id):
        print(
            f'Version {latest_version_info["s3VersionId"]} in DDB does not exist')
        # the version pointed to by ddb didn't exist, so just get latest
        if not download_db_from_s3():

            # and if that doesn't exist then just create a new one
            # delete /tmp/db.sqlite3
            os.remove('/tmp/db.sqlite3') if os.path.exists(
                '/tmp/db.sqlite3') else None
            sm = boto3.client('secretsmanager')
            print('Empty DB Initialising')
            call_command('migrate')
            call_command('createsuperuser',
                         '--no-input',
                         f'--email={sm.get_secret_value(SecretId="SUPER_USEREMAIL")["SecretString"]}',
                         f'--username={sm.get_secret_value(SecretId="SUPER_USERNAME")["SecretString"]}'
                         )
            from django.contrib.auth.models import User
            u = User.objects.get(username=sm.get_secret_value(
                SecretId="SUPER_USERNAME")["SecretString"])
            u.set_password(sm.get_secret_value(
                SecretId="SUPER_USERPASSWORD")["SecretString"])
            u.save()
            clear_version_table()
            force_write = True

    action = None
    response = None

    if 'command' in event:

        if event['command'] == 'migrate':
            def action(event, context):
                print('Performing DB Migration')
                try:
                    call_command('makemigrations')
                    call_command('migrate')
                    response = {'status': 'done'}

                except e as Exception:
                    response = {'status': 'error',
                                'message': e}

                return response
            force_write = True

        elif event['command'] == 'webrequest':
            def action(event, context): return (
                print('Performing Web Request'),
                (make_lambda_handler(
                    application,
                    binary_support=True)(event, context)))
    else:
        def action(event, context):
            print('Performing Web Request')
            response = (make_lambda_handler(
                application,
                binary_support=True)(event, context))
            return response

    file_hash_before = hashlib.md5(
        open('/tmp/db.sqlite3', 'rb').read()).hexdigest()
    print('File hashbefore is '+file_hash_before)
    response = action(event, context)

    if event['httpMethod'] in ['POST', 'PUT', 'DELETE'] or force_write:
        print('Attempting to save back to S3')
        retries = 0
        RETRY_DELAY = [0.01, 0.005]
        MAX_RETRIES = 10

        file_hash_after = hashlib.md5(
            open('/tmp/db.sqlite3', 'rb').read()).hexdigest()

        if file_hash_after != file_hash_before:
            print('File has changed, attempting to save back')
            while retries < MAX_RETRIES:
                try:

                    new_s3_version_id = upload_db_to_s3()
                    update_version(domain_name, new_version,
                                   new_s3_version_id, current_version)
                    print('Uploaded successfully ' + new_s3_version_id)
                    break  # Exit loop if successful
                except Exception as e:
                    logger.error(f'Version update conflict: {str(e)}')
                    # delete failed  upload
                    delete_s3_version(new_s3_version_id)
                    retries += 1
                    if retries >= MAX_RETRIES:
                        logger.error('Max retries reached, aborting')
                        raise
                    # progressively increase retry delay using fibonacci sequence
                    print(
                        f"Retrying in {RETRY_DELAY[0]} seconds (retry {retries}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY[0])
                    RETRY_DELAY = [RETRY_DELAY[0] +
                                   RETRY_DELAY[1], *RETRY_DELAY]

                    latest_version_info = get_latest_version(domain_name)
                    if latest_version_info:
                        s3_version_id = latest_version_info['s3VersionId']
                        current_version = latest_version_info['version']
                    else:
                        s3_version_id = None
                        current_version = 0
                    download_db_from_s3(s3_version_id)
                    response = action(event, context)
        else:
            print('File unchanged, not saving back')

    return response


def createSampleWeb(path):
    return {
        "body": "",
        "resource": "/{proxy+}",
        "path": path,
        "httpMethod": "POST",
        "isBase64Encoded": 'false',
        "queryStringParameters": {
            "foo": "bar"
        },
        "multiValueQueryStringParameters": {
            "foo": [
                "bar"
            ]
        },
        "pathParameters": {
            "proxy": "/path/to/resource"
        },
        "stageVariables": {
            "baz": "qux"
        },
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, sdch",
            "Accept-Language": "en-US,en;q=0.8",
            "Cache-Control": "max-age=0",
            "CloudFront-Forwarded-Proto": "https",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-Mobile-Viewer": "false",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Tablet-Viewer": "false",
            "CloudFront-Viewer-Country": "US",
            "Host": "1234567890.execute-api.us-east-1.amazonaws.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Custom User Agent String",
            "Via": "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)",
            "X-Amz-Cf-Id": "cDehVQoZnx43VYQb9j2-nvCh-9z396Uhbp027Y2JvkCPNLmGJHqlaA==",
            "X-Forwarded-For": "127.0.0.1, 127.0.0.2",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https"
        },
        "multiValueHeaders": {
            "Accept": [
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            ],
            "Accept-Encoding": [
                "gzip, deflate, sdch"
            ],
            "Accept-Language": [
                "en-US,en;q=0.8"
            ],
            "Cache-Control": [
                "max-age=0"
            ],
            "CloudFront-Forwarded-Proto": [
                "https"
            ],
            "CloudFront-Is-Desktop-Viewer": [
                "true"
            ],
            "CloudFront-Is-Mobile-Viewer": [
                "false"
            ],
            "CloudFront-Is-SmartTV-Viewer": [
                "false"
            ],
            "CloudFront-Is-Tablet-Viewer": [
                "false"
            ],
            "CloudFront-Viewer-Country": [
                "US"
            ],
            "Host": [
                "0123456789.execute-api.us-east-1.amazonaws.com"
            ],
            "Upgrade-Insecure-Requests": [
                "1"
            ],
            "User-Agent": [
                "Custom User Agent String"
            ],
            "Via": [
                "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)"
            ],
            "X-Amz-Cf-Id": [
                "cDehVQoZnx43VYQb9j2-nvCh-9z396Uhbp027Y2JvkCPNLmGJHqlaA=="
            ],
            "X-Forwarded-For": [
                "127.0.0.1, 127.0.0.2"
            ],
            "X-Forwarded-Port": [
                "443"
            ],
            "X-Forwarded-Proto": [
                "https"
            ]
        },
        "requestContext": {
            "accountId": "123456789012",
            "resourceId": "123456",
            "stage": "prod",
            "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {
                "cognitoIdentityPoolId": None,
                "accountId": None,
                "cognitoIdentityId": None,
                "caller": None,
                "accessKey": None,
                "sourceIp": "127.0.0.1",
                "cognitoAuthenticationType": None,
                "cognitoAuthenticationProvider": None,
                "userArn": None,
                "userAgent": "Custom User Agent String",
                "user": None
            },
            "path": "/prod/path/to/resource",
            "resourcePath": "/{proxy+}",
            "httpMethod": "POST",
            "apiId": "1234567890",
            "protocol": "HTTP/1.1"
        }
    }


if __name__ == '__main__':
    import argparse
    # Create the parser
    parser = argparse.ArgumentParser(description="Invoke lambda locally.")
    # Add the --command argument
    parser.add_argument('--command', choices=['migrate', 'webrequest'], required=True,
                        help="The command to execute. Choices are 'migrate' or 'webrequest'.")

    # Add the --path argument, but it's only required if the command is 'webrequest'
    parser.add_argument('--path', required=False,
                        help="The path to be used if the command is 'webrequest'. Required if --command is 'webrequest'.")
    # Parse the arguments
    args = parser.parse_args()

    # Check if the --command is 'webrequest' and validate the --path argument
    if args.command == 'webrequest' and args.path is None:
        parser.error("--path is required when --command is 'webrequest'")

    # Process the command
    if args.command == 'migrate':
        print("Executing migration...")
        lambda_handler({'command': 'migrate'}, {})
    elif args.command == 'webrequest':
        print(f"Processing web request for path: {args.path}")
        # Add your web request logic here
        print(lambda_handler(createSampleWeb(args.path), {}))
