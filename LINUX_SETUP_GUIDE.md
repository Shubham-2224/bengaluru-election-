# 🐧 Linux Setup Guide - Voter Data Extraction Tool

## Quick Start (TL;DR)

```bash
# 1. Install system dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar

# 2. Run the startup script
cd "/home/smasher/Projects/data extraction without api desai"
chmod +x scripts/start_server.sh
./scripts/start_server.sh

# 3. Open browser to http://localhost:5000
```

---

## 📋 Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Steps](#installation-steps)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [Troubleshooting](#troubleshooting)
6. [Production Deployment](#production-deployment)

---

## 🖥️ System Requirements

### Supported Distributions
- Ubuntu 20.04+ (LTS recommended)
- Debian 10+
- Fedora 35+
- Arch Linux
- Other Linux distributions (may require package name adjustments)

### Minimum Hardware
- **CPU:** 2 cores (4+ recommended for faster OCR)
- **RAM:** 4GB (8GB+ recommended)
- **Storage:** 2GB free space (more for processing large PDFs)

### Required Software
- Python 3.8 or higher
- Tesseract OCR 4.0+
- pip (Python package manager)
- Git (optional, for version control)

---

## 🔧 Installation Steps

### Step 1: Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-mar \
    libtesseract-dev \
    libleptonica-dev \
    libopencv-dev \
    python3-opencv
```

#### Fedora/RHEL/CentOS
```bash
sudo dnf install -y \
    python3 \
    python3-pip \
    python3-virtualenv \
    tesseract \
    tesseract-langpack-eng \
    tesseract-langpack-hin \
    tesseract-langpack-mar \
    opencv-python3
```

#### Arch Linux
```bash
sudo pacman -S \
    python \
    python-pip \
    python-virtualenv \
    tesseract \
    tesseract-data-eng \
    tesseract-data-hin \
    opencv
```

### Step 2: Verify Tesseract Installation

```bash
# Check Tesseract version
tesseract --version

# Check available languages (should include eng, hin, mar)
tesseract --list-langs
```

Expected output:
```
List of available languages (3):
eng
hin
mar
```

**If Hindi/Marathi languages are missing:**

Ubuntu/Debian:
```bash
# Download language data manually
sudo wget -P /usr/share/tesseract-ocr/4.00/tessdata/ \
    https://github.com/tesseract-ocr/tessdata/raw/main/hin.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/mar.traineddata
```

### Step 3: Navigate to Project Directory

```bash
cd "/home/smasher/Projects/data extraction without api desai"
```

### Step 4: Create Python Virtual Environment

```bash
# Remove any existing Windows venv
rm -rf backend/python-service/venv

# Create fresh Linux venv
cd backend/python-service
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Step 5: Install Python Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt
```

**If you encounter errors:**
- For PaddlePaddle errors on ARM systems (like Raspberry Pi):
  ```bash
  # Remove paddlepaddle from requirements and install CPU version
  pip install paddlepaddle==2.5.1 -f https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html
  ```

### Step 6: Configure Environment Variables (Optional)

```bash
# Copy example env file
cp env.example.txt .env

# Edit .env file
nano .env
```

**Minimal configuration (no Azure services):**
```env
DEBUG=False
FILE_RETENTION_HOURS=24
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000
OCR_DPI=400
LOG_LEVEL=INFO
```

**With Azure services (optional, for better accuracy):**
```env
# Add Azure OpenAI credentials
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Add Azure Vision credentials
AZURE_VISION_KEY=your_key_here
AZURE_VISION_ENDPOINT=https://your-vision.cognitiveservices.azure.com/
```

---

## ▶️ Running the Application

### Option 1: Using the Startup Script (Recommended)

```bash
# From project root
cd "/home/smasher/Projects/data extraction without api desai"

# Make script executable (first time only)
chmod +x scripts/start_server.sh

# Run the server
./scripts/start_server.sh
```

The script will:
- ✅ Check Python installation
- ✅ Create/verify virtual environment
- ✅ Install dependencies
- ✅ Check Tesseract OCR
- ✅ Check port availability
- ✅ Start Flask server
- ✅ Open browser automatically

### Option 2: Manual Start

```bash
# Navigate to backend
cd "/home/smasher/Projects/data extraction without api desai/backend/python-service"

# Activate venv
source venv/bin/activate

# Run Flask app
python3 app.py
```

### Accessing the Application

Once started, access the application at:
- **Local access:** http://localhost:5000
- **Network access:** http://YOUR_IP:5000

To find your IP address:
```bash
ip addr show | grep inet
```

---

## 🔍 Troubleshooting

### Issue 1: Port 5000 Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Find process using port 5000
sudo lsof -i:5000

# Kill the process
sudo kill -9 <PID>

# Or change port in .env
echo "PORT=5001" >> backend/python-service/.env
```

### Issue 2: Tesseract Not Found

**Error:** `TesseractNotFoundError`

**Solution:**
```bash
# Check if installed
which tesseract

# If not installed
sudo apt install tesseract-ocr

# Set path in .env
echo "TESSERACT_CMD=/usr/bin/tesseract" >> backend/python-service/.env
```

### Issue 3: Permission Denied

**Error:** `Permission denied: './start_server.sh'`

**Solution:**
```bash
chmod +x scripts/start_server.sh
chmod +x deployment/setup-service.sh
chmod +x deployment/service-manager.sh
```

### Issue 4: Virtual Environment Issues

**Error:** `Cannot activate virtual environment`

**Solution:**
```bash
# Remove corrupted venv
rm -rf backend/python-service/venv

# Recreate
cd backend/python-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue 5: PaddleOCR Installation Fails

**Error:** `Failed building wheel for paddlepaddle`

**Solution:**
```bash
# Option 1: Install CPU version only
pip install paddlepaddle==2.5.1

# Option 2: Skip PaddleOCR (Tesseract will be used)
# Edit requirements.txt and comment out:
# paddlepaddle
# paddleocr
```

### Issue 6: Low Disk Space

**Error:** `Disk is full` or `No space left on device`

**Solution:**
```bash
# Check disk space
df -h

# Clean up old files via API
curl -X POST http://localhost:5000/api/cleanup-files \
     -H "Content-Type: application/json" \
     -d '{"aggressive": true}'

# Or manually
rm -rf backend/python-service/uploads/*
rm -rf backend/python-service/outputs/*
```

### Issue 7: Browser Doesn't Open Automatically

**Solution:**
```bash
# Manually open browser
xdg-open http://localhost:5000

# Or use your preferred browser
firefox http://localhost:5000
google-chrome http://localhost:5000
```

### Issue 8: OCR Accuracy Poor for Marathi Text

**Current Status:** The system uses `lang='eng+hin'` but Marathi support exists in code

**Solution:**
```bash
# Ensure Marathi is installed
sudo apt install tesseract-ocr-mar

# Verify
tesseract --list-langs | grep mar

# The system should automatically use eng+hin+mar
```

---

## 🚀 Production Deployment

### As a Systemd Service (Recommended for Servers)

```bash
# Navigate to deployment folder
cd "/home/smasher/Projects/data extraction without api desai/deployment"

# Make setup script executable
chmod +x setup-service.sh

# Run setup (installs as systemd service)
sudo ./setup-service.sh
```

**Service Management:**
```bash
# Start service
sudo systemctl start voter-extraction

# Stop service
sudo systemctl stop voter-extraction

# Restart service
sudo systemctl restart voter-extraction

# Check status
sudo systemctl status voter-extraction

# View logs
sudo journalctl -u voter-extraction -f

# Enable auto-start on boot
sudo systemctl enable voter-extraction
```

### Using Service Manager Script

```bash
cd deployment
chmod +x service-manager.sh

# Easy management
./service-manager.sh start
./service-manager.sh stop
./service-manager.sh restart
./service-manager.sh status
./service-manager.sh logs
```

### Firewall Configuration

If you want to access from other machines:

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 5000/tcp
sudo ufw reload

# Fedora/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

### Reverse Proxy with Nginx (Optional)

```bash
# Install Nginx
sudo apt install nginx

# Create config
sudo nano /etc/nginx/sites-available/voter-extraction

# Add configuration:
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/voter-extraction /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 📊 Performance Optimization

### For Better OCR Performance

1. **Increase OCR DPI** (slower but more accurate):
   ```env
   OCR_DPI=600  # Default is 400
   ```

2. **Use more worker threads**:
   ```env
   MAX_BACKGROUND_WORKERS=4  # Default is 3
   ```

3. **Enable Azure Vision** for difficult pages:
   - Set up Azure Computer Vision account
   - Add credentials to `.env`

### For Large PDF Files

1. **Increase max file size**:
   ```env
   MAX_FILE_SIZE=524288000  # 500MB
   ```

2. **Use async extraction endpoint** for files with many pages

---

## 🔐 Security Considerations

### For Production Deployment

1. **Enable authentication:**
   ```env
   AUTH_ENABLED=True
   API_KEYS=your_secure_key_here
   ```

2. **Restrict CORS origins:**
   ```env
   ALLOWED_ORIGINS=https://your-domain.com
   ```

3. **Disable debug mode:**
   ```env
   DEBUG=False
   ```

4. **Use HTTPS** with Nginx + Let's Encrypt:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

---

## 📚 Additional Resources

### Documentation Files
- `deployment/README.md` - Detailed deployment guide
- `deployment/QUICK_START.md` - Quick reference
- `ANALYSIS_AND_IMPROVEMENTS.md` - Code analysis and future improvements

### API Endpoints

- `GET /health` - Health check
- `POST /api/upload-pdf` - Upload PDF file
- `POST /api/configure-extraction` - Configure grid extraction
- `POST /api/extract-grid` - Synchronous extraction (small PDFs)
- `POST /api/extract-grid-async` - Asynchronous extraction (large PDFs)
- `GET /api/task-status/<taskId>` - Check async task status
- `GET /api/download-excel/<excelId>` - Download result
- `GET /api/disk-space` - Check disk space
- `POST /api/cleanup-files` - Cleanup old files

### Logs Location
- Application logs: `backend/python-service/app.log`
- System service logs: `sudo journalctl -u voter-extraction`

---

## 🆘 Getting Help

If you encounter issues:

1. **Check logs:**
   ```bash
   tail -f backend/python-service/app.log
   ```

2. **Verify configuration:**
   ```bash
   cd backend/python-service
   source venv/bin/activate
   python config.py
   ```

3. **Test OCR:**
   ```bash
   tesseract --version
   tesseract --list-langs
   ```

4. **Check service health:**
   ```bash
   curl http://localhost:5000/health
   ```

---

## ✅ Success Indicators

You'll know everything is working when:
- ✅ Browser opens to http://localhost:5000
- ✅ You see "Voter Data Extraction Tool" interface
- ✅ You can upload a PDF file
- ✅ Grid overlay appears on PDF
- ✅ Extraction completes successfully
- ✅ Excel file downloads with data

---

## 🎯 Next Steps

1. **Test with a sample PDF**
2. **Configure grid extraction settings**
3. **Review extracted data quality**
4. **Adjust OCR settings if needed**
5. **Set up Azure services for better accuracy** (optional)
6. **Deploy as systemd service** for production

---

**Happy Extracting! 🚀**
