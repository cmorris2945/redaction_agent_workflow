# Technology Justification

## Overview
I chose a serverless, AWS-native design to meet the goals of low ops overhead, fast time-to-value, and strong security controls for PII handling.  
This stack is event-driven, scales automatically with incoming files, and aligns with a data collection and feature pipeline focus without overbuilding orchestration or MLOps layers we don't need yet.

## AWS Lambda
**Why:**
- Serverless compute eliminates infrastructure management and idle cost
- Auto-scales with S3 event notifications; concurrency can be raised if needed
- Pay-per-use pricing; no always-on cluster to maintain
- 15-minute timeout is sufficient for our per-file processing (15k payloads) with batching

**Notes:**
- Concurrency and external API quotas (Comprehend) are the real throughput limiters
- If files grow substantially, Step Functions or chunking would be added

## Amazon S3
**Why:**
- Native event notifications to trigger Lambda on object creation
- Durable, cheap storage for raw and clean JSON with predictable partitions (YYYY/MM/DD)
- Lifecycle policies for retention and cost controls (Standard → IA/Glacier)
- Server-side encryption by default (SSE-S3); can be upgraded to SSE-KMS

**Notes:**
- Bucket policies enforce TLS in transit and can require encryption at rest

## Amazon Comprehend (PII)
**Why:**
- Managed, pre-trained PII detection covering 20+ entity types out-of-the-box
- No model training, feature engineering, or model ops required
- Tight IAM, logging, and regional controls; straightforward to integrate from Lambda

**What I'm not claiming:**
- I'm not asserting a blanket ">95% accuracy." Comprehend is a strong baseline for English PII, but accuracy should be validated on our domain data. In their documentation they say it provides "high accuracy".

**When I would augment:**
- Domain-specific entities (internal IDs) → add regex/Presidio/custom recognizers
- Multilingual content → language detection or alternate provider; validate performance
- Throughput spikes → add retry, backoff, and possibly SQS between S3 and Lambda

## Amazon CloudWatch
**Why:**
- Native logs for Lambda stdout/stderr, metrics, and alarms
- Near real-time operational visibility (errors, durations, throttles)
- Can wire alarms to SNS for notifications

**Enhancements:**
- Custom metrics (e.g., payloads processed, PII types count) for KPIs and SLOs

## AWS IAM and Encryption (Security)
**Why:**
- Least-privilege IAM roles: Lambda can Get from raw, Put to clean, call Comprehend
- Encryption in transit (TLS) and at rest (SSE-S3; optional SSE-KMS with CMKs)
- CloudTrail audit of API calls for compliance and forensics

**Optional hardening:**
- SSE-KMS with customer-managed keys and scoped key policies
- VPC endpoints for S3/CloudWatch to keep traffic on AWS backbone
- S3 Block Public Access on both buckets; bucket policies to require encryption

## Alternative Considerations

### Why not Apache Airflow?
- This is just a simple test. I uploaded the json payload manually. But Airflow excels at complex, scheduled DAGs; our flow is simple and event-driven
- Requires managing scheduler/webserver/workers, upgrades, and HA
- Higher operational cost and latency (polling/schedules) than direct S3→Lambda triggers that I did manually.

**When I would choose it:**
- Multi-step batch DAGs, dependencies, backfills, SLAs, and rich orchestration
- Existing team expertise and an Airflow platform already in place

### Why not Amazon Textract?
- Textract is for extracting text from documents/imagery
- We already have text; PII detection is the need. Comprehend is the right tool

### Why not custom scripts or open-source NER (spaCy/HF) or Microsoft Presidio?
- Faster time-to-value using a managed PII detector; no model ops or labeling up front
- Custom models/rules require data annotation, evaluation, deployment, and monitoring

**When I would choose/augment:**
- Deterministic formats (account numbers, internal IDs) → regex/Presidio custom recognizers
- Domain-specific recall/precision targets → fine-tuned transformer behind an endpoint
- Vendor lock-in concerns → abstraction layer to swap detectors, A/B compare providers

## Assumptions and Limits
- **Language:** Optimized for English; multilingual support requires validation
- **Throughput:** Constrained by Comprehend TPS/quotas; mitigated via batching, retries, and quota increases
- **File size:** Single-Lambda processing; Step Functions/partitioning if files become very large
- **Accuracy:** Depends on vendor model and domain; measure on our data and augment as needed


## Poetry
**Why I used it:**
- **Dependency Management:** Clean separation of production vs. dev dependencies
- **Virtual Environment:** Automatic venv creation and management with `poetry shell`
- **Lock Files:** `poetry.lock` ensures reproducible builds across environments
- **Modern Python Packaging:** Uses pyproject.toml standard with Poetry's enhanced features
- **Development Workflow:** Easy dependency updates with `poetry update`

## References
- [Amazon Comprehend PII entities](https://docs.aws.amazon.com/comprehend/latest/dg/pii.html)
- [Amazon Comprehend pricing](https://aws.amazon.com/comprehend/pricing/)
- [AWS Lambda docs](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [Lambda pricing](https://aws.amazon.com/lambda/pricing/)
- [Amazon S3 event notifications](https://docs.aws.amazon.com/AmazonS3/latest/dev/NotificationHowTo.html)
- [CloudWatch logs/metrics/alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)

This stack lets me deliver a secure, event-driven redaction pipeline quickly, with clear upgrade paths if requirements evolve (SQS/Step Functions for orchestration, KMS for tighter key control, custom detectors for domain entities, and Airflow/ZenML if we later add complex training or batch DAGs).