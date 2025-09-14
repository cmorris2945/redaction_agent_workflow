"""
PII Redaction Lambda Function for Voice Call Metadata
"""
import json
import boto3
import os
from typing import Dict, List, Any
from datetime import datetime
import logging
from botocore.exceptions import ClientError

# Initialize AWS clients
s3_client = boto3.client('s3')
comprehend_client = boto3.client('comprehend')

# Environment variables
RAW_BUCKET = os.environ.get('S3_RAW_BUCKET', 'chrisbucketraw')
CLEAN_BUCKET = os.environ.get('S3_CLEAN_BUCKET', 'chrisbucketclean')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '25'))

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# PII entity types to redact
PII_ENTITIES = [
    'NAME', 'ADDRESS', 'EMAIL', 'PHONE', 'SSN', 
    'DATE_TIME', 'CREDIT_DEBIT_NUMBER', 'PIN', 'AWS_ACCESS_KEY',
    'AWS_SECRET_KEY', 'IP_ADDRESS', 'MAC_ADDRESS', 'LICENSE_PLATE',
    'VEHICLE_IDENTIFICATION_NUMBER', 'UK_NATIONAL_INSURANCE_NUMBER',
    'BANK_ACCOUNT_NUMBER', 'BANK_ROUTING', 'PASSPORT_NUMBER',
    'DRIVER_ID', 'TAXPAYER_IDENTIFICATION_NUMBER'
]

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for PII redaction
    """
    try:
        # Extract S3 event details
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            logger.info(f"Processing file: s3://{bucket}/{key}")
            
            # Process the file
            result = process_file(bucket, key)
            
            logger.info(f"Successfully processed {result['payloads_processed']} payloads")
            
        return {
            'statusCode': 200,
            'body': json.dumps('Processing completed successfully')
        }
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise

def process_file(bucket: str, key: str) -> Dict[str, Any]:
    """
    Process a single JSON file for PII redaction
    """
    # Read file from S3
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = json.loads(response['Body'].read())
    except ClientError as e:
        logger.error(f"Error reading file from S3: {e}")
        raise
    
    # Process payloads
    if isinstance(content, list):
        payloads = content
    elif isinstance(content, dict) and 'payloads' in content:
        payloads = content['payloads']
    else:
        payloads = [content]
    
    # Redact PII from payloads in batches
    sanitized_payloads = []
    for i in range(0, len(payloads), BATCH_SIZE):
        batch = payloads[i:i + BATCH_SIZE]
        sanitized_batch = process_batch(batch)
        sanitized_payloads.extend(sanitized_batch)
    
    # Save sanitized data to clean bucket
    clean_key = key.replace('raw/', 'clean/')
    save_to_s3(CLEAN_BUCKET, clean_key, sanitized_payloads)
    
    return {
        'payloads_processed': len(payloads),
        'output_location': f"s3://{CLEAN_BUCKET}/{clean_key}"
    }

def process_batch(payloads: List[Dict]) -> List[Dict]:
    """
    Process a batch of payloads for PII redaction
    """
    sanitized_payloads = []
    
    for payload in payloads:
        if 'sentence' in payload and payload['sentence']:
            # Detect PII
            pii_entities = detect_pii(payload['sentence'])
            
            # Redact PII
            sanitized_sentence = redact_pii(payload['sentence'], pii_entities)
            
            # Create sanitized payload
            sanitized_payload = payload.copy()
            sanitized_payload['sentence'] = sanitized_sentence
            sanitized_payload['pii_detected'] = len(pii_entities) > 0
            sanitized_payload['pii_types'] = list(set([e['Type'] for e in pii_entities]))
            sanitized_payload['processed_timestamp'] = datetime.utcnow().isoformat()
            
            sanitized_payloads.append(sanitized_payload)
        else:
            sanitized_payloads.append(payload)
    
    return sanitized_payloads

def detect_pii(text: str) -> List[Dict]:
    """
    Detect PII entities using Amazon Comprehend
    """
    try:
        response = comprehend_client.detect_pii_entities(
            Text=text,
            LanguageCode='en'
        )
        return response.get('Entities', [])
    except ClientError as e:
        logger.error(f"Error detecting PII: {e}")
        return []

def redact_pii(text: str, entities: List[Dict]) -> str:
    """
    Redact PII entities from text
    """
    if not entities:
        return text
    
    # Sort entities by position (reverse order to maintain positions)
    entities_sorted = sorted(entities, key=lambda x: x['BeginOffset'], reverse=True)
    
    redacted_text = text
    for entity in entities_sorted:
        if entity['Type'] in PII_ENTITIES:
            start = entity['BeginOffset']
            end = entity['EndOffset']
            redaction = f"[{entity['Type']}]"
            redacted_text = redacted_text[:start] + redaction + redacted_text[end:]
    
    return redacted_text

def save_to_s3(bucket: str, key: str, data: List[Dict]) -> None:
    """
    Save processed data to S3
    """
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        logger.info(f"Saved sanitized data to s3://{bucket}/{key}")
    except ClientError as e:
        logger.error(f"Error saving to S3: {e}")
        raise