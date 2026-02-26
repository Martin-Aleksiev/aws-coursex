from flask import Flask, jsonify, request, send_file
import boto3
from botocore.exceptions import ClientError
import logging
import pymysql
import os
from io import BytesIO
import random
import json
from datetime import datetime

# AWS Clients
sqs_client = boto3.client('sqs', region_name='us-east-1')
sns_client = boto3.client('sns', region_name='us-east-1')

# Environment variables
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AWS Clients (using IAM role from EC2 instance metadata)
s3_client = boto3.client('s3', region_name='us-east-1')

# RDS Configuration (from environment variables)
RDS_HOST = os.getenv('RDS_HOST')
RDS_USER = os.getenv('RDS_USER', 'admin')
RDS_PASSWORD = os.getenv('RDS_PASSWORD')
RDS_DATABASE = os.getenv('RDS_DATABASE', 'images_db')
S3_BUCKET = os.getenv('S3_BUCKET', 'martin-aleksiev-bucket-603196661040')

def get_db_connection():
    """Get connection to RDS MySQL database"""
    try:
        connection = pymysql.connect(
            host=RDS_HOST,
            user=RDS_USER,
            password=RDS_PASSWORD,
            database=RDS_DATABASE
        )
        return connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def get_ec2_metadata():
    """
    Retrieve EC2 instance metadata using IMDSv2.
    Returns region, AZ, instance ID, and instance type.
    """
    try:
        import requests
        
        # IMDSv2 requires a token first
        token_url = 'http://169.254.169.254/latest/api/token'
        token_response = requests.put(
            token_url,
            headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
            timeout=1
        )
        
        if token_response.status_code != 200:
            logger.error(f"Failed to get IMDSv2 token: {token_response.status_code}")
            raise Exception("Could not get metadata token")
        
        token = token_response.text
        
        # Now use the token to get metadata
        metadata_url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        response = requests.get(
            metadata_url,
            headers={'X-aws-ec2-metadata-token': token},
            timeout=1
        )
        
        if response.status_code == 200:
            metadata = response.json()
            return {
                'region': metadata.get('region', 'unknown'),
                'availability_zone': metadata.get('availabilityZone', 'unknown'),
                'instance_id': metadata.get('instanceId', 'unknown'),
                'instance_type': metadata.get('instanceType', 'unknown')
            }
        else:
            logger.error(f"Metadata service returned status {response.status_code}")
    except Exception as e:
        logger.error(f"Error getting EC2 metadata: {e}")
    
    return {
        'region': 'unknown',
        'availability_zone': 'unknown',
        'instance_id': 'unknown',
        'instance_type': 'unknown'
    }

