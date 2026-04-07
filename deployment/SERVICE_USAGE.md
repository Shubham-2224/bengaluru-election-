# Systemd Service Usage Guide

## 🚀 Running as a System Service

Instead of manually running the server every time, you can set it up as a systemd service that:
- ✅ Starts automatically on boot
- ✅ Restarts automatically if it crashes
- ✅ Runs in the background
- ✅ Easy to manage with simple commands

---

## 📋 One-Time Setup

### Install the Service

```bash
cd ~/ocr/voter_extraction_without_API/deployment
chmod +x setup-service.sh
sudo ./setup-service.sh
```

This script will:
1. Detect your project location automatically
2. Check all prerequisites
3. Create virtual environment if needed
4. Install and configure the systemd service
5. Enable auto-start on boot
6. Start the service immediately

**Note:** The script auto-detects paths, so it works regardless of where you've placed the project!

---

## 🎮 Managing the Service

### Quick Commands

Use the service manager script for easy management:

```bash
cd ~/ocr/voter_extraction_without_API/deployment
chmod +x service-manager.sh
./service-manager.sh [command]
```

### Available Commands

| Command | Description |
|---------|-------------|
| `start` | Start the service |
| `stop` | Stop the service |
| `restart` | Restart the service |
| `status` | Show detailed service status |
| `logs` | Show live logs (follow mode) |
| `logs-tail` | Show last 50 lines of logs |
| `enable` | Enable auto-start on boot |
| `disable` | Disable auto-start on boot |
| `check` | Check if running and port status |
| `info` | **Show access URLs with current IPs** |

---

## 📱 Getting Current IP Address

After restarting your AWS instance (when IP changes):

```bash
cd ~/ocr/voter_extraction_without_API/deployment
./service-manager.sh info
```

**Output Example:**
```
Service Information:
===================
Local URL:       http://localhost:5000
Private IP:      http://172.31.10.49:5000
Public IP:       http://13.201.89.53:5000

👉 Access from browser: http://13.201.89.53:5000

API Endpoints:
  Health:      /health
  Server Info: /api/server-info

Status: RUNNING
```

---

## 🔧 Direct Systemctl Commands

You can also use standard systemctl commands directly:

```bash
# Start service
sudo systemctl start voter-extraction

# Stop service
sudo systemctl stop voter-extraction

# Restart service
sudo systemctl restart voter-extraction

# Check status
sudo systemctl status voter-extraction

# View logs (live)
sudo journalctl -u voter-extraction -f

# View last 100 log lines
sudo journalctl -u voter-extraction -n 100

# Enable auto-start on boot
sudo systemctl enable voter-extraction

# Disable auto-start on boot
sudo systemctl disable voter-extraction
```

---

## 🔍 Troubleshooting

### Check if Service is Running

```bash
sudo systemctl status voter-extraction
```

Look for:
- **Active: active (running)** - Service is running ✅
- **Active: failed** - Service crashed ❌
- **Active: inactive (dead)** - Service is stopped ⚠️

### View Error Logs

```bash
# Last 50 lines
sudo journalctl -u voter-extraction -n 50

# Live logs
sudo journalctl -u voter-extraction -f

# All logs
sudo journalctl -u voter-extraction --no-pager
```

### Common Issues

#### Issue: Service fails to start

**Check logs:**
```bash
sudo journalctl -u voter-extraction -n 50
```

**Common causes:**
1. Port 5000 already in use
2. Python virtual environment not set up
3. Missing dependencies
4. Permission issues

**Solution:**
```bash
# Check port
sudo lsof -i:5000

# Re-run setup
cd ~/ocr/voter_extraction_without_API/deployment
sudo ./setup-service.sh
```

#### Issue: Service runs but can't access from browser

**Check:**
1. Service is running: `sudo systemctl status voter-extraction`
2. Port is listening: `sudo netstat -tlnp | grep 5000`
3. Security Group has port 5000 open
4. Using correct public IP: `./service-manager.sh info`

