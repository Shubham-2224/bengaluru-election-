#!/bin/bash
# System Check Script for Voter Data Extraction Tool
# Run this before starting the server to verify all dependencies

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║   System Check - Voter Extraction Tool        ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

ERRORS=0
WARNINGS=0

# Check 1: Python 3
echo -n "Checking Python 3... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION"
    else
        echo -e "${RED}✗${NC} Python $PYTHON_VERSION (need 3.8+)"
        ERRORS=$((ERRORS+1))
    fi
else
    echo -e "${RED}✗${NC} Not found"
    echo "  Install: sudo apt install python3"
    ERRORS=$((ERRORS+1))
fi

# Check 2: pip
echo -n "Checking pip... "
if command -v pip3 &> /dev/null; then
    PIP_VERSION=$(pip3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓${NC} pip $PIP_VERSION"
else
    echo -e "${RED}✗${NC} Not found"
    echo "  Install: sudo apt install python3-pip"
    ERRORS=$((ERRORS+1))
fi

# Check 3: venv module
echo -n "Checking python3-venv... "
if python3 -m venv --help &> /dev/null; then
    echo -e "${GREEN}✓${NC} Available"
else
    echo -e "${RED}✗${NC} Not found"
    echo "  Install: sudo apt install python3-venv"
    ERRORS=$((ERRORS+1))
fi

# Check 4: Tesseract
echo -n "Checking Tesseract OCR... "
if command -v tesseract &> /dev/null; then
    TESS_VERSION=$(tesseract --version 2>&1 | head -n1 | cut -d' ' -f2)
    echo -e "${GREEN}✓${NC} $TESS_VERSION"
    
    # Check languages
    echo "  Languages:"
    LANGS=$(tesseract --list-langs 2>&1 | tail -n +2)
    
    echo -n "    - English (eng): "
    if echo "$LANGS" | grep -q "^eng$"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC} Missing"
        ERRORS=$((ERRORS+1))
    fi
    
    echo -n "    - Hindi (hin): "
    if echo "$LANGS" | grep -q "^hin$"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠${NC} Missing (recommended)"
        echo "      Install: sudo apt install tesseract-ocr-hin"
        WARNINGS=$((WARNINGS+1))
    fi
    
    echo -n "    - Marathi (mar): "
    if echo "$LANGS" | grep -q "^mar$"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠${NC} Missing (recommended)"
        echo "      Install: sudo apt install tesseract-ocr-mar"
        WARNINGS=$((WARNINGS+1))
    fi
else
    echo -e "${RED}✗${NC} Not found"
    echo "  Install: sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin tesseract-ocr-mar"
    ERRORS=$((ERRORS+1))
fi

# Check 5: Port 5000 availability
echo -n "Checking port 5000... "
if command -v lsof &> /dev/null; then
    PORT_CHECK=$(lsof -i:5000 -t 2>/dev/null)
    if [ -z "$PORT_CHECK" ]; then
        echo -e "${GREEN}✓${NC} Available"
    else
        PROCESS=$(ps -p $PORT_CHECK -o comm= 2>/dev/null)
        echo -e "${YELLOW}⚠${NC} In use by $PROCESS (PID: $PORT_CHECK)"
        echo "  To kill: sudo kill -9 $PORT_CHECK"
        WARNINGS=$((WARNINGS+1))
    fi
else
    echo -e "${YELLOW}⚠${NC} lsof not available, cannot check"
fi

# Check 6: Disk space
echo -n "Checking disk space... "
DISK_SPACE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$DISK_SPACE" -gt 5 ]; then
    echo -e "${GREEN}✓${NC} ${DISK_SPACE}GB available"
else
    echo -e "${YELLOW}⚠${NC} Only ${DISK_SPACE}GB available (low)"
    WARNINGS=$((WARNINGS+1))
fi

# Check 7: Project structure
echo -n "Checking project structure... "
if [ -d "backend/python-service" ] && [ -f "backend/python-service/app.py" ]; then
    echo -e "${GREEN}✓${NC} Valid"
