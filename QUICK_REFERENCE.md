# 🚀 Quick Reference - Voter Data Extraction Tool (Linux)

## ⚡ Quick Start (Copy & Paste)

```bash
# 1. Check system requirements
./check_system.sh

# 2. Start the server
./scripts/start_server.sh

# 3. Access in browser
# http://localhost:5000
```

---

## 📂 Project Structure

```
data extraction without api desai/
├── backend/python-service/     # Flask backend
│   ├── app.py                  # Main Flask application
│   ├── extractor.py            # Data extraction logic
│   ├── excel_generator.py      # Excel export
│   ├── requirements.txt        # Python dependencies
│   ├── venv/                   # Virtual environment
│   ├── uploads/                # Uploaded PDFs
│   └── outputs/                # Generated Excel files
├── frontend/                   # Web interface
│   ├── index.html              # Main UI
│   ├── js/                     # JavaScript files
│   └── css/                    # Stylesheets
├── deployment/                 # Production deployment
│   ├── setup-service.sh        # Install as systemd service
│   └── service-manager.sh      # Manage service
└── scripts/                    # Helper scripts
    └── start_server.sh         # Development server
```

---

## 🛠️ Common Commands

### System Check
```bash
# Run system check
./check_system.sh

# Check Python version
python3 --version

# Check Tesseract
tesseract --version
tesseract --list-langs
```

### Development Server
```bash
# Start server (auto-setup)
./scripts/start_server.sh

# Manual start
cd backend/python-service
source venv/bin/activate
python3 app.py

# Stop server
Ctrl+C
```

### Virtual Environment
```bash
# Create new venv
cd backend/python-service
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Deactivate venv
deactivate

# Install dependencies
pip install -r requirements.txt

# Update dependencies
pip install --upgrade -r requirements.txt
```

### Production Service
```bash
# Install as service (one-time)
cd deployment
sudo ./setup-service.sh

# Service management
sudo systemctl start voter-extraction
sudo systemctl stop voter-extraction
sudo systemctl restart voter-extraction
sudo systemctl status voter-extraction

# View logs
sudo journalctl -u voter-extraction -f
sudo journalctl -u voter-extraction -n 100

# Enable/disable auto-start
sudo systemctl enable voter-extraction
sudo systemctl disable voter-extraction

# Using manager script
./deployment/service-manager.sh start
./deployment/service-manager.sh stop
./deployment/service-manager.sh status
./deployment/service-manager.sh logs
```

### Troubleshooting
```bash
# Check port usage
sudo lsof -i:5000
sudo ss -tuln | grep 5000

# Kill process on port 5000
sudo lsof -i:5000 -t | xargs sudo kill -9

# Check disk space
df -h
du -sh backend/python-service/uploads/
du -sh backend/python-service/outputs/

# Clean up files
rm -rf backend/python-service/uploads/*
rm -rf backend/python-service/outputs/*

# View application logs
tail -f backend/python-service/app.log
tail -f backend/python-service/app.log | grep ERROR

# Test OCR
tesseract test_image.png output --oem 3 --psm 6 -l eng+hin+mar

# Check Python packages
pip list
pip show flask
```

### Configuration
```bash
# Copy environment template
cp backend/python-service/env.example.txt backend/python-service/.env

# Edit configuration
nano backend/python-service/.env

# View configuration
cat backend/python-service/.env

# Test configuration
cd backend/python-service
source venv/bin/activate
python3 config.py
```

---

## 🔧 API Endpoints (curl examples)

```bash
# Health check
curl http://localhost:5000/health

# Upload PDF
curl -X POST http://localhost:5000/api/upload-pdf \
  -F "file=@voter_data.pdf"

# Check disk space
curl http://localhost:5000/api/disk-space

# Cleanup old files
curl -X POST http://localhost:5000/api/cleanup-files \
  -H "Content-Type: application/json" \
  -d '{"aggressive": false}'

# Download Excel (replace EXCEL_ID)
curl -o output.xlsx http://localhost:5000/api/download-excel/EXCEL_ID
```

---

## 🐛 Common Issues & Quick Fixes

### Port 5000 in use
```bash
sudo lsof -i:5000 -t | xargs sudo kill -9
```

### Tesseract not found
```bash
sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar
```

### Permission denied on scripts
```bash
chmod +x check_system.sh
chmod +x scripts/start_server.sh
chmod +x deployment/*.sh
```

### Virtual environment issues
```bash
rm -rf backend/python-service/venv
cd backend/python-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Disk full error
```bash
# Check space
df -h

