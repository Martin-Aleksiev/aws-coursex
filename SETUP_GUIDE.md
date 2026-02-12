# Flask Web Application Project - Complete Setup Guide

## What You Have

I've created a complete Python Flask project structure with:

### Files Created:
1. **app.py** - Main Flask application with 3 endpoints
2. **requirements.txt** - Python dependencies
3. **build.sh** - Automated build script
4. **README.md** - Complete documentation
5. **.gitignore** - Git ignore rules

## Step-by-Step Setup

### Step 1: Create GitHub Repository

1. Go to GitHub.com and log in
2. Click "New repository"
3. **Repository name**: `web-app-project`
4. **Description**: Flask EC2 Metadata Web Application
5. **Visibility**: Public (or Private if you prefer)
6. Click "Create repository"

### Step 2: Upload Files to GitHub

You have two options:

**Option A: Using Git CLI (Recommended)**
```bash
# Create local directory
mkdir web-app-project
cd web-app-project

# Initialize git
git init
git add .
git commit -m "Initial commit: Flask EC2 metadata application"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/web-app-project.git
git push -u origin main
```

**Option B: Upload via GitHub Web UI**
1. Go to your repository on GitHub
2. Click "Add file" → "Upload files"
3. Drag and drop all files
4. Click "Commit changes"

### Step 3: Test Locally (Optional but Recommended)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/web-app-project.git
cd web-app-project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python3 app.py

# In another terminal, test the endpoints
curl http://localhost:5000/
curl http://localhost:5000/api/metadata
curl http://localhost:5000/health
```

### Step 4: Build the Artifact

```bash
# Make build script executable
chmod +x build.sh

# Run build
./build.sh

# This creates: build/web-app-artifact-TIMESTAMP.zip
```

### Step 5: Upload Artifact to S3

```bash
# Upload to your S3 bucket
aws s3 cp build/web-app-artifact-*.zip s3://martin-a-a/ --profile s3-admin

# Verify upload
aws s3 ls s3://martin-a-a/ --profile s3-admin
```

## Application Endpoints

1. **HTML Page** (`GET /`)
   - Returns styled HTML page with instance metadata
   - User-friendly display
   - Shows: Region, AZ, Instance ID, Instance Type

2. **REST API** (`GET /api/metadata`)
   - Returns JSON response
   - Machine-readable format
   - Perfect for programmatic access

3. **Health Check** (`GET /health`)
   - Simple endpoint for load balancer health checks
   - Returns: `{"status": "healthy"}`

## Key Features

✅ **EC2 Metadata Integration**: Uses boto3 and EC2 Instance Metadata Service
✅ **Multi-endpoint design**: HTML + REST API + Health Check
✅ **Automated build process**: One command creates deployable artifact
✅ **Ready for AMI**: Includes deploy.sh and systemd service file
✅ **Load balancer ready**: Health check endpoint included

## Next Steps (For Load Balancer Task)

1. ✅ Create project and upload to GitHub (THIS STEP)
2. Build artifact and upload to S3
3. Create custom AMI with Python/Flask runtime
4. Create Auto-Scaling Group (2-3 instances)
5. Attach Elastic Load Balancer

## File Locations

Local project is in: `/home/claude/web_app_project/`

## Troubleshooting

**Port 5000 already in use?**
```bash
python3 app.py --port 8080
# Or modify app.py last line to: app.run(host='0.0.0.0', port=8080)
```

**ModuleNotFoundError: No module named 'flask'?**
```bash
pip install -r requirements.txt
```

**Permission denied on build.sh?**
```bash
chmod +x build.sh
```

## Ready?

Once you've created the GitHub repository and pushed the files, let me know and we'll proceed with:
- Building the artifact
- Uploading to S3
- Creating the custom AMI
- Setting up the load balancer
