# Flask EC2 Metadata Web Application

A simple Python Flask web application that displays AWS EC2 instance metadata (Region and Availability Zone).

## Project Structure

```
web-app-project/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── build.sh              # Build automation script
├── README.md             # This file
└── .github/
    └── workflows/
        └── build-and-deploy.yml  # CI/CD workflow (optional)
```

## Features

- **HTML Endpoint** (`/`): Returns a styled HTML page showing instance metadata
- **REST API Endpoint** (`/api/metadata`): Returns metadata as JSON
- **Health Check** (`/health`): Simple health check for load balancers
- **EC2 Metadata Integration**: Uses boto3 to fetch region, AZ, instance ID, and instance type

## Requirements

- Python 3.7+
- Flask 2.3.3
- boto3 (AWS SDK for Python)
- requests

## Local Development

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/web-app-project.git
cd web-app-project
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python3 app.py
```

The application will start on `http://localhost:5000`

### 5. Test the Endpoints

- **HTML Page**: `curl http://localhost:5000/`
- **API Endpoint**: `curl http://localhost:5000/api/metadata`
- **Health Check**: `curl http://localhost:5000/health`

## Building the Artifact

### Automated Build (Recommended)

```bash
chmod +x build.sh
./build.sh
```

This creates a ZIP file in the `build/` directory containing:
- `app.py`
- `requirements.txt`
- `deploy.sh` (deployment script)
- `flask-app.service` (systemd service file)

### Manual Build

```bash
mkdir -p build/web-app-artifact
cp app.py requirements.txt build/web-app-artifact/
cd build
zip -r web-app-artifact.zip web-app-artifact/
```

## Uploading to S3

```bash
# Upload artifact to S3
aws s3 cp build/web-app-artifact-TIMESTAMP.zip s3://your-bucket-name/

# Example with s3-admin profile
aws s3 cp build/web-app-artifact-TIMESTAMP.zip s3://martin-a-a/ --profile s3-admin
```

## Deployment on EC2 (Custom AMI)

The artifact includes:
- `deploy.sh`: Automated deployment script
- `flask-app.service`: Systemd service for auto-start

### Deployment Steps

1. Download artifact from S3
2. Extract the ZIP
3. Run `deploy.sh`
4. Application starts on port 5000

## CI/CD with GitHub Actions (Optional)

You can automate the build and S3 upload using GitHub Actions. Add `.github/workflows/build-and-deploy.yml` for automatic builds on push.

## AWS EC2 Metadata Service

The application uses the EC2 Instance Metadata Service to retrieve:
- **Region**: AWS region (e.g., eu-central-1)
- **Availability Zone**: AZ within region (e.g., eu-central-1a)
- **Instance ID**: Unique instance identifier
- **Instance Type**: Instance type (e.g., t2.micro)

Endpoint: `http://169.254.169.254/latest/dynamic/instance-identity/document`

## Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/` | GET | HTML page with metadata | HTML |
| `/api/metadata` | GET | JSON metadata | JSON |
| `/health` | GET | Health check | JSON |

## Example Response

### HTML (/)
```html
AWS EC2 Instance Information
Region: eu-central-1
Availability Zone: eu-central-1a
Instance ID: i-0123456789abcdef0
Instance Type: t2.micro
```

### JSON (/api/metadata)
```json
{
  "region": "eu-central-1",
  "availability_zone": "eu-central-1a",
  "instance_id": "i-0123456789abcdef0",
  "instance_type": "t2.micro"
}
```

## Notes

- Port 5000 is used by default (changeable in `app.py`)
- Application runs as `ubuntu` user when deployed on EC2
- For production, use a proper WSGI server (e.g., Gunicorn) instead of Flask's development server
- Load balancer should use `/health` endpoint for health checks

## License

MIT

## Author

[Your Name]
