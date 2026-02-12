from flask import Flask, jsonify
import boto3
from botocore.exceptions import ClientError
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_ec2_metadata():
    """
    Retrieve EC2 instance metadata using boto3 EC2 Instance Metadata Service.
    Returns region, AZ, instance ID, and instance type.
    """
    try:
        # Create EC2 client - region will be auto-detected from instance metadata
        ec2_client = boto3.client('ec2', region_name=None)
        
        # Get instance metadata from the EC2 Instance Metadata Service
        session = boto3.Session()
        ec2_metadata = session.client('ec2').meta.region_name
        
        # Alternative approach: Use the metadata service directly
        import requests
        metadata_url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
        
        try:
            response = requests.get(metadata_url, timeout=1)
            if response.status_code == 200:
                metadata = response.json()
                return {
                    'region': metadata.get('region'),
                    'availability_zone': metadata.get('availabilityZone'),
                    'instance_id': metadata.get('instanceId'),
                    'instance_type': metadata.get('instanceType')
                }
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not reach metadata service: {e}")
        
        # Fallback: try to get from boto3 session
        return {
            'region': session.region_name or 'unknown',
            'availability_zone': 'unknown',
            'instance_id': 'unknown',
            'instance_type': 'unknown'
        }
        
    except Exception as e:
        logger.error(f"Error getting EC2 metadata: {e}")
        return {
            'region': 'unknown',
            'availability_zone': 'unknown',
            'error': str(e)
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

if __name__ == '__main__':
    # Run on 0.0.0.0 so it's accessible from outside the instance
    app.run(host='0.0.0.0', port=5000, debug=False)