# Clean uploads/outputs
rm -rf backend/python-service/uploads/*
rm -rf backend/python-service/outputs/*

# Or via API
curl -X POST http://localhost:5000/api/cleanup-files \
  -H "Content-Type: application/json" \
  -d '{"aggressive": true}'
```

### PaddleOCR installation fails
```bash
# Option 1: Install CPU version
pip install paddlepaddle==2.5.1

# Option 2: Skip it (edit requirements.txt)
nano backend/python-service/requirements.txt
# Comment out: paddlepaddle and paddleocr
```

---

## 📊 Environment Variables (.env)

```env
# Server
DEBUG=False                      # Enable debug mode (dev only)
PORT=5000                        # Server port
HOST=0.0.0.0                     # Bind address

# Security
FILE_RETENTION_HOURS=24          # Auto-cleanup period
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000
AUTH_ENABLED=False               # Enable API authentication
API_KEYS=key1,key2               # API keys (if auth enabled)

# OCR
TESSERACT_CMD=/usr/bin/tesseract # Tesseract path
OCR_DPI=400                      # OCR resolution (300-600)
OCR_CONFIDENCE_THRESHOLD=0.7     # Azure fallback threshold

# Azure (Optional)
AZURE_OPENAI_API_KEY=            # Azure OpenAI key
AZURE_OPENAI_ENDPOINT=           # Azure OpenAI endpoint
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_VISION_KEY=                # Azure Vision key
AZURE_VISION_ENDPOINT=           # Azure Vision endpoint

# Performance
MAX_BACKGROUND_WORKERS=3         # Concurrent tasks
MAX_FILE_SIZE=524288000          # Max upload size (bytes)

# Logging
LOG_LEVEL=INFO                   # DEBUG|INFO|WARNING|ERROR
LOG_FILE=app.log                 # Log file name
```

---

## 🔥 Pro Tips

### 1. **Better OCR accuracy**
```env
OCR_DPI=600  # Increase from 400 (slower but better)
```

### 2. **Auto-start on boot**
```bash
sudo systemctl enable voter-extraction
```

### 3. **Monitor logs in real-time**
```bash
# Application logs
tail -f backend/python-service/app.log

# Service logs
sudo journalctl -u voter-extraction -f

# Only errors
tail -f backend/python-service/app.log | grep -i error
```

### 4. **Access from other devices**
```bash
# Find your IP
ip addr show | grep "inet " | grep -v 127.0.0.1

# Access from other devices
# http://YOUR_IP:5000
```

### 5. **Firewall setup**
```bash
# Ubuntu (UFW)
sudo ufw allow 5000/tcp
sudo ufw enable

# Fedora (firewalld)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

### 6. **Performance tuning**
```bash
# For large PDFs, increase workers
echo "MAX_BACKGROUND_WORKERS=4" >> backend/python-service/.env

# Use async extraction for files > 10 pages
# (Use /api/extract-grid-async endpoint)
```

### 7. **Backup configuration**
```bash
# Backup .env file
cp backend/python-service/.env backend/python-service/.env.backup

# Restore
cp backend/python-service/.env.backup backend/python-service/.env
```

---

## 📈 Monitoring

### Check Service Status
```bash
# Quick status
./deployment/service-manager.sh status

# Detailed status
sudo systemctl status voter-extraction -l

# Is it running?
ps aux | grep app.py
```

### Resource Usage
```bash
# CPU and Memory
top -p $(pgrep -f "python3 app.py")
htop -p $(pgrep -f "python3 app.py")

# Disk usage
df -h
du -sh backend/python-service/{uploads,outputs}
```

### View Statistics
```bash
# Application logs
grep "records extracted" backend/python-service/app.log

# Count processed files
ls -1 backend/python-service/outputs/*.xlsx | wc -l

# Average extraction time
grep "Extraction time" backend/python-service/app.log | awk '{sum+=$NF; count++} END {print sum/count "s average"}'
```

---

## 🌐 URLs

- **Application:** http://localhost:5000
- **Health Check:** http://localhost:5000/health
- **API Base:** http://localhost:5000/api

---

## 📞 Support

**Issues?**
1. Run `./check_system.sh`
2. Check logs: `tail -f backend/python-service/app.log`
3. Test API: `curl http://localhost:5000/health`
4. Review: `LINUX_SETUP_GUIDE.md`

---

## 🎯 Workflow

1. **Upload PDF** → Upload voter data PDF
2. **Configure Grid** → Draw grid on first page
3. **Define Template** → Mark fields (Voter ID, Name, etc.)
4. **Extract** → Process all pages
5. **Download Excel** → Get results

---

**Last Updated:** 2026-01-19  
**System:** Linux (Ubuntu/Debian/Fedora/Arch)
