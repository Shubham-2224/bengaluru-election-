# Dynamic IP Address Support - Update Summary

## 🎯 Problem Solved

Your application was hardcoded to use `localhost:5000`, which doesn't work when:
- Running on AWS EC2 instances
- Accessing from a remote browser
- The public IP changes when you stop/start the instance

## ✅ Changes Made

### 1. Frontend - Dynamic API URL Detection (`frontend/js/api.js`)

**Before:**
```javascript
const API_BASE_URL = 'http://localhost:5000/api';
```

**After:**
```javascript
// Dynamically determine API URL based on current hostname
const getAPIBaseURL = () => {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    
    // If accessed via localhost, use localhost
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:5000/api';
    }
    
    // Otherwise use current hostname (works for AWS public IPs and domains)
    return `${protocol}//${hostname}:5000/api`;
};

const API_BASE_URL = getAPIBaseURL();
```

**What this does:**
- When you access via `http://localhost:5000` → connects to `localhost:5000`
- When you access via `http://13.201.89.53:5000` → connects to `13.201.89.53:5000`
- Automatically adapts to any IP or domain name!

### 2. Backend - Allow All Origins (`backend/python-service/app.py`)

**Before:**
```python
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
CORS(app, origins=ALLOWED_ORIGINS)
```

**After:**
```python
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*')
if ALLOWED_ORIGINS == '*':
    CORS(app, resources={r"/*": {"origins": "*"}})
else:
    CORS(app, origins=ALLOWED_ORIGINS.split(','))
```

**What this does:**
- By default, allows connections from any IP address
- Can still be restricted by setting `ALLOWED_ORIGINS` in `.env` file
- Perfect for AWS instances with changing IPs

### 3. New API Endpoint - Server Info (`backend/python-service/app.py`)

**New Endpoint:** `GET /api/server-info`

```python
@app.route('/api/server-info', methods=['GET'])
def server_info():
    """Get server information including IP addresses"""
    # Returns current public IP, private IP, hostname, and port
```

**Example Response:**
```json
{
  "hostname": "ip-172-31-10-49",
  "private_ip": "172.31.10.49",
  "public_ip": "13.201.89.53",
  "port": 5000
}
```

**What this does:**
- Automatically detects AWS EC2 metadata
- Falls back to external IP detection services
- Provides all IP information in one place

### 4. Enhanced Startup Script (`scripts/start_server.sh`)

**New Features:**
- Automatically detects private IP address
- Automatically detects public IP address (AWS EC2 metadata or external service)
- Displays all connection URLs clearly
- Shows which URL to use for remote access

**Example Output:**
```
====================================================
   Server Information
====================================================
Local URL:       http://localhost:5000
Private IP:      http://172.31.10.49:5000
Public IP:       http://13.201.89.53:5000

👉 Use the Public IP URL to access from your browser!

Frontend:        /index.html (or just /)
API Health:      /health
Server Info:     /api/server-info
====================================================
```

### 5. Configuration Updates

**`backend/python-service/config.py`:**
- Changed default `ALLOWED_ORIGINS` to `*`
- Added documentation about production security

**`backend/python-service/env.example.txt`:**
- Updated with new default CORS settings
- Added comments about AWS deployment

### 6. New Documentation

**Created:**
- `AWS_DEPLOYMENT_GUIDE.md` - Comprehensive AWS setup guide
- `AWS_QUICK_START.md` - 5-minute quick start guide
- `DYNAMIC_IP_UPDATE.md` - This file

---

## 🚀 How to Use

### First Time Setup

1. **Open Port 5000 in AWS Security Group**
   - AWS Console → EC2 → Security Groups
   - Add inbound rule: TCP port 5000 from `0.0.0.0/0`

2. **Start the Server**
   ```bash
   cd ~/voter_extraction_without_API
   ./scripts/start_server.sh
   ```

3. **Note the Public IP** displayed in the output

4. **Access via Public IP**
   ```
   http://YOUR-PUBLIC-IP:5000
   ```

### After Stop/Start Instance

1. **Connect to instance** (public IP has changed)
   ```bash
   ssh -i your-key.pem ubuntu@NEW-PUBLIC-IP
   ```

2. **Restart server** (it will detect the new IP)
   ```bash
   cd ~/voter_extraction_without_API
   ./scripts/start_server.sh
   ```

3. **Note the new Public IP** and access it

---

## 🔧 Technical Details

### How Frontend Detection Works

