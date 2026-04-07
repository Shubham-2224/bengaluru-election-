#!/bin/bash

# Setup script for Voter Extraction Service on Ubuntu EC2
# This script installs and configures the systemd service

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "===================================================="
echo "   Voter Extraction Service Setup"
echo "===================================================="
echo ""

# Get the current user and auto-detect project root
CURRENT_USER=$(whoami)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
SERVICE_DIR="$PROJECT_ROOT/deployment"
SERVICE_FILE="$SERVICE_DIR/voter-extraction.service"
SYSTEMD_DIR="/etc/systemd/system"
TARGET_SERVICE="$SYSTEMD_DIR/voter-extraction.service"

echo -e "${BLUE}Detected project root: $PROJECT_ROOT${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}ERROR: Do not run this script as root.${NC}"
   echo "Run it as your regular user (the script will use sudo when needed)"
   exit 1
fi

echo -e "${BLUE}[1/6]${NC} Checking prerequisites..."

# Check if project directory exists
if [ ! -d "$PROJECT_ROOT" ]; then
    echo -e "${RED}ERROR: Project directory not found at: $PROJECT_ROOT${NC}"
    echo "Please make sure you've uploaded the code to the correct location."
    exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}ERROR: Service file not found at: $SERVICE_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Project directory found"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is not installed${NC}"
    echo "Install it with: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Python 3 found: $(python3 --version)"

# Check Tesseract (CRITICAL for extraction)
if ! command -v tesseract &> /dev/null; then
    echo -e "${RED}ERROR: Tesseract OCR is not installed${NC}"
    echo "Tesseract is REQUIRED for data extraction."
    echo "Install it with: sudo apt update && sudo apt install tesseract-ocr tesseract-ocr-hin"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Tesseract found: $(tesseract --version 2>&1 | head -n 1)"
echo "  Location: $(which tesseract)"

# Check if virtual environment exists
VENV_PATH="$PROJECT_ROOT/backend/python-service/venv"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}[WARNING]${NC} Virtual environment not found. Creating it..."
    cd "$PROJECT_ROOT/backend/python-service"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}[OK]${NC} Virtual environment created and dependencies installed"
else
    echo -e "${GREEN}[OK]${NC} Virtual environment found"
fi

echo ""
echo -e "${BLUE}[2/6]${NC} Updating service file with current user and paths..."

# Get the actual path dynamically
ACTUAL_WORKING_DIR="$PROJECT_ROOT/backend/python-service"
ACTUAL_VENV_BIN="$ACTUAL_WORKING_DIR/venv/bin"
ACTUAL_PYTHON="$ACTUAL_VENV_BIN/python3"

# Create a temporary service file with the actual values
TEMP_SERVICE=$(mktemp)
sed "s|<USERNAME>|$CURRENT_USER|g" "$SERVICE_FILE" | \
sed "s|/home/<USERNAME>/ocr/voter_extraction_without_API|$PROJECT_ROOT|g" | \
sed "s|/home/$CURRENT_USER/ocr/voter_extraction_without_API|$PROJECT_ROOT|g" > "$TEMP_SERVICE"

echo -e "${GREEN}[OK]${NC} Service file configured"
echo "  User: $CURRENT_USER"
echo "  Working Directory: $ACTUAL_WORKING_DIR"
echo "  Python: $ACTUAL_PYTHON"

echo ""
echo -e "${BLUE}[3/6]${NC} Installing systemd service..."

# Copy service file to systemd directory
sudo cp "$TEMP_SERVICE" "$TARGET_SERVICE"
sudo chmod 644 "$TARGET_SERVICE"
rm "$TEMP_SERVICE"

echo -e "${GREEN}[OK]${NC} Service file installed to $TARGET_SERVICE"

echo ""
echo -e "${BLUE}[4/6]${NC} Reloading systemd daemon..."
sudo systemctl daemon-reload
echo -e "${GREEN}[OK]${NC} Systemd daemon reloaded"

echo ""
echo -e "${BLUE}[5/6]${NC} Enabling service to start on boot..."
sudo systemctl enable voter-extraction.service
echo -e "${GREEN}[OK]${NC} Service enabled"

echo ""
echo -e "${BLUE}[6/6]${NC} Starting service..."
sudo systemctl start voter-extraction.service
sleep 2

# Check service status
if sudo systemctl is-active --quiet voter-extraction.service; then
    echo -e "${GREEN}[OK]${NC} Service is running"
else
    echo -e "${YELLOW}[WARNING]${NC} Service may not have started correctly"
    echo "Checking status..."
    sudo systemctl status voter-extraction.service --no-pager -l
fi

echo ""
echo "===================================================="
echo "   Setup Complete!"
echo "===================================================="
echo ""
echo "Service Information:"
echo "  Name: voter-extraction.service"
echo "  Status: $(sudo systemctl is-active voter-extraction.service)"
echo "  Port: 5000"
echo ""
echo "Useful Commands:"
echo "  Check status:  sudo systemctl status voter-extraction"
echo "  View logs:     sudo journalctl -u voter-extraction -f"
echo "  Start service: sudo systemctl start voter-extraction"
echo "  Stop service:  sudo systemctl stop voter-extraction"
echo "  Restart:       sudo systemctl restart voter-extraction"
echo ""
echo "Access your application at:"
echo "  http://$(curl -s ifconfig.me || echo 'your-ec2-ip'):5000"
echo "  or"
echo "  http://localhost:5000 (from the EC2 instance)"
echo ""
echo "===================================================="
echo ""

