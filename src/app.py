import json
import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs_client = boto3.client('sqs')
sns_client = boto3.client('sns')

SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')

def lambda_handler(event, context):
    """
    Triggered by SQS queue (polling invocation)
    Processes image upload messages and publishes to SNS
    """
    
    logger.info(f"Received event from SQS: {json.dumps(event)}")
    
    records = event.get('Records', [])
    
    for record in records:
        try:
            message_body = json.loads(record['body'])
            
            image_name = message_body['image_name']
            file_size = message_body['file_size']
            extension = message_body['file_extension']
            timestamp = message_body['timestamp']
            
            logger.info(f"Processing image upload: {image_name}")
            
            sns_message = f"""Image Upload Notification
========================

An image has been uploaded to the image repository.

Image Details:
- Name: {image_name}
- Size: {file_size} bytes ({file_size / 1024:.2f} KB)
- Extension: {extension}
- Uploaded: {timestamp}

Thank you for using our image upload service!"""
            
            sns_response = sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f'Image Upload: {image_name}',
                Message=sns_message,
                MessageAttributes={
                    'Extension': {
                        'DataType': 'String',
                        'StringValue': extension
                    }
                }
            )
            
            logger.info(f"Published SNS message: {sns_response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Processed {len(records)} messages')
    }