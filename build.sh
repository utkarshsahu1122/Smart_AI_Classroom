#!/bin/bash
set -e

# 1. Install Backend Dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 2. Ensure Required Directories Exist
echo "Setting up application directories..."
mkdir -p app/static/vectorstores
mkdir -p app/static/temp_uploads
mkdir -p app/static/qrcodes

# 3. Build Frontend
echo "Building React frontend..."
cd frontend
npm install
npm run build
echo "Deployment build completed successfully!"
