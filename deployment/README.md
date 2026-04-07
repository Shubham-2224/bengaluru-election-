# Deployment Files - Updated for AWS

## 📁 Files in This Directory

### 1. `voter-extraction.service`
Systemd service configuration file.

**Key Features:**
- ✅ Auto-detects project location
- ✅ Runs as your user (not root)
- ✅ Auto-restart on crash
- ✅ Full system PATH (includes tesseract, etc.)
- ✅ Loads .env file automatically
- ✅ Proper OCR temp file access
- ✅ Listens on 0.0.0.0:5000 (accessible from outside)

**Recent Fix (Jan 2026):**
- ✅ Fixed PATH to include `/usr/bin` for tesseract
- ✅ Added EnvironmentFile to load .env
- ✅ Disabled PrivateTmp for OCR temp files
- ✅ Now extraction works same as manual run!

### 2. `setup-service.sh`
One-time setup script to install the systemd service.

**Features:**
- ✅ Auto-detects project directory
- ✅ Validates all prerequisites
- ✅ Creates virtual environment if needed
- ✅ Installs and enables service
- ✅ Starts service automatically

**Usage:**
```bash
cd ~/ocr/voter_extraction_without_API/deployment
chmod +x setup-service.sh
sudo ./setup-service.sh
```

### 3. `service-manager.sh`
Easy-to-use service management tool.

**Features:**
- ✅ Start/stop/restart service
- ✅ View logs
- ✅ Check status
- ✅ **Show current IP addresses** (important for AWS!)
- ✅ **Debug mode** - detailed diagnostics
- ✅ **Test environment** - verify all dependencies
- ✅ Enable/disable auto-start

**Usage:**
```bash
cd ~/ocr/voter_extraction_without_API/deployment
chmod +x service-manager.sh
./service-manager.sh [command]
```

**Most Useful Commands:**
```bash
# Get current public IP (use this after AWS restart!)
./service-manager.sh info

# Check if running
./service-manager.sh status

# Full diagnostic (if extraction not working)
./service-manager.sh debug

# Test all dependencies
./service-manager.sh test-env

# View logs
./service-manager.sh logs
```

### 4. `SERVICE_USAGE.md`
Complete guide for using the systemd service.

### 5. `EXTRACTION_FIX.md`
**Important!** Quick guide to fix extraction issues in systemd service.

### 6. `SYSTEMD_TROUBLESHOOTING.md`
Comprehensive troubleshooting guide for service issues.

### 7. `QUICK_REFERENCE.md`
Quick command reference card.

---

## 🚀 Quick Start

### First Time Setup

```bash
# 1. Navigate to deployment directory
cd ~/ocr/voter_extraction_without_API/deployment

# 2. Make scripts executable
chmod +x *.sh

# 3. Run setup (one-time)
sudo ./setup-service.sh
```

### Get Access URL

```bash
./service-manager.sh info
```

This shows your current public IP - use it to access the application!

---

## 🔄 After AWS Instance Stop/Start

Your public IP changes every time you stop and start your AWS instance.

**Quick Solution:**
```bash
cd ~/ocr/voter_extraction_without_API/deployment
./service-manager.sh info
```

The service should already be running (auto-starts on boot).  
Just note the new public IP and access it!

---

## 📋 What Changed?

### Updates Made:

1. **`voter-extraction.service`**
   - ✅ Fixed path from `/PythonData_From_data/` to correct structure
   - ✅ Now uses dynamic path: `/home/<USERNAME>/ocr/voter_extraction_without_API/`
   - ✅ Added HOST and PORT environment variables
   - ✅ Service auto-detects correct paths

2. **`setup-service.sh`**
   - ✅ Auto-detects project root (no hardcoded paths!)
   - ✅ Works wherever you place the project
   - ✅ Dynamically replaces all placeholders
   - ✅ Better error messages
   - ✅ Shows actual paths being used

3. **`service-manager.sh`**
   - ✅ Added `info` command to show current IPs
   - ✅ Auto-detects public IP (AWS metadata or external service)
   - ✅ Shows private IP for local network access
   - ✅ Displays current service status

4. **New: `SERVICE_USAGE.md`**
   - ✅ Complete usage guide
   - ✅ Troubleshooting tips
   - ✅ AWS-specific instructions

---

## 🎯 Why Use Systemd Service?

### Benefits vs Manual Running

| Feature | Manual | Systemd |
|---------|--------|---------|
| Runs in background | ❌ | ✅ |
| Survives SSH disconnect | ❌ | ✅ |
| Auto-start on boot | ❌ | ✅ |
| Auto-restart on crash | ❌ | ✅ |
| Easy log access | ❌ | ✅ |
| Status monitoring | ❌ | ✅ |

### Perfect for AWS!

- ✅ Service starts automatically when instance boots
- ✅ No need to manually start after reboot
- ✅ Can close SSH - service keeps running
- ✅ Easy to get current IP with `service-manager.sh info`

---

## 📱 Common Tasks

### After AWS Instance Restart
```bash
./service-manager.sh info
# Note the new public IP and access it
```

### Check if Running
```bash
./service-manager.sh status
```

### View Logs
```bash
./service-manager.sh logs
```

### Restart Service
```bash
./service-manager.sh restart
```

### Update Code
```bash
# After pulling new code:
./service-manager.sh restart
```

---

## 🛠️ Troubleshooting

### Service Won't Start

```bash
# Check what's wrong
sudo journalctl -u voter-extraction -n 50

# Re-run setup
sudo ./setup-service.sh
```

### Can't Access from Browser

**Checklist:**
1. ✅ Service running: `./service-manager.sh status`
2. ✅ Port 5000 open in AWS Security Group
3. ✅ Using correct public IP: `./service-manager.sh info`
4. ✅ Health check works: `curl http://localhost:5000/health`

### Port Already in Use

```bash
# Find what's using port 5000
sudo lsof -i:5000

# Kill it
sudo kill -9 <PID>

# Restart service
./service-manager.sh restart
```

---

## 📚 Additional Resources

- **Complete AWS Guide**: See `/AWS_DEPLOYMENT_GUIDE.md` in project root
- **Quick Start**: See `/AWS_QUICK_START.md` in project root
- **Service Usage**: See `SERVICE_USAGE.md` in this directory

---

## ✅ Summary

The systemd service is now fully configured for AWS with:
- ✅ Dynamic path detection
- ✅ Auto-start on boot
- ✅ Easy IP address lookup
- ✅ Simple management commands
- ✅ Works with changing AWS IPs

Just run `./service-manager.sh info` after each AWS restart to get your new public IP!
