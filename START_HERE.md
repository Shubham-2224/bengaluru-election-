# 🎯 START HERE - Linux Quick Start

## ✅ Your System Status: READY!

All dependencies are installed and verified on your Linux system.

---

## 🚀 To Start the Server (Just One Command!)

```bash
cd "/home/smasher/Projects/data extraction without api desai"
./scripts/start_server.sh
```

**That's it!** The server will start and your browser will open automatically to:
**http://localhost:5000**

---

## 📁 New Files Created for You

I've created comprehensive documentation for running this project on Linux:

### 1. **LINUX_SETUP_GUIDE.md** (Complete Guide)
   - Full installation instructions
   - System requirements
   - Configuration options
   - Troubleshooting section
   - Production deployment guide

### 2. **QUICK_REFERENCE.md** (Command Cheat Sheet)
   - Common commands
   - API endpoints
   - Environment variables
   - Pro tips and tricks

### 3. **READY_TO_RUN.md** (System Status)
   - Your system check results
   - What's working
   - Quick start steps
   - First-time setup timeline

### 4. **check_system.sh** (System Verification Script)
   - Checks all dependencies
   - Verifies configuration
   - Reports any issues
   - Run anytime: `./check_system.sh`

### 5. **START_HERE.md** (This File)
   - Quick overview
   - Fastest way to get started

---

## 📊 System Check Results

✅ **Python 3.12.3** - Installed and working  
✅ **pip 24.0** - Package manager ready  
✅ **Tesseract OCR 5.3.4** - OCR engine ready  
✅ **English (eng)** - Language pack installed  
✅ **Hindi (hin)** - Language pack installed  
✅ **Marathi (mar)** - Language pack installed  
✅ **Port 5000** - Available for use  
✅ **168 GB** - Disk space available  
✅ **Internet** - Connected for pip installs  

---

## 🎓 What This Project Does

**Voter Data Extraction Tool** - A web-based application that:

1. **Uploads** PDF files containing voter data
2. **Analyzes** the document structure with OCR
3. **Extracts** voter information:
   - Voter ID (EPIC number)
   - Name (Hindi/Marathi with English transliteration)
   - Photo (embedded in Excel)
   - Relative's name (Father/Husband/Mother)
   - House number, Gender, Age
   - Serial number, Assembly number
   - Booth center and address
4. **Exports** data to Excel with images

**Tech Stack:**
- **Backend:** Flask (Python) on port 5000
- **Frontend:** HTML/CSS/JavaScript with PDF.js
- **OCR:** Tesseract (English + Hindi + Marathi)
- **Optional:** PaddleOCR, Azure Vision, Azure OpenAI

---

## ⚡ Quick Start (Copy-Paste)

### Option 1: Development Mode (Recommended for Testing)

```bash
# Navigate to project
cd "/home/smasher/Projects/data extraction without api desai"

# Start server (auto-installs dependencies)
./scripts/start_server.sh

# Access at http://localhost:5000
```

### Option 2: Production Mode (Run as Service)

```bash
# Navigate to deployment
cd "/home/smasher/Projects/data extraction without api desai/deployment"

# Install as systemd service
sudo ./setup-service.sh

# Manage service
sudo systemctl start voter-extraction
sudo systemctl status voter-extraction

# Access at http://localhost:5000
```

---

## 🔄 First Run Process

When you run `./scripts/start_server.sh` for the first time:

```
[1/4] Setting up Python virtual environment... ✓
[2/4] Installing/Updating Python dependencies... ✓
[3/4] Checking configuration... ✓
[4/4] Checking Tesseract OCR... ✓
[5/6] Checking port 5000... ✓
[6/6] Starting Flask server... ✓

╔════════════════════════════════════════════════╗
║   Voter Extraction - Python Service (Flask)   ║
╚════════════════════════════════════════════════╝

  Server running on: http://0.0.0.0:5000
  Ready to process requests!
```

⏱️ **Expected time:** 3-5 minutes (first time only)  
⏱️ **Subsequent starts:** ~10 seconds

---

## 🖥️ Using the Web Interface

Once the server is running:

1. **Open Browser** → http://localhost:5000