else
    echo -e "${RED}✗${NC} Invalid directory structure"
    echo "  Run this script from project root"
    ERRORS=$((ERRORS+1))
fi

# Check 8: Requirements file
echo -n "Checking requirements.txt... "
if [ -f "backend/python-service/requirements.txt" ]; then
    REQ_COUNT=$(wc -l < backend/python-service/requirements.txt)
    echo -e "${GREEN}✓${NC} Found ($REQ_COUNT packages)"
else
    echo -e "${RED}✗${NC} Not found"
    ERRORS=$((ERRORS+1))
fi

# Check 9: Virtual environment
echo -n "Checking virtual environment... "
if [ -d "backend/python-service/venv" ]; then
    if [ -d "backend/python-service/venv/bin" ]; then
        echo -e "${GREEN}✓${NC} Linux venv exists"
    elif [ -d "backend/python-service/venv/Scripts" ]; then
        echo -e "${YELLOW}⚠${NC} Windows venv detected (needs recreation)"
        echo "  Solution: rm -rf backend/python-service/venv && cd backend/python-service && python3 -m venv venv"
        WARNINGS=$((WARNINGS+1))
    else
        echo -e "${YELLOW}⚠${NC} Corrupted venv (needs recreation)"
        WARNINGS=$((WARNINGS+1))
    fi
else
    echo -e "${YELLOW}⚠${NC} Not created yet (will be created on first run)"
fi

# Check 10: Environment file
echo -n "Checking .env configuration... "
if [ -f "backend/python-service/.env" ]; then
    echo -e "${GREEN}✓${NC} Found"
    
    # Check for Azure keys
    if grep -q "AZURE_OPENAI_API_KEY=your_" backend/python-service/.env 2>/dev/null; then
        echo -e "  ${YELLOW}⚠${NC} Azure OpenAI not configured (optional)"
    fi
    
    if grep -q "AZURE_VISION_KEY=your_" backend/python-service/.env 2>/dev/null; then
        echo -e "  ${YELLOW}⚠${NC} Azure Vision not configured (optional)"
    fi
else
    echo -e "${YELLOW}⚠${NC} Not found (using defaults)"
    echo "  To configure: cp backend/python-service/env.example.txt backend/python-service/.env"
fi

# Check 11: OpenCV (optional but helpful)
echo -n "Checking OpenCV... "
if python3 -c "import cv2" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Available"
else
    echo -e "${YELLOW}⚠${NC} Not available (will be installed with pip)"
fi

# Check 12: Network connectivity (for pip installs)
echo -n "Checking network connectivity... "
if ping -c 1 pypi.org &> /dev/null; then
    echo -e "${GREEN}✓${NC} Internet accessible"
else
    echo -e "${YELLOW}⚠${NC} Cannot reach pypi.org"
    WARNINGS=$((WARNINGS+1))
fi

# Summary
echo ""
echo "════════════════════════════════════════════════"
echo "  Summary"
echo "════════════════════════════════════════════════"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "You're ready to start the server:"
    echo "  ./scripts/start_server.sh"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ ${WARNINGS} warning(s) found${NC}"
    echo ""
    echo "System is mostly ready. You can proceed but may want to"
    echo "address warnings for optimal performance."
    echo ""
    echo "To start: ./scripts/start_server.sh"
else
    echo -e "${RED}✗ ${ERRORS} error(s), ${WARNINGS} warning(s) found${NC}"
    echo ""
    echo "Please fix the errors above before starting the server."
    echo ""
    echo "Quick fix for common issues:"
    echo "  sudo apt update"
    echo "  sudo apt install -y python3 python3-pip python3-venv tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar"
fi

echo ""
echo "════════════════════════════════════════════════"
echo ""

# Exit with error code if critical errors found
if [ $ERRORS -gt 0 ]; then
    exit 1
else
    exit 0
fi
