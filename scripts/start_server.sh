#!/bin/bash

# Voter Extraction Server - Linux/Ubuntu/macOS Startup Script
# This script automates the setup and startup of the Flask server
# Works on Linux, Ubuntu, and macOS

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where the script is located and navigate to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_NAME="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_NAME="Linux"
else
    OS_NAME="Unix"
fi

echo ""
echo "===================================================="
echo "   Voter Extraction - Python Server ($OS_NAME)"
echo "===================================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}====================================================${NC}"
    echo -e "${RED}   ERROR: Python Not Found${NC}"
    echo -e "${RED}====================================================${NC}"
    echo ""
    echo "Python 3 is not installed or not in your system PATH!"
    echo ""
    echo "SOLUTION:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "1. Install Python 3.8+ using Homebrew:"
        echo "   brew install python@3.12"
        echo "2. If Homebrew is not installed:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    else
    echo "1. Install Python 3.8+ using your package manager:"
    echo "   Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    echo "   Fedora/RHEL:   sudo dnf install python3 python3-pip"
    echo "   Arch Linux:    sudo pacman -S python python-pip"
    fi
    echo "2. After installation, run this script again"
    echo ""
    echo "===================================================="
    echo ""
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Python found"
python3 --version

# Check if backend directory exists
if [ ! -d "backend/python-service" ]; then
    echo ""
    echo -e "${RED}====================================================${NC}"
    echo -e "${RED}   ERROR: Directory Not Found${NC}"
    echo -e "${RED}====================================================${NC}"
    echo ""
    echo "Python service directory not found!"
    echo "Expected location: backend/python-service"
    echo ""
    echo "Make sure you are running this file from the project root."
    echo ""
    echo "===================================================="
    echo ""
    exit 1
fi

cd backend/python-service

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo ""
    echo -e "${RED}====================================================${NC}"
    echo -e "${RED}   ERROR: requirements.txt Not Found${NC}"
    echo -e "${RED}====================================================${NC}"
    echo ""
    echo "The requirements.txt file is missing!"
    echo "This file is needed to install Python dependencies."
    echo ""
    echo "Make sure you are in the correct directory:"
    echo "backend/python-service"
    echo ""
    echo "===================================================="
    echo ""
    exit 1
fi

echo ""
echo -e "${BLUE}[1/4]${NC} Setting up Python virtual environment..."

# Check if venv exists and if it's a Windows venv (has Scripts but no bin)
if [ -d "venv" ]; then
    if [ -d "venv/Scripts" ] && [ ! -d "venv/bin" ]; then
        echo -e "${YELLOW}[WARNING]${NC} Windows virtual environment detected"
        echo "Removing Windows venv and creating Linux-compatible one..."
        rm -rf venv
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            echo -e "${RED}ERROR: Failed to create virtual environment${NC}"
            echo "Make sure python3-venv is installed:"
            echo "  sudo apt install python3-venv"
            exit 1
        fi
        echo -e "${GREEN}[OK]${NC} Linux virtual environment created"
    elif [ -d "venv/bin" ]; then
        echo -e "${GREEN}[OK]${NC} Virtual environment already exists (Linux)"
    else
        echo -e "${YELLOW}[WARNING]${NC} Virtual environment appears corrupted"
        echo "Recreating virtual environment..."
        rm -rf venv
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            echo -e "${RED}ERROR: Failed to create virtual environment${NC}"
            echo "Make sure python3-venv is installed:"
            echo "  sudo apt install python3-venv"
            exit 1
        fi
        echo -e "${GREEN}[OK]${NC} Virtual environment recreated"
    fi
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Failed to create virtual environment${NC}"
        echo "Make sure python3-venv is installed:"
        echo "  sudo apt install python3-venv"
        exit 1
    fi
    echo -e "${GREEN}[OK]${NC} Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Failed to activate virtual environment${NC}"
    echo "Trying to recreate virtual environment..."
    rm -rf venv
    python3 -m venv venv
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Still failed to activate virtual environment${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${BLUE}[2/4]${NC} Installing/Updating Python dependencies..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install -r requirements.txt --quiet

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}[WARNING]${NC} Some dependencies may have failed to install."
    echo "Continuing anyway..."
else
    echo -e "${GREEN}[OK]${NC} Dependencies ready"
fi

echo ""
echo -e "${BLUE}[3/4]${NC} Checking configuration..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[INFO]${NC} .env file not found. Using defaults."
    echo -e "${YELLOW}[INFO]${NC} To configure Azure/Google APIs, copy env.example.txt to .env"
else
    echo -e "${GREEN}[OK]${NC} Configuration file found"
fi

# Check for Tesseract OCR
echo ""
echo -e "${BLUE}[4/4]${NC} Checking Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    echo -e "${GREEN}[OK]${NC} Tesseract OCR found"
    tesseract --version | head -n 1
else
    echo -e "${YELLOW}[WARNING]${NC} Tesseract OCR not found in PATH"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Install it with: brew install tesseract tesseract-lang"
    else
    echo "Install it with: sudo apt install tesseract-ocr tesseract-ocr-hin"
    fi
    echo "Continuing anyway (some features may not work)..."
fi

# Check if port 5000 is already in use
echo ""
echo -e "${BLUE}[5/7]${NC} Checking port 5000..."
PORT_IN_USE=false
PORT_PID=""
PORT_COMMAND=""

