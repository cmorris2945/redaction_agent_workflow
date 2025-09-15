#!/bin/bash
echo "Chris Morris's PII Redaction System - Complete Setup"
echo "=================================================="
echo ""
echo "WARNING: Before you run my script, you NEED these things:"
echo "   1. AWS CLI installed and configured (run 'aws configure' first)"
echo "   2. An AWS account with S3, Lambda, IAM, and Comprehend permissions"
echo "   3. Git and Bash/Terminal access"
echo ""
echo "   If you don't have these, my script WILL FAIL!"
echo "   Go set them up first, then come back."
echo ""
read -p "Got all that? Press Enter to continue or Ctrl+C to bail out..."
echo ""

# Get user's AWS account ID
echo "Checking your AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "ERROR: Your AWS CLI isn't configured properly!"
    echo "   Run 'aws configure' first, then try my script again."
    exit 1
fi

echo "Your AWS Account: $ACCOUNT_ID"
echo "   (If this looks wrong, you can't proceed - fix your AWS config first!)"

# Set unique bucket names (so you don't conflict with mine or others)
RAW_BUCKET="chris-pii-raw-${ACCOUNT_ID}-$(date +%s)"
CLEAN_BUCKET="chris-pii-clean-${ACCOUNT_ID}-$(date +%s)"

echo ""
echo "Creating YOUR S3 buckets (I'm making them unique so you don't clash with mine)..."
aws s3 mb s3://$RAW_BUCKET --region us-east-2
aws s3 mb s3://$CLEAN_BUCKET --region us-east-2

if [ $? -ne 0 ]; then
    echo "ERROR: Couldn't create S3 buckets! You probably don't have S3 permissions."
    echo "   Ask your AWS admin to give you S3 access, then try again."
    exit 1
fi

echo "Creating IAM role and policies (this is where my system gets its permissions)..."
aws iam create-role --role-name ChrisPiiRedactionLambdaRole \
  --assume-role-policy-document file://lambda-trust-policy.json

aws iam create-policy --policy-name ChrisPiiRedactionLambdaPolicy \
  --policy-document file://lambda-execution-policy.json

aws iam attach-role-policy --role-name ChrisPiiRedactionLambdaRole \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/ChrisPiiRedactionLambdaPolicy

aws iam attach-role-policy --role-name ChrisPiiRedactionLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

if [ $? -ne 0 ]; then
    echo "ERROR: IAM setup failed! You can't create roles/policies."
    echo "   You need IAM admin permissions to run my script."
    exit 1
fi

echo "Waiting for IAM role to propagate (AWS is slow sometimes, you can't rush this)..."
sleep 15

echo "Creating my Lambda deployment package..."
mkdir -p lambda-deployment
cp src/redactio_agent/lambda_function.py lambda-deployment/
cd lambda-deployment && zip -r ../lambda-deployment.zip . && cd ..

echo "Deploying my Lambda function to YOUR AWS account..."
aws lambda create-function \
  --function-name chris-pii-redaction-function \
  --runtime python3.9 \
  --role arn:aws:iam::$ACCOUNT_ID:role/ChrisPiiRedactionLambdaRole \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 900 \
  --memory-size 3008 \
  --environment Variables="{S3_RAW_BUCKET=$RAW_BUCKET,S3_CLEAN_BUCKET=$CLEAN_BUCKET}" \
  --region us-east-2

if [ $? -ne 0 ]; then
    echo "ERROR: Lambda deployment failed! You might not have Lambda permissions."
    echo "   Or maybe you already ran my script before? Check the AWS console."
    exit 1
fi

echo "Setting up S3 trigger (this is the magic that makes everything automatic)..."
aws lambda add-permission \
  --function-name chris-pii-redaction-function \
  --statement-id s3-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::$RAW_BUCKET \
  --region us-east-2

# Update S3 event configuration with your actual values
sed "s/YOUR_ACCOUNT_ID/$ACCOUNT_ID/g" s3-event-configuration.json > temp-s3-config.json
sed "s/your-raw-bucket-name/$RAW_BUCKET/g" temp-s3-config.json > final-s3-config.json

aws s3api put-bucket-notification-configuration \
  --bucket $RAW_BUCKET \
  --notification-configuration file://final-s3-config.json \
  --region us-east-2

echo ""
echo "SUCCESS! My PII Redaction System is now running in YOUR AWS account!"
echo "================================================================="
echo "Here's what I built for you:"
echo "   Raw Bucket: s3://$RAW_BUCKET"
echo "   Clean Bucket: s3://$CLEAN_BUCKET"
echo "   Lambda Function: chris-pii-redaction-function"
echo "   Region: us-east-2"
echo ""
echo "You can test it right now:"
echo "   aws s3 cp test-payload.json s3://$RAW_BUCKET/raw/2025/09/14/demo.json --region us-east-2"
echo "   sleep 15"
echo "   aws s3 cp s3://$CLEAN_BUCKET/clean/2025/09/14/demo.json result.json --region us-east-2"
echo "   cat result.json"
echo ""
echo "Pro tip: You can run this demo as many times as you want!"
echo "   Just change the filename each time so you don't overwrite."
echo ""
echo "Built by Chris Morris - Software Engineer"
echo "This system processes 450K-900K records/day in production!"

# Cleanup temp files if you want here...
rm -f temp-s3-config.json final-s3-config.json lambda-deployment.zip
rm -rf lambda-deployment

echo ""
echo "Complete."