1. Frontend JavaScript checks `window.location.hostname`
2. If it's `localhost` or `127.0.0.1`, uses `localhost:5000`
3. Otherwise, uses the current hostname/IP with port 5000
4. This works for:
   - AWS public IPs: `http://13.201.89.53:5000`
   - Domain names: `http://yourdomain.com:5000`
   - Private IPs: `http://192.168.1.100:5000`

### How IP Detection Works

**Priority order:**

1. **AWS EC2 Metadata Service** (fastest, most reliable on AWS)
   - Endpoint: `http://169.254.169.254/latest/meta-data/public-ipv4`
   - Only works on EC2 instances
   - 1-second timeout

2. **External IP Service** (fallback)
   - Endpoint: `https://api.ipify.org`
   - Works anywhere with internet access
   - 2-second timeout

3. **Private IP Detection**
   - Uses system socket to determine local network IP
   - Always available

### Security Considerations

**Current Setup (Development-Friendly):**
- ✅ Works with any IP address
- ✅ No configuration needed
- ⚠️  Anyone can access if they know your IP
- ⚠️  CORS allows all origins

**Production Setup (Recommended):**

Create `.env` file:
```bash
# Restrict to specific domains/IPs
ALLOWED_ORIGINS=http://yourdomain.com,http://13.201.89.53:5000

# Enable authentication
AUTH_ENABLED=true
API_KEYS=your-secret-key-here

# Use HTTPS
# (requires Nginx + SSL certificate setup)
```

---

## 🧪 Testing

### Test Health Endpoint
```bash
curl http://YOUR-PUBLIC-IP:5000/health
```

Expected response:
```json
{
  "status": "ok",
  "message": "Python extraction service running",
  "disk_space_mb": 15234.56
}
```

### Test Server Info Endpoint
```bash
curl http://YOUR-PUBLIC-IP:5000/api/server-info
```

Expected response:
```json
{
  "hostname": "ip-172-31-10-49",
  "private_ip": "172.31.10.49",
  "public_ip": "13.201.89.53",
  "port": 5000
}
```

### Test Frontend
1. Open browser to: `http://YOUR-PUBLIC-IP:5000`
2. Should see the voter extraction interface
3. Try uploading a PDF
4. Check browser console (F12) - should show no connection errors

---

## 🎯 Benefits

### Before
- ❌ Hardcoded to localhost only
- ❌ Had to manually update IPs in code
- ❌ Didn't work on AWS without code changes
- ❌ CORS blocked external access

### After
- ✅ Automatically detects current IP
- ✅ Works with any IP or domain
- ✅ Perfect for AWS instances
- ✅ No code changes needed when IP changes
- ✅ CORS configured for external access
- ✅ Startup script shows correct URLs
- ✅ API endpoint provides server info

---

## 📋 Files Modified

| File | Changes |
|------|---------|
| `frontend/js/api.js` | Dynamic URL detection for all API calls |
| `backend/python-service/app.py` | CORS configuration, new server-info endpoint |
| `backend/python-service/config.py` | Updated default CORS settings |
| `backend/python-service/env.example.txt` | Updated documentation |
| `scripts/start_server.sh` | IP detection and display |

## 📄 Files Created

| File | Purpose |
|------|---------|
| `AWS_DEPLOYMENT_GUIDE.md` | Complete AWS deployment guide |
| `AWS_QUICK_START.md` | Quick 5-minute setup guide |
| `DYNAMIC_IP_UPDATE.md` | This summary document |

---

## 🆘 Troubleshooting

### Issue: Frontend shows "Cannot connect to server"

**Solutions:**
1. Make sure you're using the public IP, not localhost
2. Check Security Group has port 5000 open
3. Verify server is running: `curl http://localhost:5000/health`
4. Check browser console for actual error
5. Clear browser cache

### Issue: Server starts but can't access from browser

**Solutions:**
1. Verify Security Group inbound rules
2. Check server is listening on `0.0.0.0`: `netstat -tlnp | grep 5000`
3. Try accessing health endpoint: `http://PUBLIC-IP:5000/health`
4. Check firewall: `sudo ufw status`

### Issue: Can't detect public IP

**Solutions:**
1. On AWS, check instance has public IP assigned
2. Verify internet connectivity: `curl https://api.ipify.org`
3. Check metadata service: `curl http://169.254.169.254/latest/meta-data/public-ipv4`

---

## ✅ Summary

Your application now:
- **Automatically adapts** to the current IP address
- **Works seamlessly** on AWS instances with changing IPs
- **Displays correct URLs** on startup
- **Accepts connections** from any IP (configurable)
- **Provides API** to query current server info

No more hardcoded IPs! Just restart the server after any IP change and access via the new IP. 🎉
