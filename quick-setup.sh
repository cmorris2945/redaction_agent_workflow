  --statement-id s3-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::$RAW_BUCKET \
  --region us-east-2

# Update S3 event configuration with actual values
sed "s/YOUR_ACCOUNT_ID/$ACCOUNT_ID/g" s3-event-configuration.json > temp-s3-config.json
sed "s/your-raw-bucket-name/$RAW_BUCKET/g" temp-s3-config.json > final-s3-config.json

aws s3api put-bucket-notification-configuration \
  --bucket $RAW_BUCKET \
  --notification-configuration file://final-s3-config.json \
  --region us-east-2

echo "✅ Setup complete!"
echo "📋 Summary:"
echo "   Raw Bucket: s3://$RAW_BUCKET"
echo "   Clean Bucket: s3://$CLEAN_BUCKET"
echo "   Lambda Function: pii-redaction-function"
echo "   Region: us-east-2"
echo ""
echo "🧪 Test your system:"
echo "   aws s3 cp test-file.json s3://$RAW_BUCKET/raw/2025/09/14/test-file.json"

# Cleanup temp files
rm -f temp-s3-config.json final-s3-config.json
