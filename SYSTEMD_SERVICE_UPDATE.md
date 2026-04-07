# Systemd Service Update - January 2026

## 🎯 What Was Updated

The voter-extraction.service and related deployment scripts have been updated to work correctly with AWS instances and dynamic paths.

---

## ❌ Previous Issues

1. **Wrong Path**: Service file had `/PythonData_From_data/` which doesn't exist
2. **Hardcoded Paths**: Setup script had fixed path to `/home/ubuntu/ocr/PythonData_From_data`
3. **No IP Detection**: No easy way to get current public IP after AWS restart
4. **Manual Configuration**: Required manual editing of service files

---

## ✅ What's Fixed

### 1. Systemd Service File (`voter-extraction.service`)

**Before:**
```ini
WorkingDirectory=/home/<USERNAME>/Projects/voter_extraction_without_API/PythonData_From_data/backend/python-service
```

**After:**
```ini
WorkingDirectory=/home/<USERNAME>/ocr/voter_extraction_without_API/backend/python-service
```

**Key Changes:**
- ✅ Fixed incorrect path
- ✅ Added HOST and PORT environment variables
- ✅ Properly configured for AWS instances

### 2. Setup Script (`setup-service.sh`)

**Before:**
```bash
PROJECT_ROOT="/home/ubuntu/ocr/PythonData_From_data"  # Hardcoded!
```

**After:**
```bash
# Auto-detect project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
```

**Key Changes:**
- ✅ Auto-detects project location
- ✅ Works wherever you place the project
- ✅ Dynamically replaces all placeholders
- ✅ Better error messages and validation

### 3. Service Manager (`service-manager.sh`)

**New Feature: IP Detection**
```bash
./service-manager.sh info
```

**Output:**
```
Service Information:
===================
Local URL:       http://localhost:5000
Private IP:      http://172.31.10.49:5000
Public IP:       http://13.201.89.53:5000

👉 Access from browser: http://13.201.89.53:5000

Status: RUNNING
```

**Key Features:**
- ✅ Shows current public IP (auto-detected from AWS metadata)
- ✅ Shows private IP for local network
- ✅ One command to get all access URLs
- ✅ Perfect for AWS instances with changing IPs

### 4. New Documentation

Created comprehensive guides:
- ✅ `deployment/README.md` - Overview of deployment files
- ✅ `deployment/SERVICE_USAGE.md` - Complete usage guide
- ✅ Updated all AWS guides in project root

---

## 🚀 How to Use

### First Time Setup

1. **Install the service:**
   ```bash
   cd ~/ocr/voter_extraction_without_API/deployment
   sudo ./setup-service.sh
   ```

2. **Get your access URL:**
   ```bash
   ./service-manager.sh info
   ```

3. **Access the application:**
   - Open browser to the Public IP shown
   - Example: `http://13.201.89.53:5000`

### After AWS Instance Restart

When your public IP changes:

```bash
cd ~/ocr/voter_extraction_without_API/deployment
./service-manager.sh info
```

That's it! The service auto-starts on boot.  
Just note the new public IP and use it to access the application.

---

## 📋 Available Commands

### Service Manager Commands

```bash
cd ~/ocr/voter_extraction_without_API/deployment

# Get current IPs (most important for AWS!)
./service-manager.sh info

# Check status
./service-manager.sh status

# Start/stop/restart
./service-manager.sh start
./service-manager.sh stop
./service-manager.sh restart

# View logs
./service-manager.sh logs         # Live logs
./service-manager.sh logs-tail    # Last 50 lines

# Enable/disable auto-start
./service-manager.sh enable
./service-manager.sh disable

# Full health check
./service-manager.sh check
```

### Direct Systemctl Commands

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