2. **Upload PDF**
   - Click "Choose PDF File" or drag & drop
   - Wait for PDF to load

3. **Configure Grid**
   - Set rows and columns (e.g., 10 × 3)
   - Click "Draw Grid"
   - Grid overlay appears on PDF

4. **Define Template** (One-time per PDF format)
   - Select field type (Voter ID, Name, Photo, etc.)
   - Click on cell to mark field location
   - Repeat for all fields

5. **Extract Data**
   - Click "Extract Vertically"
   - Wait for processing (progress shown)
   - Preview extracted data

6. **Download Excel**
   - Click "Download Excel"
   - Excel file with all data and photos

---

## 📱 Access from Other Devices

To access from phones/tablets/other computers on your network:

```bash
# Find your IP address
ip addr show | grep "inet " | grep -v 127.0.0.1

# Example output: 192.168.1.100

# Access from other devices:
# http://192.168.1.100:5000

# Allow through firewall (if needed)
sudo ufw allow 5000/tcp
```

---

## 🛠️ Useful Commands

```bash
# Check system status
./check_system.sh

# Start server
./scripts/start_server.sh

# Stop server
Ctrl+C

# View logs
tail -f backend/python-service/app.log

# Check if running
curl http://localhost:5000/health

# Clean old files
rm -rf backend/python-service/{uploads,outputs}/*
```

---

## 📚 Documentation Files

| File | Purpose | When to Read |
|------|---------|--------------|
| **START_HERE.md** | Quick overview | Right now! |
| **READY_TO_RUN.md** | System status | Before first run |
| **QUICK_REFERENCE.md** | Command reference | Daily use |
| **LINUX_SETUP_GUIDE.md** | Complete guide | Troubleshooting |
| `deployment/README.md` | Production setup | For servers |
| `deployment/QUICK_START.md` | Service deployment | Production use |

---

## ⚙️ Configuration (Optional)

The system works with default settings, but you can customize:

```bash
# Create config file
cp backend/python-service/env.example.txt backend/python-service/.env

# Edit settings
nano backend/python-service/.env

# Key settings:
# - OCR_DPI=400 (increase to 600 for better accuracy)
# - FILE_RETENTION_HOURS=24 (auto-cleanup period)
# - DEBUG=False (enable for development)
```

---

## 🚨 Troubleshooting

### Server won't start?
```bash
./check_system.sh  # Re-run system check
tail -f backend/python-service/app.log  # Check logs
```

### Port 5000 in use?
```bash
sudo lsof -i:5000  # Find what's using it
sudo lsof -i:5000 -t | xargs sudo kill -9  # Kill it
```

### Dependencies fail?
```bash
rm -rf backend/python-service/venv  # Remove venv
./scripts/start_server.sh  # Recreate and reinstall
```

### More help?
- Read: `LINUX_SETUP_GUIDE.md` (Troubleshooting section)
- Check: `QUICK_REFERENCE.md` (Common issues)

---

## 🎯 What's Next?

### Right Now:
```bash
./scripts/start_server.sh
```

### After Testing:
- Review `QUICK_REFERENCE.md` for commands
- Configure settings in `.env` if needed
- Set up as system service for production

### For Production:
```bash
cd deployment
sudo ./setup-service.sh
```

---

## 💡 Did You Know?

- ✨ The system auto-cleans files older than 24 hours
- ✨ Supports PDFs up to 500MB
- ✨ Can process English, Hindi, and Marathi text
- ✨ Exports data with embedded photos in Excel
- ✨ Uses async processing for large PDFs
- ✨ Has built-in fallback OCR strategies
- ✨ Can run as a background service
- ✨ Includes API for automation

---

## 🎉 Ready to Start?

Your Linux system is fully configured. Just run:

```bash
./scripts/start_server.sh
```

**Browser will open automatically to:** http://localhost:5000

---

**Questions?** All documentation is in the project root:
- `LINUX_SETUP_GUIDE.md` - Complete guide
- `QUICK_REFERENCE.md` - Quick commands
- `READY_TO_RUN.md` - System status

**Good luck with your data extraction! 🚀**
