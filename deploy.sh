#!/bin/bash

# Configuration
LAMBDA_FUNCTION_NAME="pii-redaction-function"
S3_RAW_BUCKET="your-raw-bucket-name"
S3_CLEAN_BUCKET="your-clean-bucket-name"
LAMBDA_ROLE_NAME="lambda-s3-comprehend-role"
ZIP_FILE="lambda_deployment.zip"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is not installed. Please install it first:"
    echo "curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Install dependencies using Poetry
echo "Installing dependencies with Poetry..."
poetry install --only main

# Create deployment package
echo "Creating deployment package..."
poetry run python -m pip install --upgrade pip
poetry export --only main -f requirements.txt --output requirements.txt
poetry run pip install -r requirements.txt --target ./package

echo "Packaging Lambda function..."
cd package
zip -r ../$ZIP_FILE .
cd ..
zip -g $ZIP_FILE -r src

# Create IAM role for Lambda if it doesn't exist
echo "Creating IAM role..."
if ! aws iam get-role --role-name $LAMBDA_ROLE_NAME &> /dev/null; then
    aws iam create-role \
        --role-name $LAMBDA_ROLE_NAME \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }'

    # Attach policies to the role
    echo "Attaching policies..."
    aws iam attach-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
        
    aws iam attach-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/ComprehendFullAccess
        
    aws iam attach-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
fi

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text)

# Create or update Lambda function
echo "Deploying Lambda function..."
if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME &> /dev/null; then
    # Update existing function
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --zip-file fileb://$ZIP_FILE
        
    aws lambda update-function-configuration \
        --function-name $LAMBDA_FUNCTION_NAME \
        --environment "Variables={LOG_LEVEL=INFO}"
else
    # Create new function
    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --runtime python3.9 \
        --role $ROLE_ARN \
        --handler src/lambda_function.lambda_handler \
        --zip-file fileb://$ZIP_FILE \
        --timeout 30 \
        --memory-size 128 \
        --environment "Variables={LOG_LEVEL=INFO}"
fi

# Add S3 trigger to Lambda function
echo "Configuring S3 trigger..."
aws lambda add-permission \
    --function-name $LAMBDA_FUNCTION_NAME \
    --action lambda:InvokeFunction \
    --principal s3.amazonaws.com \
    --source-arn arn:aws:s3:::$S3_RAW_BUCKET \
    --statement-id s3-trigger

# Configure S3 to trigger Lambda
echo "Configuring S3 trigger..."
aws s3api put-bucket-notification-configuration \
    --bucket $S3_RAW_BUCKET \
    --notification-configuration '{
        "LambdaFunctionConfigurations": [
            {
                "LambdaFunctionArn": "'$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --query 'Configuration.FunctionArn' --output text)'",
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {
                        "FilterRules": [
                            {
                                "Name": "prefix",
                                "Value": "raw/"
                            }
                        ]
                    }
                }
            }
        ]
    }'

echo "Deployment completed!"
echo "Clean up deployment package..."
rm -f $ZIP_FILE
rm -rf package
rm -f requirements.txt

echo "To test the function:"
echo "aws s3 cp test_data.json s3://$S3_RAW_BUCKET/raw/test.json"