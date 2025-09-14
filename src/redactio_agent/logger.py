import logging
import os
from datetime import datetime

# For Lambda environment, we don't want to create local log files
# Instead, we'll use CloudWatch for logging
if not os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    # We're running locally, so create log files
    LOGS_DIR = "logs"
    os.makedirs(LOGS_DIR, exist_ok=True)
    LOG_FILE = os.path.join(LOGS_DIR, f"log_{datetime.now().strftime('%Y-%m-%d')}.log")
    
    logging.basicConfig(
        filename=LOG_FILE,
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
else:
    # We're running in AWS Lambda, use standard logging to CloudWatch
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

def get_logger(name):
    """Get a logger instance with the given name"""
    logger = logging.getLogger(name)
    
    # Set level based on environment variable or default to INFO
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    return logger