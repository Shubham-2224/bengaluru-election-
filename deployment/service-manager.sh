#!/bin/bash

# Service Management Helper Script
# Quick commands to manage the voter-extraction service

SERVICE_NAME="voter-extraction"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    echo ""
    echo "Voter Extraction Service Manager"
    echo "================================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start      - Start the service"
    echo "  stop       - Stop the service"
    echo "  restart    - Restart the service"
    echo "  status     - Show service status"
    echo "  logs       - Show service logs (follow mode)"
    echo "  logs-tail  - Show last 50 lines of logs"
    echo "  enable     - Enable service to start on boot"
    echo "  disable    - Disable service from starting on boot"
    echo "  check      - Check if service is running and port is open"
    echo "  info       - Show access URLs with current IP addresses"
    echo "  debug      - Show detailed debugging information"
    echo "  test-env   - Test if all dependencies are available"
    echo ""
}

show_info() {
    echo ""
    echo "Service Information:"
    echo "==================="
    
    # Get IPs
    PRIVATE_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")
    PUBLIC_IP=""
    
    if command -v curl &> /dev/null; then
        PUBLIC_IP=$(curl -s --connect-timeout 1 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || \
                    curl -s --connect-timeout 2 https://api.ipify.org 2>/dev/null || echo "")
    fi
    
    echo "Local URL:       http://localhost:5000"
    if [ ! -z "$PRIVATE_IP" ]; then
        echo "Private IP:      http://$PRIVATE_IP:5000"
    fi
    if [ ! -z "$PUBLIC_IP" ]; then
        echo -e "${GREEN}Public IP:       http://$PUBLIC_IP:5000${NC}"
        echo ""
        echo -e "${YELLOW}👉 Access from browser: http://$PUBLIC_IP:5000${NC}"
    fi
    
    echo ""
    echo "API Endpoints:"
    echo "  Health:      /health"
    echo "  Server Info: /api/server-info"
    echo ""
    
    if sudo systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "Status: ${GREEN}RUNNING${NC}"
    else
        echo -e "Status: ${RED}STOPPED${NC}"
    fi
    echo ""
}

show_debug() {
    echo ""
    echo "Debug Information:"
    echo "=================="
    echo ""
    
    echo "1. Service Status:"
    sudo systemctl status $SERVICE_NAME --no-pager -l | head -n 20
    
    echo ""
    echo "2. Recent Logs (last 30 lines):"
    sudo journalctl -u $SERVICE_NAME -n 30 --no-pager
    
    echo ""
    echo "3. Service Environment:"
    sudo systemctl show $SERVICE_NAME --property=Environment
    
    echo ""
    echo "4. Working Directory:"
    sudo systemctl show $SERVICE_NAME --property=WorkingDirectory
    
    echo ""
    echo "5. Port Check:"
    if sudo lsof -i:5000 > /dev/null 2>&1; then
        echo -e "${GREEN}Port 5000 is in use:${NC}"
        sudo lsof -i:5000
    else
        echo -e "${RED}Port 5000 is NOT in use${NC}"
    fi
    
    echo ""
    echo "6. Process Check:"
    if pgrep -f "python3 app.py" > /dev/null; then
        echo -e "${GREEN}Python process is running:${NC}"
        ps aux | grep "python3 app.py" | grep -v grep
    else
        echo -e "${RED}No Python process found${NC}"
    fi
    echo ""
}

test_environment() {
    echo ""
    echo "Testing Environment Dependencies:"
    echo "================================="
    echo ""
    
    # Check Python
    if command -v python3 &> /dev/null; then
        echo -e "${GREEN}✓${NC} Python3: $(python3 --version)"
    else
        echo -e "${RED}✗${NC} Python3 not found"
    fi
    
    # Check Tesseract
    if command -v tesseract &> /dev/null; then
        echo -e "${GREEN}✓${NC} Tesseract: $(tesseract --version 2>&1 | head -n 1)"
        echo "   Location: $(which tesseract)"
    else
        echo -e "${RED}✗${NC} Tesseract not found"
    fi
    
    # Check virtual environment
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
    VENV_PATH="$PROJECT_ROOT/backend/python-service/venv"
    
    if [ -d "$VENV_PATH" ]; then
        echo -e "${GREEN}✓${NC} Virtual environment exists"
        if [ -f "$VENV_PATH/bin/python3" ]; then
            echo -e "${GREEN}✓${NC} Python in venv: $($VENV_PATH/bin/python3 --version)"
        fi
    else
        echo -e "${RED}✗${NC} Virtual environment not found"
    fi
    
    # Check uploads/outputs directories
    if [ -d "$PROJECT_ROOT/backend/python-service/uploads" ]; then
        echo -e "${GREEN}✓${NC} Uploads directory exists"
    else
        echo -e "${YELLOW}!${NC} Uploads directory missing"
    fi
    
    if [ -d "$PROJECT_ROOT/backend/python-service/outputs" ]; then
        echo -e "${GREEN}✓${NC} Outputs directory exists"
    else
        echo -e "${YELLOW}!${NC} Outputs directory missing"
    fi
    
    # Check .env file
    if [ -f "$PROJECT_ROOT/backend/python-service/.env" ]; then
        echo -e "${GREEN}✓${NC} .env file exists"
    else
        echo -e "${YELLOW}!${NC} .env file not found (optional)"
    fi
    
    # Test if we can import key Python modules
    echo ""
    echo "Testing Python imports in virtual environment:"
    cd "$PROJECT_ROOT/backend/python-service"
    source venv/bin/activate
    
    python3 -c "import flask; print('✓ Flask: ' + flask.__version__)" 2>/dev/null || echo -e "${RED}✗ Flask import failed${NC}"
    python3 -c "import fitz; print('✓ PyMuPDF (fitz): OK')" 2>/dev/null || echo -e "${RED}✗ PyMuPDF import failed${NC}"
    python3 -c "import pytesseract; print('✓ pytesseract: OK')" 2>/dev/null || echo -e "${RED}✗ pytesseract import failed${NC}"
    python3 -c "import PIL; print('✓ Pillow: ' + PIL.__version__)" 2>/dev/null || echo -e "${RED}✗ Pillow import failed${NC}"
    
    deactivate
    
    echo ""
}

check_status() {
    echo ""
    echo "Service Status:"
    echo "==============="
    sudo systemctl status $SERVICE_NAME --no-pager -l
    echo ""
    echo "Port Check:"
    echo "==========="
    if sudo lsof -i:5000 > /dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC} Port 5000 is in use"
        sudo lsof -i:5000
    else
        echo -e "${RED}[ERROR]${NC} Port 5000 is not in use"
    fi
    echo ""
}

