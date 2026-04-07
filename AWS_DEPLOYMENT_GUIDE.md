# AWS EC2 Deployment Guide

## 🚀 Quick Setup for AWS Instances with Dynamic Public IPs

This application now automatically detects and adapts to your AWS instance's public IP address, making it perfect for EC2 instances where the public IP changes on every stop/start.

---

## ✅ What's Been Fixed

### Dynamic IP Detection
- **Frontend**: Automatically uses the current hostname/IP to connect to the backend
- **Backend**: Accepts connections from any origin (CORS configured)
- **Startup Script**: Detects and displays both private and public IPs

### Key Features
1. No hardcoded IPs - everything is dynamic
2. Works with changing AWS public IPs
3. Automatically detects AWS EC2 metadata
4. Falls back to external IP detection if not on AWS

---

## 📋 Prerequisites

### 1. AWS EC2 Instance
- Ubuntu 20.04+ or Amazon Linux 2
- At least 2 GB RAM (4 GB recommended)
- 10+ GB storage

### 2. Security Group Configuration
**IMPORTANT**: You must open port 5000 in your AWS Security Group:

1. Go to AWS Console → EC2 → Security Groups
2. Select your instance's security group
3. Click "Edit inbound rules"
4. Add a new rule:
   - **Type**: Custom TCP
   - **Port Range**: 5000
   - **Source**: 
     - `0.0.0.0/0` (allows access from anywhere) OR
     - Your specific IP address for security (e.g., `203.0.113.0/32`)
5. Click "Save rules"

---

## 🔧 Installation Steps

### Step 1: Connect to Your AWS Instance

```bash
ssh -i your-key.pem ubuntu@YOUR-PUBLIC-IP
```

### Step 2: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv tesseract-ocr tesseract-ocr-hin git curl

# Verify installations
python3 --version
tesseract --version
```

### Step 3: Clone/Upload Your Project

```bash
# If using git
git clone <your-repo-url>
cd voter_extraction_without_API

# OR upload files using scp from your local machine:
# scp -i your-key.pem -r /local/path/to/project ubuntu@YOUR-PUBLIC-IP:~/
```

### Step 4: Start the Server

```bash
cd ~/voter_extraction_without_API
chmod +x scripts/start_server.sh
./scripts/start_server.sh
```

The script will:
1. Create a Python virtual environment
2. Install all dependencies
3. Detect your public IP address
4. Start the Flask server
5. Display the correct URL to access

---

## 🌐 Accessing Your Application

### After Starting the Server

The startup script will display something like:

```
====================================================
   Server Information
====================================================
Local URL:       http://localhost:5000
Private IP:      http://172.31.10.49:5000
Public IP:       http://13.201.89.53:5000

👉 Use the Public IP URL to access from your browser!
====================================================
```

**Copy the Public IP URL** and open it in your browser:
```
http://YOUR-PUBLIC-IP:5000
```

The application will automatically connect to the correct backend URL!

---

## 🔄 Handling IP Changes

### When You Stop/Start Your Instance

1. **Stop the instance** (public IP is released)
2. **Start the instance** (new public IP is assigned)
3. **Run the startup script again**:
   ```bash
   cd ~/voter_extraction_without_API
   ./scripts/start_server.sh
   ```
4. **Note the new Public IP** displayed
5. **Access using the new IP**: `http://NEW-PUBLIC-IP:5000`

### Making It Easier

To avoid IP changes, consider:

1. **Elastic IP** (AWS feature):
   - Allocate an Elastic IP in AWS Console
   - Associate it with your instance
   - The IP remains the same even after stop/start
   - Note: There's a small charge if the IP is not associated with a running instance

2. **Domain Name**:
   - Use Route 53 or another DNS service
   - Point a domain to your instance
   - Access via: `http://yourdomain.com:5000`

---

## 🔒 Security Considerations

### Production Deployment

For production use, update the security settings:

