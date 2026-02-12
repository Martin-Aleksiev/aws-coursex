from flask import Flask, jsonify
import boto3
from botocore.exceptions import ClientError
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

if __name__ == '__main__':
    # Run on 0.0.0.0 so it's accessible from outside the instance
    app.run(host='0.0.0.0', port=5000, debug=False)
