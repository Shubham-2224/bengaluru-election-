# Systemd Service Troubleshooting Guide

## 🔍 Problem: Data Extraction Works with `./start_server.sh` but NOT with Systemd Service

This is a common issue caused by environment differences between your shell and the systemd service.

---

## ✅ Solution - Update Required

The service file has been updated to fix:

1. **PATH Environment** - Now includes system binaries (`/usr/bin` for tesseract, etc.)
2. **Environment File** - Now loads `.env` file automatically
3. **PrivateTmp** - Disabled to allow temp file access for OCR
4. **PYTHONUNBUFFERED** - Added for proper logging

### Apply the Fix:

```bash
cd ~/ocr/voter_extraction_without_API/deployment

# Re-install the service with the fix
sudo ./setup-service.sh

# Restart the service
./service-manager.sh restart

# Check if it's working
./service-manager.sh debug
```

---

## 🔧 Diagnostic Commands

### 1. Check Service Status

```bash
cd ~/ocr/voter_extraction_without_API/deployment
./service-manager.sh status
```

### 2. Run Full Debug Check

```bash
./service-manager.sh debug
```

This shows:
- Service status
- Recent logs
- Environment variables
- Working directory
- Port status
- Process information

### 3. Test Environment Dependencies

```bash
./service-manager.sh test-env
```

This checks:
- Python availability
- Tesseract OCR installation
- Virtual environment
- Required directories
- Python module imports

### 4. View Live Logs

```bash
./service-manager.sh logs
```

Watch for extraction errors in real-time.

---

## 🐛 Common Issues & Solutions

### Issue 1: "tesseract: command not found"

**Symptom:** Logs show tesseract cannot be found

**Cause:** PATH doesn't include `/usr/bin`

**Solution:**
```bash
# Check if tesseract is installed
which tesseract

# If found, re-install service
cd ~/ocr/voter_extraction_without_API/deployment
sudo ./setup-service.sh
```

### Issue 2: No Records Extracted (No Error)

**Symptom:** Service runs but extraction returns 0 records

**Possible Causes:**
1. Tesseract not accessible
2. Temp files can't be created
3. Working directory wrong
4. Environment variables missing

**Solution:**
```bash
# Run environment test
./service-manager.sh test-env

# Check for errors
./service-manager.sh debug

# Re-install service
sudo ./setup-service.sh
```

### Issue 3: Module Import Errors

**Symptom:** Logs show "ModuleNotFoundError" or "ImportError"

**Cause:** Virtual environment not activated or dependencies missing

**Solution:**
```bash
# Reinstall dependencies
cd ~/ocr/voter_extraction_without_API/backend/python-service
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Restart service
cd ~/ocr/voter_extraction_without_API/deployment
./service-manager.sh restart
```

### Issue 4: Permission Denied

**Symptom:** Logs show permission errors for uploads/outputs

**Cause:** Service user doesn't have write permission

**Solution:**
```bash
cd ~/ocr/voter_extraction_without_API/backend/python-service

# Fix permissions
chmod 755 uploads outputs
chown $USER:$USER uploads outputs

# Restart service
cd ~/ocr/voter_extraction_without_API/deployment
./service-manager.sh restart
```

### Issue 5: .env File Not Loaded

**Symptom:** Azure API features don't work (AI formatting, Azure Vision)

**Cause:** .env file not found or not loaded

**Solution:**
```bash
cd ~/ocr/voter_extraction_without_API/backend/python-service

# Create .env from example
cp env.example.txt .env
nano .env  # Edit with your API keys

# Re-install service
cd ~/ocr/voter_extraction_without_API/deployment
sudo ./setup-service.sh
```

---

## 📊 Comparing Environments

### What's Different Between Shell and Systemd?

| Aspect | Shell (./start_server.sh) | Systemd Service |
|--------|---------------------------|-----------------|
| PATH | Full user PATH + venv | Must be explicitly set |
| Environment | All user env vars | Only what's defined |
| .env file | Auto-loaded by Python | Must be in EnvironmentFile |
| Working Dir | Script sets it | Must be in WorkingDirectory |
| Temp files | Uses /tmp | Uses PrivateTmp if enabled |
| User | Your user | Specified in User= |
| Shell | Full shell environment | Minimal environment |

### The Fix Applied:

```ini
# Full system PATH
Environment="PATH=/home/<user>/ocr/.../venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Load .env file
EnvironmentFile=-/home/<user>/ocr/.../backend/python-service/.env

# Allow shared /tmp access
# PrivateTmp=false

# Unbuffered Python output for logs
Environment="PYTHONUNBUFFERED=1"
```

