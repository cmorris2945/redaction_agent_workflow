import json
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from custom_exception import CustomException
from redaction_utils import redact_pii

# Initialize Powertools
logger = Logger(service="pii-redaction")
tracer = Tracer(service="pii-redaction")

s3 = boto3.client('s3')

@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict, context: LambdaContext):
    try:
        logger.info("Lambda function execution started")
        
        # Get the bucket and key from the S3 event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        logger.info(f"Processing file: {bucket}/{key}")
        
        # Only process files in the raw/ prefix
        if not key.startswith('raw/'):
            logger.warning(f"Skipping file not in raw/ prefix: {key}")
            return {'statusCode': 200, 'body': 'Skipped - not in raw folder'}
        
        # Download the file from S3
        logger.info(f"Downloading file from S3: {bucket}/{key}")
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        data = json.loads(content)
        
        logger.info(f"Successfully downloaded and parsed {len(data)} records")
        
        # Process each record
        processed_data = []
        success_count = 0
        error_count = 0
        
        for i, record in enumerate(data):
            try:
                logger.debug(f"Processing record {i+1}: {record.get('verbatim_id', 'unknown')}")
                processed_record = redact_pii(record)
                processed_data.append(processed_record)
                success_count += 1
            except Exception as e:
                logger.error(f"Error processing record {i+1}: {str(e)}")
                error_count += 1
                # Add the original record with error flag
                record['processing_error'] = str(e)
                processed_data.append(record)
        
        logger.info(f"Record processing completed: {success_count} successful, {error_count} failed")
        
        # Upload processed data to clean bucket
        clean_bucket = 'your-clean-bucket-name'  # Replace with your clean bucket name
        clean_key = key.replace('raw/', 'clean/')
        
        logger.info(f"Uploading processed data to: {clean_bucket}/{clean_key}")
        s3.put_object(
            Bucket=clean_bucket,
            Key=clean_key,
            Body=json.dumps(processed_data),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        logger.info(f"Successfully processed and uploaded {len(processed_data)} records to: {clean_bucket}/{clean_key}")
        
        # Return summary of processing
        return {
            'statusCode': 200, 
            'body': json.dumps({
                'message': 'Processing completed successfully',
                'processed_records': len(processed_data),
                'successful': success_count,
                'failed': error_count,
                'output_location': f"{clean_bucket}/{clean_key}"
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return {
            'statusCode': 500, 
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process file'
            })
        }