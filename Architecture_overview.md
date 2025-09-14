New-Item -Path "ARCHITECTURE.md" -ItemType File -Value @"
# Architecture Design

## Data Flow
\`\`\`
1. Voice metadata JSON files → S3 Raw Bucket (s3://voice-metadata-raw/YYYY/MM/DD/)
2. S3 Event Notification → Lambda Trigger
3. Lambda Function:
   a. Read JSON file from S3
   b. Parse ~15,000 payloads
   c. Send sentences to Amazon Comprehend
   d. Receive PII entities
   e. Redact PII from sentences
   f. Write sanitized JSON to S3 Clean Bucket
4. S3 Clean Bucket → Analytics/ML Pipelines
5. CloudWatch → Monitoring & Alerts
\`\`\`

## Components

### Storage Layer
- **S3 Raw Bucket**: Partitioned by date (YYYY/MM/DD)
- **S3 Clean Bucket**: Sanitized data with same partitioning

### Processing Layer
- **Lambda Function**: 3GB memory, 15-minute timeout
- **Batch Processing**: Process payloads in chunks of 25

### ML Services
- **Amazon Comprehend**: DetectPiiEntities API

### Monitoring
- **CloudWatch Logs**: Application logs
- **CloudWatch Metrics**: Processing time, error rates
- **SNS**: Alert notifications

## Security
- **Encryption**: S3 SSE-S3, Lambda environment variables
- **IAM Roles**: Least privilege access
- **VPC**: Optional for enhanced security
"@