---

## 🧪 Testing Extraction

### Test via API (Service Running)

```bash
# Start service
./service-manager.sh start

# Get public IP
./service-manager.sh info

# Upload a test PDF via browser
# Check if extraction works
```

### Compare with Manual Run

```bash
# Stop service first
./service-manager.sh stop

# Run manually
cd ~/ocr/voter_extraction_without_API
./scripts/start_server.sh

# Test extraction
# Compare results
```

---

## 📝 Logging & Monitoring

### Enable Verbose Logging

Create/edit `.env`:

```bash
cd ~/ocr/voter_extraction_without_API/backend/python-service
nano .env
```

Add:
```
LOG_LEVEL=INFO
ENABLE_CONSOLE_LOG=true
```

Restart service:
```bash
cd ~/ocr/voter_extraction_without_API/deployment
./service-manager.sh restart
./service-manager.sh logs
```

### Check Application Logs

```bash
# Application log file
tail -f ~/ocr/voter_extraction_without_API/backend/python-service/app.log

# Systemd journal
sudo journalctl -u voter-extraction -f

# Both at once (two terminals)
```

---

## 🔬 Deep Debugging

### 1. Test Tesseract from Service Environment

```bash
# Check what the service sees
sudo -u $USER env -i \
  PATH=/home/$USER/ocr/voter_extraction_without_API/backend/python-service/venv/bin:/usr/bin:/bin \
  which tesseract
```

### 2. Test Python Import from Service Environment

```bash
cd ~/ocr/voter_extraction_without_API/backend/python-service

# Simulate service environment
sudo -u $USER env -i \
  PATH=/home/$USER/ocr/voter_extraction_without_API/backend/python-service/venv/bin:/usr/bin:/bin \
  WorkingDirectory=/home/$USER/ocr/voter_extraction_without_API/backend/python-service \
  venv/bin/python3 -c "import pytesseract; print('OK')"
```

### 3. Test OCR Directly

```bash
cd ~/ocr/voter_extraction_without_API/backend/python-service
source venv/bin/activate

# Test OCR processor
python3 -c "
from ocr_processor_400dpi import OCRProcessor400DPI
processor = OCRProcessor400DPI()
print('OCR Processor initialized successfully')
"
```

---

## ✅ Verification Checklist

After applying the fix:

- [ ] Service starts: `./service-manager.sh status`
- [ ] No errors in logs: `./service-manager.sh logs-tail`
- [ ] Tesseract found: `./service-manager.sh test-env`
- [ ] Port 5000 listening: `./service-manager.sh check`
- [ ] Health endpoint works: `curl http://localhost:5000/health`
- [ ] PDF upload works via browser
- [ ] Extraction returns records (> 0)
- [ ] Excel file generated
- [ ] Excel download works

---

## 🆘 Still Not Working?

### Collect Debug Info:

```bash
cd ~/ocr/voter_extraction_without_API/deployment

# Create debug report
{
  echo "=== System Info ==="
  uname -a
  echo ""
  
  echo "=== Service Status ==="
  sudo systemctl status voter-extraction --no-pager -l
  echo ""
  
  echo "=== Environment Test ==="
  ./service-manager.sh test-env
  echo ""
  
  echo "=== Recent Logs ==="
  sudo journalctl -u voter-extraction -n 100 --no-pager
  echo ""
  
  echo "=== Service Configuration ==="
  sudo cat /etc/systemd/system/voter-extraction.service
  echo ""
  
} > debug-report.txt

echo "Debug report saved to debug-report.txt"
```

### Compare Environments:

```bash
# Check what start_server.sh has
echo $PATH

# Check what service has
sudo systemctl show voter-extraction --property=Environment
```

---

## 📚 Additional Resources

- **Service Manager**: `./service-manager.sh help`
- **Main AWS Guide**: `../AWS_DEPLOYMENT_GUIDE.md`
- **Service Usage**: `./SERVICE_USAGE.md`
- **Quick Reference**: `./QUICK_REFERENCE.md`

---

## 💡 Pro Tips

1. **Always check logs first**: `./service-manager.sh logs-tail`
2. **Test environment**: Run `./service-manager.sh test-env` after setup
3. **Compare with manual**: If service fails but manual works, it's environment
4. **Use debug mode**: Add `DEBUG=true` to `.env` for verbose logging
5. **Check permissions**: Service must read uploads, write outputs

---

**Remember:** The service runs in a minimal environment. What works in your shell might not work in systemd without proper configuration!
