# 🔧 AWS Deployment Troubleshooting Guide

## Common Issues and Solutions

### 1. Curl Package Conflict (Amazon Linux 2023)

**Error:**
```
Transaction failed - conflicting packages
curl conflicts with curl-minimal-7.87.0
```

**Solution:**
The enhanced setup script now handles this automatically, but if you encounter it manually:

```bash
# Replace curl-minimal with full curl package
sudo dnf install -y --allowerasing curl

# Or remove curl from dependency list if not needed
sudo dnf install -y git python3 python3-pip python3-devel gcc gcc-c++ make wget htop
```

**Fixed in:** `setup-aws-enhanced.sh` lines 96-108

### 2. Services Fail to Start

**Check service status:**
```bash
sudo systemctl status qdrant vector-api vector-ui
```

**Common causes:**
- **Qdrant not ready:** API tries to connect before Qdrant starts
- **Port conflicts:** Another service using ports 6333, 8000, or 8501
- **Permission issues:** Incorrect user/group in systemd files

**Solutions:**
```bash
# Restart services in order
sudo systemctl restart qdrant
sleep 10
sudo systemctl restart vector-api
sleep 5  
sudo systemctl restart vector-ui

# Check port usage
sudo netstat -tulpn | grep -E "(6333|8000|8501)"

# Check logs
sudo journalctl -u qdrant -f
sudo journalctl -u vector-api -f
```

### 3. Memory Issues During Indexing

**Error:**
```
OOMKilled: Out of memory
RuntimeError: CUDA out of memory
```

**Solution:**
Reduce batch sizes in `.env`:
```bash
echo "EMBEDDING_BATCH_SIZE=512" >> .env
echo "UPLOAD_BATCH_SIZE=256" >> .env
echo "MAX_THREADS=2" >> .env

# Restart API service
sudo systemctl restart vector-api
```

### 4. Python Dependencies Installation Fails

**Error:**
```
Failed building wheel for some-package
```

**Solution:**
```bash
# Install development headers
sudo dnf install -y python3-devel gcc gcc-c++ make

# For scientific packages
sudo dnf install -y atlas-devel lapack-devel blas-devel

# Upgrade pip and try again
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --no-cache-dir
```

### 5. Connection Refused Errors

**Symptoms:**
- Cannot access services from browser
- `curl: (7) Failed to connect`

**Check:**
```bash
# Verify services are listening
sudo netstat -tulpn | grep -E "(6333|8000|8501)"

# Test local connectivity
curl http://localhost:6333/health
curl http://localhost:8000/health
curl -I http://localhost:8501

# Check AWS Security Group rules
# Make sure ports 22, 6333, 8000, 8501 are open
```

### 6. Streamlit Won't Load

**Common issues:**
- Streamlit takes longer to start than other services
- Browser cache issues
- Missing dependencies

**Solutions:**
```bash
# Wait longer for Streamlit to start (can take 30-60 seconds)
sleep 60
curl -I http://localhost:8501

# Clear browser cache and try again
# Try in incognito/private mode

# Check Streamlit logs
sudo journalctl -u vector-ui -n 50
```

### 7. Qdrant Storage Issues

**Error:**
```
Failed to create collection
Storage path not accessible
```

**Solution:**
```bash
# Check Qdrant data directory permissions
ls -la /var/lib/qdrant
sudo chown -R $USER:$USER /var/lib/qdrant
sudo chmod -R 755 /var/lib/qdrant

# Restart Qdrant
sudo systemctl restart qdrant
```

## Health Check Commands

Run these to diagnose issues:

```bash
# System resources
free -h
df -h
top

# Service status
sudo systemctl status qdrant vector-api vector-ui

# Network connectivity
curl http://localhost:6333/health
curl http://localhost:8000/health
curl -I http://localhost:8501

# Logs
sudo journalctl -u qdrant --no-pager -n 20
sudo journalctl -u vector-api --no-pager -n 20
sudo journalctl -u vector-ui --no-pager -n 20

# Process check
ps aux | grep -E "(qdrant|uvicorn|streamlit)" | grep -v grep
```

## Emergency Reset

If everything fails, use the cleanup script:

```bash
# Download and run cleanup
./cleanup-aws.sh

# Reboot instance
sudo reboot

# Re-run setup after reboot
./setup-aws-enhanced.sh
```

## Getting Help

1. **Check service logs first:** `sudo journalctl -u service-name -f`
2. **Verify ports are open:** Security Group rules in AWS Console
3. **Test locally:** `curl localhost:port` before testing remotely
4. **Check resources:** `free -h` and `df -h` for memory/disk issues
5. **Try health monitor:** `./health-monitor-enhanced.sh`

## Version Compatibility

- **Qdrant:** 1.15.0 (latest stable)
- **Python:** 3.8+ (Amazon Linux 2023 comes with 3.11)
- **FastAPI:** 0.104.0+
- **Streamlit:** 1.28.0+

If you encounter issues not covered here, check the enhanced health monitor output for specific error details.