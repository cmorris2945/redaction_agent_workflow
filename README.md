# PII Redaction Agent. "I tried to organize this. Please look in all the appropriate directories to find directions, explanations, code/scripts and diagrams. You can even run this yourself but I tested this plenty of times."


A serverless AWS-based system for automatically detecting and redacting Personally Identifiable Information (PII) from JSON verbatim data using AWS Comprehend, Lambda, and S3. 


## 🎯 Overview

This system automatically processes JSON files uploaded to S3, detects PII using AWS Comprehend, redacts sensitive information, and saves clean data to a separate bucket.

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/a764dfd4-a09e-4778-9513-24193d839cb8" />



**Supported PII Types:**
- Names (PERSON)
- Email addresses (EMAIL)
- Phone numbers (PHONE)
- Addresses (ADDRESS)

## 🚀 Quick Start

### 1. Clone and Configure
```bash
git clone my repot here....  https://github.com/cmorris2945/redaction_agent_workflow.git
cd into this directory.... redactio_agent
aws configure  # Enter your own AWS credentials. I did not give anyone access to mine.
```

### 2. Deploy with One Command
```bash
./quick-setup.sh
```

### 3. Test It Works
```bash
# Create test file
echo '[{"sentence": "Call John Smith at 555-1234"}]' > test.json

# Upload (triggers processing)
aws s3 cp test.json s3://your-raw-bucket/raw/2025/09/14/test.json        ### put your approporiate name in here.

# Check results
aws s3 cp s3://your-clean-bucket/clean/2025/09/14/test.json result.json    #### same with this. Put your clean bucket name in here.
cat result.json
```
