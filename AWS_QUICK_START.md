# AWS Quick Start Guide

## 🚀 5-Minute Setup

### 1️⃣ Install Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv tesseract-ocr tesseract-ocr-hin curl
```

### 2️⃣ Open Port 5000 in AWS Security Group
1. AWS Console → EC2 → Security Groups
2. Select your instance's security group
3. Edit inbound rules → Add rule
4. **Type**: Custom TCP, **Port**: 5000, **Source**: `0.0.0.0/0`
5. Save rules

### 3️⃣ Start the Server
```bash
cd ~/voter_extraction_without_API
chmod +x scripts/start_server.sh
./scripts/start_server.sh
```

### 4️⃣ Note Your Public IP
The script will display:
```
Public IP:       http://13.201.89.53:5000
👉 Use the Public IP URL to access from your browser!
```

### 5️⃣ Access the Application
Open in your browser:
```
http://YOUR-PUBLIC-IP:5000
```

---

## 🔄 After Stop/Start Instance

```bash
# 1. SSH into instance with new public IP
ssh -i your-key.pem ubuntu@NEW-PUBLIC-IP

# 2. Start the server
cd ~/voter_extraction_without_API
./scripts/start_server.sh

# 3. Note the new public IP and access it
```

---

## 🛠️ Troubleshooting

### Can't Connect?
```bash
# Check server is running
curl http://localhost:5000/health

# Check port 5000 is listening
sudo netstat -tlnp | grep 5000

# Check server logs
tail -f backend/python-service/app.log
```

### Frontend Shows "Cannot connect to server"?
- ✅ Make sure you're using the **public IP**, not localhost
- ✅ Port 5000 is open in AWS Security Group
- ✅ Server is actually running (check logs)

---

## 📱 Keep Server Running After Disconnect

```bash
# Use screen
sudo apt install screen
screen -S voter-app
./scripts/start_server.sh

# Detach: Press Ctrl+A, then D
# Reattach later: screen -r voter-app
```

---

## 🆘 Need Help?

See full documentation: [AWS_DEPLOYMENT_GUIDE.md](./AWS_DEPLOYMENT_GUIDE.md)