case "$1" in
    start)
        echo "Starting $SERVICE_NAME..."
        sudo systemctl start $SERVICE_NAME
        sleep 1
        sudo systemctl status $SERVICE_NAME --no-pager -l | head -n 10
        ;;
    stop)
        echo "Stopping $SERVICE_NAME..."
        sudo systemctl stop $SERVICE_NAME
        sleep 1
        sudo systemctl status $SERVICE_NAME --no-pager -l | head -n 10
        ;;
    restart)
        echo "Restarting $SERVICE_NAME..."
        sudo systemctl restart $SERVICE_NAME
        sleep 2
        sudo systemctl status $SERVICE_NAME --no-pager -l | head -n 10
        ;;
    status)
        check_status
        ;;
    logs)
        echo "Showing logs (Press Ctrl+C to exit)..."
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    logs-tail)
        echo "Last 50 lines of logs:"
        sudo journalctl -u $SERVICE_NAME -n 50 --no-pager
        ;;
    enable)
        echo "Enabling $SERVICE_NAME to start on boot..."
        sudo systemctl enable $SERVICE_NAME
        echo -e "${GREEN}[OK]${NC} Service enabled"
        ;;
    disable)
        echo "Disabling $SERVICE_NAME from starting on boot..."
        sudo systemctl disable $SERVICE_NAME
        echo -e "${YELLOW}[OK]${NC} Service disabled"
        ;;
    check)
        check_status
        ;;
    info)
        show_info
        ;;
    debug)
        show_debug
        ;;
    test-env)
        test_environment
        ;;
    *)
        show_help
        ;;
esac