@app.route('/', methods=['GET'])
def index():
    """
    Home page - returns HTML page with instance metadata
    """
    metadata = get_ec2_metadata()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>EC2 Instance Information</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 50px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                max-width: 500px;
            }}
            h1 {{
                color: #FF9900;
            }}
            .info {{
                margin: 15px 0;
                padding: 10px;
                background-color: #f9f9f9;
                border-left: 4px solid #FF9900;
            }}
            .label {{
                font-weight: bold;
                color: #333;
            }}
            .value {{
                color: #666;
                margin-left: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AWS EC2 Instance Information</h1>
            <div class="info">
                <span class="label">Region:</span>
                <span class="value">{metadata.get('region', 'N/A')}</span>
            </div>
            <div class="info">
                <span class="label">Availability Zone:</span>
                <span class="value">{metadata.get('availability_zone', 'N/A')}</span>
            </div>
            <div class="info">
                <span class="label">Instance ID:</span>
                <span class="value">{metadata.get('instance_id', 'N/A')}</span>
            </div>
            <div class="info">
                <span class="label">Instance Type:</span>
                <span class="value">{metadata.get('instance_type', 'N/A')}</span>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content, 200, {'Content-Type': 'text/html'}

@app.route('/api/metadata', methods=['GET'])
def api_metadata():
    """
    REST API endpoint - returns instance metadata as JSON
    """
    metadata = get_ec2_metadata()
    return jsonify(metadata), 200

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for load balancer
    """
    return jsonify({'status': 'healthy'}), 200

# ============================================================
# IMAGE OPERATIONS ENDPOINTS
# ============================================================

@app.route('/api/images/upload', methods=['POST'])
def upload_image():
    """
    Upload image to S3 and store metadata in RDS
    
    Expected: multipart/form-data with 'file' field
    Returns: JSON with success status and image details
    """
    try:
        # Check if file in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get file details
        filename = file.filename
        file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        file_content = file.read()
        file_size = len(file_content)
        
        # Upload to S3
        s3_key = f'images/{filename}'
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_content
        )
        
        logger.info(f"Uploaded image to S3: {s3_key}")
        
        # Store metadata in RDS
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        sql = """
        INSERT INTO image_metadata 
        (image_name, file_size, file_extension, s3_key)
        VALUES (%s, %s, %s, %s)
        """
        
        cursor.execute(sql, (filename, file_size, file_extension, s3_key))
        connection.commit()
        cursor.close()
        connection.close()
        
        logger.info(f"Stored metadata in RDS: {filename}")

        # Send message to SQS
        message_body = {
            'image_name': filename,
            'file_size': file_size,
            'file_extension': file_extension,
            'timestamp': datetime.utcnow().isoformat(),
            's3_key': s3_key
        }
        
        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message_body),
            MessageAttributes={
                'Extension': {
                    'StringValue': file_extension,
                    'DataType': 'String'
                }
            }
        )
        
        logger.info(f"Sent SQS message for: {filename}")
        
        return jsonify({
            'success': True,
            'message': f'Image {filename} uploaded successfully',
            'image_name': filename,
            'size': file_size,
            'extension': file_extension
        }), 201
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/images/download/<image_name>', methods=['GET'])
def download_image(image_name):
    """
    Download image from S3 by name
    
    Returns: File download
    """
    try:
        # Get file from S3
        s3_key = f'images/{image_name}'
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        
        logger.info(f"Downloaded image from S3: {image_name}")
        
        # Return file
        return send_file(
            BytesIO(response['Body'].read()),
            download_name=image_name,
            as_attachment=True
        )
    
    except s3_client.exceptions.NoSuchKey:
        logger.warning(f"Image not found in S3: {image_name}")
        return jsonify({'error': f'Image {image_name} not found'}), 404
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/images/metadata/<image_name>', methods=['GET'])
def get_image_metadata(image_name):
    """
    Get metadata for specific image by name
    
    Returns: JSON with name, size_bytes, extension, last_update
    """
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        
        sql = """
        SELECT image_name, file_size, file_extension, last_update
        FROM image_metadata
        WHERE image_name = %s
        """
        
        cursor.execute(sql, (image_name,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if not result:
            logger.warning(f"Metadata not found: {image_name}")
            return jsonify({'error': f'Image {image_name} not found'}), 404
        
        logger.info(f"Retrieved metadata: {image_name}")
        
        return jsonify({
            'name': result['image_name'],
            'size_bytes': result['file_size'],
            'extension': result['file_extension'],
            'last_update': result['last_update'].isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Metadata retrieval error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/images/metadata/random', methods=['GET'])
def get_random_image_metadata():
    """
    Get metadata for a random image
    
    Returns: JSON with name, size_bytes, extension, last_update
    """
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        
        # Get random image
        sql = """
        SELECT image_name, file_size, file_extension, last_update
        FROM image_metadata
        ORDER BY RAND()
        LIMIT 1
        """
        
        cursor.execute(sql)
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if not result:
            logger.warning("No images found in database")
            return jsonify({'error': 'No images found'}), 404
        
        logger.info(f"Retrieved random image metadata: {result['image_name']}")
        
        return jsonify({
            'name': result['image_name'],
            'size_bytes': result['file_size'],
            'extension': result['file_extension'],
            'last_update': result['last_update'].isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Random metadata retrieval error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/images/<image_name>', methods=['DELETE'])
def delete_image(image_name):
    """
    Delete image from S3 and metadata from RDS by name
    
    Returns: JSON with success status
    """
    try:
        # Delete from RDS first
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        sql = "DELETE FROM image_metadata WHERE image_name = %s"
        cursor.execute(sql, (image_name,))
        connection.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            connection.close()
            logger.warning(f"Image not found in database: {image_name}")
            return jsonify({'error': f'Image {image_name} not found'}), 404
        
        cursor.close()
        connection.close()
        
        logger.info(f"Deleted metadata from RDS: {image_name}")
        
        # Delete from S3
        s3_key = f'images/{image_name}'
        s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        
        logger.info(f"Deleted image from S3: {image_name}")
        
        return jsonify({
            'success': True,
            'message': f'Image {image_name} deleted successfully'
        }), 200
    
    except Exception as e:
        logger.error(f"Delete error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/images', methods=['GET'])
def list_images():
    """
    List all images with their metadata
    
    Returns: JSON array of all images
    """
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        
        sql = """
        SELECT image_name, file_size, file_extension, last_update
        FROM image_metadata
        ORDER BY last_update DESC
        """
        
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        
        images = [
            {
                'name': row['image_name'],
                'size_bytes': row['file_size'],
                'extension': row['file_extension'],
                'last_update': row['last_update'].isoformat()
            }
            for row in results
        ]
        
        logger.info(f"Retrieved {len(images)} images from database")
        
        return jsonify({'images': images, 'total': len(images)}), 200
    
    except Exception as e:
        logger.error(f"List images error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscribe', methods=['POST'])
def subscribe_email():
    """Subscribe email to image upload notifications"""
    try:
        email = request.json.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        response = sns_client.subscribe(
            TopicArn=SNS_TOPIC_ARN,
            Protocol='email',
            Endpoint=email
        )
        
        subscription_arn = response['SubscriptionArn']
        logger.info(f"Email subscribed: {email}")
        
        return jsonify({
            'success': True,
            'message': f'Confirmation sent to {email}',
            'subscription_arn': subscription_arn
        }), 201
    
    except Exception as e:
        logger.error(f"Subscribe error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/unsubscribe', methods=['POST'])
def unsubscribe_email():
    """Unsubscribe email from notifications"""
    try:
        subscription_arn = request.json.get('subscription_arn')
        
        if not subscription_arn:
            return jsonify({'error': 'subscription_arn required'}), 400
        
        sns_client.unsubscribe(SubscriptionArn=subscription_arn)
        logger.info(f"Email unsubscribed: {subscription_arn}")
        
        return jsonify({
            'success': True,
            'message': 'Successfully unsubscribed'
        }), 200
    
    except Exception as e:
        logger.error(f"Unsubscribe error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-consistency', methods=['GET'])
def check_consistency():
    """Trigger Lambda consistency check synchronously"""
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        response = lambda_client.invoke(FunctionName='flask-app-DataConsistencyFunction', InvocationType='RequestResponse', Payload=json.dumps({'source': 'web-app', 'httpMethod': 'GET'}))
        result = json.loads(response['Payload'].read())
        logger.info(f"Consistency check result: {json.dumps(result)}")
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Consistency check error: {e}")
        return jsonify({'error': str(e)}), 500
        
if __name__ == '__main__':
    # Run on 0.0.0.0 so it's accessible from outside the instance
    app.run(host='0.0.0.0', port=5000, debug=False)