1. **Restrict CORS Origins**:
   ```bash
   cd backend/python-service
   nano .env
   ```
   
   Add:
   ```
   ALLOWED_ORIGINS=http://YOUR-DOMAIN.com,http://YOUR-PUBLIC-IP:5000
   ```

2. **Use HTTPS** (Recommended):
   - Set up Nginx as a reverse proxy
   - Use Let's Encrypt for SSL certificates
   - Configure to forward port 443 → 5000

3. **Firewall Rules**:
   - Limit Security Group access to specific IPs
   - Use AWS VPC for network isolation

4. **Authentication**:
   - Enable API authentication in `.env`:
   ```
   AUTH_ENABLED=true
   API_KEYS=your-secret-key-here
   ```

---

## 🛠️ Troubleshooting

### Problem: Cannot Connect to Server

**Check 1**: Is the server running?
```bash
curl http://localhost:5000/health
```

**Check 2**: Is port 5000 open in Security Group?
- AWS Console → EC2 → Security Groups → Inbound Rules

**Check 3**: Check server logs
```bash
cd backend/python-service
tail -f app.log
```

### Problem: Frontend Shows "Cannot connect to server"

**Solution**: 
1. Open browser console (F12)
2. Check what URL it's trying to connect to
3. Make sure you're accessing via public IP, not localhost
4. Clear browser cache and reload

### Problem: Server Crashes or Out of Memory

**Solution**:
1. Check instance specs (need at least 2 GB RAM)
2. Monitor with: `htop` or `free -h`
3. Consider upgrading instance type

---

## 📊 API Endpoints

Once running, you can test these endpoints:

- **Health Check**: `http://YOUR-PUBLIC-IP:5000/health`
- **Server Info**: `http://YOUR-PUBLIC-IP:5000/api/server-info`
- **Frontend**: `http://YOUR-PUBLIC-IP:5000/`

### Server Info Endpoint

This endpoint returns current IP information:

```bash
curl http://YOUR-PUBLIC-IP:5000/api/server-info
```

Response:
```json
{
  "hostname": "ip-172-31-10-49",
  "private_ip": "172.31.10.49",
  "public_ip": "13.201.89.53",
  "port": 5000
}
```

---

## 🚀 Running as a System Service (Optional)

To keep the server running after you disconnect:

### Option 1: Using Screen

```bash
# Install screen
sudo apt install screen

# Start a screen session
screen -S voter-app

# Run the server
cd ~/voter_extraction_without_API
./scripts/start_server.sh

# Detach: Press Ctrl+A, then D
# Reattach later: screen -r voter-app
```

### Option 2: Using Systemd Service

```bash
# Use the provided service file
cd deployment
sudo ./setup-service.sh
```

This creates a systemd service that:
- Starts automatically on boot
- Restarts if it crashes
- Can be controlled with `systemctl`

Commands:
```bash
sudo systemctl start voter-extraction
sudo systemctl stop voter-extraction
sudo systemctl status voter-extraction
sudo systemctl enable voter-extraction  # Auto-start on boot
```

---

## 📝 Notes

1. **Public IP Changes**: Every time you stop and start your EC2 instance, the public IP changes. Note the new IP from the startup script.

2. **Port 5000**: Make sure this port is always open in your Security Group.

3. **File Storage**: Uploaded PDFs and generated Excel files are stored on the instance. They will persist unless you terminate the instance.

4. **Automatic Cleanup**: The application automatically cleans up old files after 24 hours (configurable in `.env`).

5. **Resource Usage**: Each PDF processing job can use significant CPU and memory. Monitor your instance resources.

---

## 🆘 Support

If you encounter issues:

1. Check the logs: `backend/python-service/app.log`
2. Verify Security Group settings
3. Test the health endpoint: `curl http://localhost:5000/health`
4. Review the startup script output for errors

---

## ✅ Summary

Your application is now configured to:
- ✅ Automatically detect current IP address
- ✅ Work with changing AWS public IPs
- ✅ Display the correct access URL on startup
- ✅ Accept connections from any IP (configurable)
- ✅ Provide server info via API endpoint

Just restart the application after any IP change, and you're good to go!