#### Issue: Service stops after a while

**Check resource usage:**
```bash
# Memory
free -h

# Disk space
df -h

# Service status
sudo systemctl status voter-extraction
```

**View crash logs:**
```bash
sudo journalctl -u voter-extraction --since "1 hour ago"
```

---

## 🔄 After AWS Instance Restart

When you stop and start your AWS instance (IP changes):

### Option 1: Using Service (Recommended)

```bash
# The service should auto-start on boot (if enabled)
# Just get the new IP:
cd ~/ocr/voter_extraction_without_API/deployment
./service-manager.sh info
```

### Option 2: Manual Restart

```bash
# If service didn't auto-start:
sudo systemctl start voter-extraction

# Get new IP
./service-manager.sh info
```

---

## 📊 Monitoring

### Real-Time Logs

```bash
sudo journalctl -u voter-extraction -f
```

### Check Resource Usage

```bash
# CPU and Memory
top -p $(pgrep -f "python3 app.py")

# Or use htop
htop -p $(pgrep -f "python3 app.py")
```

### Check Port Status

```bash
sudo lsof -i:5000
# or
sudo netstat -tlnp | grep 5000
```

---

## 🛡️ Security Notes

The service runs with these security settings:
- ✅ Runs as your user (not root)
- ✅ `NoNewPrivileges=true` - Cannot escalate privileges
- ✅ `PrivateTmp=true` - Isolated /tmp directory
- ✅ File descriptor limit: 65536

---

## 🔧 Updating the Application

When you update your code:

```bash
# 1. Stop the service
sudo systemctl stop voter-extraction

# 2. Update dependencies if needed
cd ~/ocr/voter_extraction_without_API/backend/python-service
source venv/bin/activate
pip install -r requirements.txt

# 3. Restart the service
sudo systemctl start voter-extraction

# Or just restart without stopping first:
sudo systemctl restart voter-extraction
```

---

## 📝 Configuration

### Environment Variables

Edit the service file if you need custom environment variables:

```bash
sudo nano /etc/systemd/system/voter-extraction.service
```

Add under `[Service]` section:
```ini
Environment="DEBUG=False"
Environment="FILE_RETENTION_HOURS=24"
Environment="ALLOWED_ORIGINS=*"
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart voter-extraction
```

### Using .env File

The service automatically loads `.env` from the application directory:

```bash
cd ~/ocr/voter_extraction_without_API/backend/python-service
nano .env
```

After editing:
```bash
sudo systemctl restart voter-extraction
```

---

## ✅ Service Benefits

| Feature | Manual Run | Systemd Service |
|---------|-----------|-----------------|
| Auto-start on boot | ❌ | ✅ |
| Auto-restart on crash | ❌ | ✅ |
| Runs in background | ❌ | ✅ |
| Survives SSH disconnect | ❌ | ✅ |
| Easy log management | ❌ | ✅ |
| Resource limits | ❌ | ✅ |
| Status monitoring | ❌ | ✅ |

---

## 🆘 Need Help?

1. **Check logs**: `sudo journalctl -u voter-extraction -n 100`
2. **Check status**: `sudo systemctl status voter-extraction`
3. **Test health**: `curl http://localhost:5000/health`
4. **Get IP info**: `./service-manager.sh info`

---

## 📚 Quick Reference Card

```bash
# Setup (one-time)
cd ~/ocr/voter_extraction_without_API/deployment
sudo ./setup-service.sh

# Get current IP (after reboot)
./service-manager.sh info

# Manage service
./service-manager.sh start|stop|restart|status|logs

# View logs
./service-manager.sh logs        # Live
./service-manager.sh logs-tail   # Last 50 lines

# Check everything
./service-manager.sh check
```

---

**Pro Tip:** After setting up the service, you can close your SSH session and the server will keep running!
