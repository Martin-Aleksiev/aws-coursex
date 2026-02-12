#!/bin/bash
# Build script for Python Flask web application
# Creates a deployable ZIP artifact

set -e

echo "=== Building Flask Web Application ==="

# Create build directory
BUILD_DIR="build"
ARTIFACT_NAME="web-app-artifact"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACT_FILE="${ARTIFACT_NAME}-${TIMESTAMP}.zip"

# Clean previous builds
rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}

echo "Creating artifact directory..."
mkdir -p ${BUILD_DIR}/${ARTIFACT_NAME}

echo "Copying application files..."
cp app.py ${BUILD_DIR}/${ARTIFACT_NAME}/
cp requirements.txt ${BUILD_DIR}/${ARTIFACT_NAME}/

echo "Creating deployment script..."
cat > ${BUILD_DIR}/${ARTIFACT_NAME}/deploy.sh << 'EOF'
#!/bin/bash
# Deployment script for Flask application

set -e

echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo "Starting Flask application..."
nohup python3 app.py > app.log 2>&1 &

echo "Flask application started on port 5000"
EOF

chmod +x ${BUILD_DIR}/${ARTIFACT_NAME}/deploy.sh

echo "Creating startup systemd service..."
cat > ${BUILD_DIR}/${ARTIFACT_NAME}/flask-app.service << 'EOF'
[Unit]
Description=Flask EC2 Metadata Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/flask-app
ExecStart=/usr/bin/python3 /opt/flask-app/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Creating ZIP artifact..."
cd ${BUILD_DIR}
zip -r ${ARTIFACT_FILE} ${ARTIFACT_NAME}/
cd ..

echo ""
echo "=== Build Complete ==="
echo "Artifact created: ${BUILD_DIR}/${ARTIFACT_FILE}"
echo "Size: $(du -h ${BUILD_DIR}/${ARTIFACT_FILE} | cut -f1)"