# Enable auto-start
sudo systemctl enable voter-extraction
```

---

## 🎁 Benefits of This Update

### For AWS Instances

| Before | After |
|--------|-------|
| ❌ Service file had wrong paths | ✅ Correct paths, auto-detected |
| ❌ Manual editing required | ✅ Fully automatic setup |
| ❌ No way to get current IP | ✅ `./service-manager.sh info` shows it |
| ❌ Had to manually check IP services | ✅ Auto-detects from AWS metadata |

### For Service Management

| Feature | Status |
|---------|--------|
| Auto-start on boot | ✅ Enabled by default |
| Auto-restart on crash | ✅ Enabled |
| Runs in background | ✅ Yes |
| Survives SSH disconnect | ✅ Yes |
| Easy IP lookup | ✅ One command |
| Simple log access | ✅ Built-in |

---

## 🔧 Technical Details

### How IP Detection Works

1. **Try AWS EC2 Metadata Service** (fastest, most reliable on AWS)
   ```bash
   curl http://169.254.169.254/latest/meta-data/public-ipv4
   ```

2. **Fallback to External Service** (if not on AWS)
   ```bash
   curl https://api.ipify.org
   ```

3. **Private IP Detection**
   ```bash
   hostname -I | awk '{print $1}'
   ```

### Service Configuration

The service runs with:
- **User**: Your user account (not root)
- **Working Directory**: Auto-detected project location
- **Environment**: HOST=0.0.0.0, PORT=5000
- **Restart Policy**: Always restart on failure
- **Security**: NoNewPrivileges, PrivateTmp enabled

### File Locations

```
Project Structure:
~/ocr/voter_extraction_without_API/
├── deployment/
│   ├── voter-extraction.service  ← Systemd service file
│   ├── setup-service.sh          ← One-time setup script
│   ├── service-manager.sh        ← Management tool
│   ├── README.md                 ← Deployment overview
│   └── SERVICE_USAGE.md          ← Usage guide
├── backend/
│   └── python-service/
│       ├── app.py               ← Flask application
│       └── venv/                ← Python virtual environment
└── frontend/
    └── ...

System Files (after setup):
/etc/systemd/system/
└── voter-extraction.service      ← Installed service file
```

---

## 🛠️ Troubleshooting

### Service Won't Start

```bash
# Check error logs
sudo journalctl -u voter-extraction -n 50

# Check service status
sudo systemctl status voter-extraction

# Try re-running setup
cd ~/ocr/voter_extraction_without_API/deployment
sudo ./setup-service.sh
```

### Can't Access from Browser

**Checklist:**
1. ✅ Service running: `./service-manager.sh status`
2. ✅ Get current IP: `./service-manager.sh info`
3. ✅ AWS Security Group has port 5000 open
4. ✅ Test locally: `curl http://localhost:5000/health`

### Need to Update Code

```bash
# After pulling new code or making changes:
cd ~/ocr/voter_extraction_without_API/deployment
./service-manager.sh restart
```

---

## 📚 Documentation Structure

```
Project Documentation:
├── AWS_DEPLOYMENT_GUIDE.md      ← Complete AWS setup guide
├── AWS_QUICK_START.md           ← 5-minute quick start
├── DYNAMIC_IP_UPDATE.md         ← Dynamic IP changes summary
├── SYSTEMD_SERVICE_UPDATE.md    ← This file
└── deployment/
    ├── README.md                ← Deployment files overview
    └── SERVICE_USAGE.md         ← Service usage guide
```

---

## ✅ Summary

### What You Get

1. **Automatic Setup**: Run one script, everything is configured
2. **Auto-Start**: Service starts on boot automatically
3. **Easy IP Lookup**: One command shows current public IP
4. **Simple Management**: Easy commands for all operations
5. **AWS Optimized**: Perfect for instances with changing IPs
6. **Complete Docs**: Comprehensive guides for everything

### Key Commands to Remember

```bash
# Setup (one-time)
cd ~/ocr/voter_extraction_without_API/deployment
sudo ./setup-service.sh

# Get current IP (after AWS restart)
./service-manager.sh info

# Manage service
./service-manager.sh start|stop|restart|status

# View logs
./service-manager.sh logs
```

---

## 🎉 Result

Your voter extraction service now:
- ✅ Installs correctly with auto-detected paths
- ✅ Starts automatically on AWS instance boot
- ✅ Provides easy IP address lookup
- ✅ Works seamlessly with changing AWS public IPs
- ✅ Offers simple management commands
- ✅ Includes comprehensive documentation

**No more manual configuration or path editing needed!** 🚀
