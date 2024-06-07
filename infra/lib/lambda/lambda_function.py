import boto3
import os
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

dynamodb = boto3.client('dynamodb')
table_name = os.environ['TABLE_NAME']

def lambda_handler(event, context):
    logger.debug(f"Received event: {json.dumps(event)}")
    field_name = event['info']['fieldName']
    
    if field_name == 'getLatestVersion':
        return get_latest_version(event['arguments']['domainName'])
    elif field_name == 'updateVersion':
        return update_version(event['arguments']['domainName'], event['arguments']['s3Path'])
    else:
        logger.error(f"Unknown field name: {field_name}")
        return None

def get_latest_version(domain_name):
    try:
        response = dynamodb.query(
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
                'version': int(item['version']['N'])
            }
        else:
            logger.debug("No items found")
            return None
    except Exception as e:
        logger.error(f"Error querying DynamoDB: {str(e)}")
        raise

def update_version(domain_name, s3_path):
    try:
        # Get the latest version
        latest_version_info = get_latest_version(domain_name)
        new_version = (latest_version_info['version'] + 1) if latest_version_info else 1

        response = dynamodb.put_item(
            TableName=table_name,
            Item={
                'domainName': {'S': domain_name},
                's3Path': {'S': s3_path},
                'version': {'N': str(new_version)}  # Use a numeric value
            },
            ConditionExpression='attribute_not_exists(domainName) OR version < :new_version',
            ExpressionAttributeValues={
                ':new_version': {'N': str(new_version)}
            }
        )
        logger.debug(f"Updated version: {new_version} for domain: {domain_name}")
        return {
            'domainName': domain_name,
            's3Path': s3_path,
            'version': new_version
        }
    except dynamodb.exceptions.ConditionalCheckFailedException as e:
        logger.error(f"Version conflict: {str(e)}")
        raise Exception('Version conflict, try again.')
    except Exception as e:
        logger.error(f"Error updating DynamoDB: {str(e)}")
        raise