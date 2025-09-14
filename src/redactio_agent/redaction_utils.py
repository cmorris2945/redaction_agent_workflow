import boto3
import sys
from logger import get_logger
from custom_exception import CustomException

# Initialize logger
logger = get_logger(__name__)

comprehend = boto3.client('comprehend')

def redact_pii(record):
    """
    Redact PII from a record using Amazon Comprehend
    """
    try:
        # Make a copy of the record to avoid modifying the original
        processed_record = record.copy()
        text = record.get('sentence', '')
        
        logger.debug(f"Processing text: {text[:100]}..." if len(text) > 100 else text)
        
        if text:
            # Detect PII entities
            logger.debug("Calling Amazon Comprehend to detect PII")
            response = comprehend.detect_pii_entities(
                Text=text,
                LanguageCode='en'
            )
            
            pii_entities = response['Entities']
            logger.info(f"Found {len(pii_entities)} PII entities in text")
            
            # Log details of found PII entities
            for entity in pii_entities:
                logger.debug(f"PII Entity: {entity['Type']} at position {entity['BeginOffset']}-{entity['EndOffset']}")
            
            # Redact PII entities
            redacted_text = text
            for entity in sorted(pii_entities, key=lambda x: x['BeginOffset'], reverse=True):
                start = entity['BeginOffset']
                end = entity['EndOffset']
                redacted_text = redacted_text[:start] + '[REDACTED]' + redacted_text[end:]
            
            # Update the record with redacted text
            processed_record['sentence_redacted'] = redacted_text
            processed_record['original_sentence'] = text  # Keep original for reference
            processed_record['pii_types_found'] = [entity['Type'] for entity in pii_entities]
            del processed_record['sentence']  # Remove the original sentence
            
            logger.debug(f"Redacted text: {redacted_text}")
        
        return processed_record
        
    except Exception as e:
        error_msg = f"Error redacting PII: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Create a custom exception with detailed information
        custom_error = CustomException(error_msg, sys)
        logger.error(f"Custom error details: {str(custom_error)}")
        
        # Add error information to the record
        record['redaction_error'] = str(custom_error)
        return record  # Return original record if error occurs