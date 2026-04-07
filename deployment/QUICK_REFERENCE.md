# Quick Reference Card

## 🚀 First Time Setup

```bash
cd ~/ocr/voter_extraction_without_API/deployment
sudo ./setup-service.sh
./service-manager.sh info
```

## 🔄 After AWS Restart (IP Changed)

```bash
cd ~/ocr/voter_extraction_without_API/deployment
./service-manager.sh info
```
**Service auto-starts. Just note the new IP!**

## 📱 Common Commands

```bash
# Get current IPs
./service-manager.sh info

# Check if running
./service-manager.sh status

# Restart
./service-manager.sh restart

# View logs
./service-manager.sh logs
```

## 🆘 Troubleshooting

```bash
# Check logs
sudo journalctl -u voter-extraction -n 50

# Re-install
sudo ./setup-service.sh

# Check port
sudo lsof -i:5000
```

## ✅ Checklist

- [ ] Port 5000 open in AWS Security Group
- [ ] Service installed: `sudo systemctl status voter-extraction`
- [ ] Auto-start enabled: `sudo systemctl is-enabled voter-extraction`
- [ ] Public IP noted: `./service-manager.sh info`
- [ ] Browser access works: `http://PUBLIC-IP:5000`

---

**That's it! Simple and effective.** 🎉
