New-Item -Path "ARCHITECTURE_DIAGRAM.md" -ItemType File -Value @"
# PII Redaction Architecture Diagram

## System Architecture

\`\`\`
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    AWS Cloud (us-east-1)                             │
│                                                                                       │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                                  Data Flow                                    │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                       │
│     ┌─────────────┐                                                                  │
│     │   Voice     │                                                                  │
│     │  Metadata   │                                                                  │
│     │ JSON Files  │                                                                  │
│     └──────┬──────┘                                                                  │
│            │                                                                          │
│            │ Upload                                                                   │
│            ▼                                                                          │
│  ┌─────────────────────┐         S3 Event          ┌─────────────────────┐          │
│  │                     │         Trigger           │                     │          │
│  │   S3 Raw Bucket     │─────────────────────────▶│   Lambda Function   │          │
│  │                     │                           │                     │          │
│  │ /raw/YYYY/MM/DD/    │                           │   - Read JSON       │          │
│  │                     │                           │   - Parse Payloads  │          │
│  │ ┌─────────────────┐ │                           │   - Detect PII      │          │
│  │ │  JSON Files     │ │                           │   - Redact Data     │          │
│  │ │  ~30-60/day     │ │◀──────────────┐          │   - Write Clean     │          │
│  │ │  ~15K payloads  │ │     Read      │          │                     │          │
│  │ └─────────────────┘ │               │          │   Memory: 3GB       │          │
│  └─────────────────────┘               │          │   Timeout: 15min    │          │
│                                         │          └──────────┬──────────┘          │
│                                         │                     │                      │
│                                         │                     │ API Calls            │
│                                         │                     ▼                      │
│                                         │          ┌─────────────────────┐          │
│                                         │          │                     │          │
│                                         └──────────│  Amazon Comprehend  │          │
│                                                    │                     │          │
│                                                    │  DetectPiiEntities  │          │
│                                                    │                     │          │
│                                                    │  - Names            │          │
│                                                    │  - Addresses        │          │
│                                                    │  - Emails           │          │
│                                                    │  - Phone Numbers    │          │
│                                                    │  - SSN              │          │
│                                                    └─────────────────────┘          │
│                                                                                       │
│            │                                                   │                      │
│            │ Write                                            │                      │
│            ▼                                                   │                      │
│  ┌─────────────────────┐                                     │                      │
│  │                     │                                     │                      │
│  │  S3 Clean Bucket    │                                     │ Logs & Metrics       │
│  │                     │                                     ▼                      │
│  │ /clean/YYYY/MM/DD/  │                          ┌─────────────────────┐          │
│  │                     │                          │                     │          │
│  │ ┌─────────────────┐ │                          │    CloudWatch       │          │
│  │ │ Sanitized JSON  │ │                          │                     │          │
│  │ │ PII Redacted    │ │                          │  - Application Logs │          │
│  │ │ Analytics Ready │ │                          │  - Metrics          │          │
│  │ └─────────────────┘ │                          │  - Alarms           │          │
│  └──────────┬──────────┘                          └──────────┬──────────┘          │
│             │                                                 │                      │
│             │                                                 │ Alerts               │
│             ▼                                                 ▼                      │
│  ┌─────────────────────┐                          ┌─────────────────────┐          │
│  │                     │                          │                     │          │
│  │  Analytics/ML       │                          │        SNS          │          │
│  │    Pipelines        │                          │                     │          │
│  │                     │                          │   Email/SMS Alerts  │          │
│  │ - Natural Language  │                          │                     │          │
│  │ - Insights Gen      │                          └─────────────────────┘          │
│  │ - Reporting         │                                                            │
│  └─────────────────────┘                                                            │
│                                                                                       │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                              Security & Governance                            │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                       │
│    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│    │              │    │              │    │              │    │              │   │
│    │   IAM Roles  │    │   KMS Keys   │    │  CloudTrail  │    │   S3 SSE     │   │
│    │              │    │              │    │              │    │              │   │
│    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
\`\`\`

## Data Processing Flow

\`\`\`
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│              │      │              │      │              │      │              │
│  Raw JSON    │─────▶│   Lambda     │─────▶│  Comprehend  │─────▶│ Clean JSON   │
│   Upload     │      │   Trigger    │      │   PII Scan   │      │   Storage    │
│              │      │              │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘
       │                     │                      │                      │
       │                     │                      │                      │
       ▼                     ▼                      ▼                      ▼
  [S3 Event]          [Read & Parse]         [Detect Entities]      [Save to S3]
                           15K                  Batch of 25          Sanitized
                         Payloads                Sentences             Data
\`\`\`

## Component Details

\`\`\`
┌─────────────────────────────────────────────────────────────────┐
│                      Lambda Function Details                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Environment Variables:                                          │
│  ├─ S3_RAW_BUCKET: voice-metadata-raw                          │
│  ├─ S3_CLEAN_BUCKET: voice-metadata-clean                      │
│  ├─ BATCH_SIZE: 25                                             │
│  └─ LOG_LEVEL: INFO                                            │
│                                                                  │
│  IAM Permissions:                                               │
│  ├─ s3:GetObject (Raw Bucket)                                  │
│  ├─ s3:PutObject (Clean Bucket)                                │
│  ├─ comprehend:DetectPiiEntities                               │
│  └─ logs:CreateLogGroup, PutLogEvents                          │
│                                                                  │
│  Processing Logic:                                              │
│  1. Receive S3 event notification                              │
│  2. Download JSON file from S3                                 │
│  3. Parse JSON payloads (15,000 per file)                     │
│  4. For each batch of 25 payloads:                            │
│     a. Extract sentences                                       │
│     b. Call Comprehend DetectPiiEntities                      │
│     c. Replace PII with [ENTITY_TYPE] tokens                  │
│  5. Save sanitized JSON to Clean Bucket                       │
│  6. Log metrics to CloudWatch                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
\`\`\`

## PII Entity Types Detected and Redacted

\`\`\`
┌────────────────────┬────────────────────┬────────────────────┐
│   Personal Info    │   Contact Info     │   Financial Info   │
├────────────────────┼────────────────────┼────────────────────┤
│ • NAME             │ • EMAIL            │ • CREDIT_CARD      │
│ • SSN              │ • PHONE            │ • BANK_ACCOUNT     │
│ • DATE_OF_BIRTH    │ • ADDRESS          │ • BANK_ROUTING     │
│ • DRIVER_LICENSE   │ • IP_ADDRESS       │ • PIN              │
│ • PASSPORT_NUMBER  │ • MAC_ADDRESS      │                    │
└────────────────────┴────────────────────┴────────────────────┘
\`\`\`

## Sample Data Transformation

\`\`\`
Input (Raw):
{
  "sentence": "John Smith lives at 123 Main St, NY 10001. Call 555-1234."
}

                    ↓ PII Detection & Redaction ↓

Output (Sanitized):
{
  "sentence": "[NAME] lives at [ADDRESS]. Call [PHONE].",
  "pii_detected": true,
  "pii_types": ["NAME", "ADDRESS", "PHONE"],
  "processed_timestamp": "2025-09-14T10:30:00Z"
}
\`\`\`

## Monitoring Dashboard

\`\`\`
┌─────────────────────────────────────────────────────────────────┐
│                     CloudWatch Dashboard                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  Files Processed     │  │  Payloads Processed  │            │
│  │  ████████████ 45/60  │  │  ████████ 675K/900K  │            │
│  └──────────────────────┘  └──────────────────────┘            │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  Avg Process Time    │  │  PII Detection Rate  │            │
│  │      3.2 min/file    │  │        87.3%         │            │
│  └──────────────────────┘  └──────────────────────┘            │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │  Error Rate          ▁▁▁▁▂▁▁▁▁▁▁▁▁▁▁▁▁▁         │          │
│  │  Lambda Duration     ████████████████████         │          │
│  │  Comprehend Calls    ▆▆▆▆▇▇▇▇▆▆▆▆▆▆▆▆           │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
│  Alarms:                                                        │
│  • ⚠️ High Error Rate (>1%)                                     │
│  • ⚠️ Processing Time (>5 min)                                  │
│  • ⚠️ Failed Invocations                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
\`\`\`

## Cost Breakdown (Estimated Monthly)

\`\`\`
┌────────────────────────────────────────────────────────────┐
│ Service          │ Usage                │ Cost            │
├──────────────────┼──────────────────────┼─────────────────┤
│ Lambda           │ 1,800 invocations    │ $15.00          │
│                  │ 5,400 GB-seconds     │                 │
├──────────────────┼──────────────────────┼─────────────────┤
│ S3               │ 10 GB storage        │ $0.23           │
│                  │ 100K requests        │ $0.40           │
├──────────────────┼──────────────────────┼─────────────────┤
│ Comprehend       │ 27M units            │ $54.00          │
│                  │ (900K payloads/day)  │                 │
├──────────────────┼──────────────────────┼─────────────────┤
│ CloudWatch       │ Logs & Metrics       │ $5.00           │
├──────────────────┼──────────────────────┼─────────────────┤
│ Total            │                      │ ~$74.63/month   │
└────────────────────────────────────────────────────────────┘
\`\`\`
"@