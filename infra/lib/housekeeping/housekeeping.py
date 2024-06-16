import boto3
import os
from botocore.exceptions import ClientError
import logging

dynamodb_client = boto3.client('dynamodb')
s3_client = boto3.client('s3')
table_name = os.environ['TABLE_NAME']
bucket_name = os.environ['BUCKET_NAME']


logger = logging.getLogger()
logger.setLevel("INFO")


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


def purge_old_versions(upto_version: str) -> dict:
    try:
        result = s3_client.list_object_versions(
            Bucket=bucket_name, Prefix='db.sqlite3')
        num_to_keep = 10
        num_kept = 0
        delete_versions = []
        for version in result['Versions']:
            if version['IsLatest'] or version['VersionId'] == upto_version:
                print('Retaining' + str(version))
            else:
                if num_kept < num_to_keep:
                    print('Retaining' + str(version))
                    num_kept = num_kept + 1
                else:
                    print('Deleting' + str(version))
                    delete_versions.append(
                        {'Key': version['Key'], 'VersionId': version['VersionId']})

        if delete_versions:
            print('Deleting versions:', delete_versions)
            delete_response = s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': delete_versions}
            )
            print('Delete response:', delete_response)
        else:
            print('No versions to delete.')

    except ClientError as e:
        raise Exception(
            "boto3 client error in list_all_objects_version function: " + e.__str__())
    except Exception as e:
        raise Exception(
            "Unexpected error in list_all_objects_version function of s3 helper: " + e.__str__())

    return


def handler(event, context):
    latest = get_latest_version('example.com')
    print(latest)
    purge_old_versions(latest['s3VersionId'])
    pass


if __name__ == '__main__':
    # for running locally - pipenv run python.... bla bla bla
    handler({}, {})
