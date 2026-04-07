# 🔧 Fix: Extraction Works in Shell but Not in Systemd Service

## ❌ Problem

- Running with `./scripts/start_server.sh` → ✅ Extraction works
- Running with systemd service → ❌ No records extracted

## 🎯 Root Cause

The systemd service was running with:
- **Incomplete PATH** - Couldn't find `tesseract` binary
- **PrivateTmp enabled** - Isolated /tmp prevented OCR temp files
- **Missing .env** - Environment variables not loaded

## ✅ The Fix (Already Applied)

The service file has been updated with:

1. **Full System PATH** - Includes `/usr/bin` where tesseract lives
2. **EnvironmentFile** - Loads `.env` automatically
3. **PrivateTmp disabled** - Allows OCR to create temp files
4. **PYTHONUNBUFFERED** - Better logging

---

## 🚀 Apply the Fix Now

### Step 1: Re-install the Service

```bash
cd ~/ocr/voter_extraction_without_API/deployment
sudo ./setup-service.sh
```

This will install the updated service configuration.

### Step 2: Verify Installation

```bash
./service-manager.sh test-env
```

Check that all items show ✓ (green checkmarks), especially:
- ✓ Tesseract
- ✓ Python3
- ✓ Virtual environment
- ✓ All Python imports

### Step 3: Restart the Service

```bash
./service-manager.sh restart
```

### Step 4: Test Extraction

1. Get your access URL:
   ```bash
   ./service-manager.sh info
   ```

2. Open the public IP URL in browser

3. Upload a test PDF

4. Check if extraction returns records > 0

5. Verify Excel file is generated

---

## 🔍 Verification Commands

### Check if Service is Running
```bash
./service-manager.sh status
```

### View Live Logs (watch for errors)
```bash
./service-manager.sh logs
```

### Run Full Diagnostic
```bash
./service-manager.sh debug
```

---

## 📊 What Changed in Service File

### Before:
```ini
Environment="PATH=/home/<user>/.../venv/bin"
PrivateTmp=true
# No EnvironmentFile
```

### After:
```ini
# Full system PATH
Environment="PATH=/home/<user>/.../venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Load .env file
EnvironmentFile=-/home/<user>/.../backend/python-service/.env

# Allow temp file access
# PrivateTmp=false  (commented out = disabled)

# Unbuffered logging
Environment="PYTHONUNBUFFERED=1"
```

---

## 🧪 Test Results

After applying the fix, you should see:

| Test | Expected Result |
|------|-----------------|
| Service starts | ✅ Active (running) |
| Tesseract found | ✅ In PATH |
| PDF upload | ✅ Succeeds |
| OCR processing | ✅ Runs |
| Record extraction | ✅ Records > 0 |
| Excel generation | ✅ File created |
| Download works | ✅ Excel downloads |

---

## 🐛 Troubleshooting

### Still No Records After Fix?

```bash
# 1. Check detailed logs
./service-manager.sh debug

# 2. Look for specific errors
sudo journalctl -u voter-extraction -n 100 | grep -i error

# 3. Test environment
./service-manager.sh test-env

# 4. Compare with manual run
./service-manager.sh stop
cd ~/ocr/voter_extraction_without_API
./scripts/start_server.sh
# Test extraction manually
```

### See Tesseract Errors?

```bash
# Verify tesseract is installed
which tesseract
tesseract --version

# Check service can see it
./service-manager.sh test-env
```

### Module Import Errors?

```bash
# Reinstall dependencies
cd ~/ocr/voter_extraction_without_API/backend/python-service
source venv/bin/activate
pip install --upgrade -r requirements.txt
deactivate

# Restart service
cd ~/ocr/voter_extraction_without_API/deployment
./service-manager.sh restart
```

---

## 📝 Detailed Troubleshooting

See: [SYSTEMD_TROUBLESHOOTING.md](./SYSTEMD_TROUBLESHOOTING.md)

---

## ✅ Success Indicator

When extraction is working, your logs should show:

```
INFO - Processing PDF: filename.pdf
INFO - Extracted X records from Y pages
INFO - Generated Excel file: abc123.xlsx
```

Not:
```
INFO - Extracted 0 records
```

---

## 🎉 Done!

After applying this fix:
- ✅ Service has full environment access
- ✅ Tesseract binary is found
- ✅ OCR temp files work
- ✅ .env variables loaded
- ✅ Extraction works same as manual run

**Quick Command:**
```bash
cd ~/ocr/voter_extraction_without_API/deployment
sudo ./setup-service.sh && ./service-manager.sh info
```

Then test extraction via the public IP!