if command -v lsof &> /dev/null; then
    PORT_INFO=$(lsof -i:5000 -t 2>/dev/null | head -n 1)
    if [ ! -z "$PORT_INFO" ]; then
        PORT_PID=$PORT_INFO
        PORT_COMMAND=$(ps -p $PORT_PID -o comm= 2>/dev/null || echo "unknown")
        PORT_IN_USE=true
    fi
elif command -v netstat &> /dev/null; then
    PORT_INFO=$(netstat -tuln 2>/dev/null | grep ':5000 ' | head -n 1)
    if [ ! -z "$PORT_INFO" ]; then
        PORT_IN_USE=true
    fi
fi

if [ "$PORT_IN_USE" = true ]; then
    echo -e "${YELLOW}[WARNING]${NC} Port 5000 is already in use"
    if [ ! -z "$PORT_PID" ] && [ ! -z "$PORT_COMMAND" ]; then
        echo "  Process: $PORT_COMMAND (PID: $PORT_PID)"
        echo ""
        echo -e "${YELLOW}Would you like to kill this process? (y/n)${NC}"
        read -t 5 -n 1 -r KILL_PROCESS || KILL_PROCESS="n"
        echo ""
        if [[ $KILL_PROCESS =~ ^[Yy]$ ]]; then
            if kill -9 $PORT_PID 2>/dev/null; then
                echo -e "${GREEN}[OK]${NC} Process killed. Port 5000 is now free."
                sleep 1
            else
                echo -e "${RED}[ERROR]${NC} Could not kill process. You may need to run:"
                echo "  sudo kill -9 $PORT_PID"
                echo ""
                echo "Or use a different port by setting PORT in .env file"
                exit 1
            fi
        else
            echo -e "${YELLOW}[INFO]${NC} Keeping existing process. Please use a different port."
            echo "Set PORT=5001 in .env file to use port 5001 instead."
            exit 1
        fi
    else
        echo "  Could not identify the process using port 5000"
        echo ""
        echo "To find and kill it manually:"
        echo "  lsof -i:5000"
        echo "  kill -9 <PID>"
        echo ""
        echo "Or use a different port by setting PORT in .env file"
        exit 1
    fi
else
    echo -e "${GREEN}[OK]${NC} Port 5000 is available"
fi

echo ""
echo -e "${BLUE}[6/6]${NC} Detecting IP addresses..."

# Detect private IP
PRIVATE_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")
if [ -z "$PRIVATE_IP" ]; then
    PRIVATE_IP=$(ip route get 8.8.8.8 2>/dev/null | awk '{print $7}' | head -n1 || echo "")
fi

# Try to detect public IP (AWS EC2 metadata service)
PUBLIC_IP=""
if command -v curl &> /dev/null; then
    # Try AWS EC2 metadata first (fast for AWS instances)
    PUBLIC_IP=$(curl -s --connect-timeout 1 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "")
    
    # If not on AWS, try external service
    if [ -z "$PUBLIC_IP" ]; then
        PUBLIC_IP=$(curl -s --connect-timeout 2 https://api.ipify.org 2>/dev/null || echo "")
    fi
elif command -v wget &> /dev/null; then
    # Try AWS EC2 metadata first
    PUBLIC_IP=$(wget -qO- --timeout=1 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "")
    
    # If not on AWS, try external service
    if [ -z "$PUBLIC_IP" ]; then
        PUBLIC_IP=$(wget -qO- --timeout=2 https://api.ipify.org 2>/dev/null || echo "")
    fi
fi

echo ""
echo -e "${BLUE}[7/7]${NC} Starting Flask server..."
echo ""
echo "===================================================="
echo "   Server Information"
echo "===================================================="
echo "Local URL:       http://localhost:5000"

if [ ! -z "$PRIVATE_IP" ]; then
    echo "Private IP:      http://$PRIVATE_IP:5000"
fi

if [ ! -z "$PUBLIC_IP" ]; then
    echo -e "${GREEN}Public IP:       http://$PUBLIC_IP:5000${NC}"
    echo ""
    echo -e "${YELLOW}👉 Use the Public IP URL to access from your browser!${NC}"
fi

echo ""
echo "Frontend:        /index.html (or just /)"
echo "API Health:      /health"
echo "Server Info:     /api/server-info"
echo ""
echo "===================================================="
echo "   Instructions"
echo "===================================================="
echo "1. Wait for 'Server running on...' message"
if [ ! -z "$PUBLIC_IP" ]; then
    echo "2. Open browser to: http://$PUBLIC_IP:5000"
else
    echo "2. Open browser to: http://localhost:5000"
fi
echo "3. Press Ctrl+C to stop the server"
echo ""
echo "Note: Make sure port 5000 is open in your firewall!"
if [ ! -z "$PUBLIC_IP" ]; then
    echo "      (AWS: Add inbound rule for TCP port 5000)"
fi
echo "===================================================="
echo ""

# Try to open browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    (sleep 3 && open http://localhost:5000 2>/dev/null) &
elif command -v xdg-open &> /dev/null; then
    # Linux
    (sleep 3 && xdg-open http://localhost:5000 2>/dev/null) &
fi

# Start the Flask server
python3 app.py

# If server exits, show message
echo ""
echo "===================================================="
echo "   Server Stopped"
echo "===================================================="
echo ""
echo "The server has been stopped."
echo "To start again, run: ./start_server.sh"
echo ""
echo "===================================================="
echo ""

