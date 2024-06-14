import json
import urllib3
import boto3
import os

http = urllib3.PoolManager()
codepipeline = boto3.client('codepipeline')

def handler(event, context):
    # Check if the function is triggered by CodePipeline
    is_codepipeline_triggered = 'CodePipeline.job' in event
    
    if is_codepipeline_triggered:
        job_id = event['CodePipeline.job']['id']
        api_endpoint = os.environ['API_ENDPOINT']
    else:
        # When triggered manually, extract the API_ENDPOINT from the environment variable or the event
        api_endpoint = os.environ.get('API_ENDPOINT') or event.get('api_endpoint')
        job_id = None

    try:
        response = http.request('POST', api_endpoint + '/migrate/')
        if response.status == 200:
            if is_codepipeline_triggered:
                put_job_success(job_id, "Migrations completed successfully.")
            else:
                print("Migrations completed successfully.")
        else:
            if is_codepipeline_triggered:
                put_job_failure(job_id, f"Migrations failed with status code: {response.status}")
            else:
                print(f"Migrations failed with status code: {response.status}")
    except Exception as e:
        if is_codepipeline_triggered:
            put_job_failure(job_id, str(e))
        else:
            print(f"Error: {str(e)}")

def put_job_success(job_id, message):
    codepipeline.put_job_success_result(jobId=job_id)
    print(f'Successfully put job success: {message}')

def put_job_failure(job_id, message):
    codepipeline.put_job_failure_result(
        jobId=job_id,
        failureDetails={
            'message': message,
            'type': 'JobFailed',
            'externalExecutionId': context.awsRequestId
        }
    )
    print(f'Failed to put job success: {message}')
