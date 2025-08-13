# 🔒 AWS Security Group Setup Guide
## Complete Port Configuration for Vector Search Service

## 📋 Required Ports Overview

| **Service** | **Port** | **Protocol** | **Purpose** | **Access** |
|-------------|----------|--------------|-------------|------------|
| SSH | 22 | TCP | Server management | Your IP only |
| Qdrant API | 6333 | TCP | Vector database HTTP API | Public/Restricted |
| Qdrant gRPC | 6334 | TCP | Vector database gRPC (optional) | Internal only |
| FastAPI | 8000 | TCP | Search API service | Public/Restricted |
| Streamlit UI | 8501 | TCP | Web interface | Public/Restricted |
| HTTPS | 443 | TCP | SSL/TLS (optional) | Public |
| HTTP | 80 | TCP | HTTP redirect (optional) | Public |

---

## 🖥️ AWS Management Console Setup

### Step 1: Navigate to Security Groups

1. **Login to AWS Console** → **EC2 Service**
2. **Left sidebar** → **Network & Security** → **Security Groups**
3. **Click "Create security group"**

### Step 2: Basic Configuration

```
Security Group Name: vector-search-sg
Description: Security group for Vector Search Service with Qdrant, FastAPI, and Streamlit
VPC: [Select your VPC]
```

### Step 3: Inbound Rules Configuration

**Click "Add Rule" for each of the following:**

#### Rule 1: SSH Access (Essential)
```
Type: SSH
Protocol: TCP
Port Range: 22
Source: My IP (recommended) or Custom IP
Description: SSH access for server management
```

#### Rule 2: Qdrant API (Essential)
```
Type: Custom TCP
Protocol: TCP
Port Range: 6333
Source: 0.0.0.0/0 (or specific IPs for security)
Description: Qdrant vector database API
```

#### Rule 3: FastAPI Service (Essential)
```
Type: Custom TCP
Protocol: TCP
Port Range: 8000
Source: 0.0.0.0/0 (or specific IPs for security)
Description: Vector Search API service
```

#### Rule 4: Streamlit UI (Essential)
```
Type: Custom TCP
Protocol: TCP
Port Range: 8501
Source: 0.0.0.0/0 (or specific IPs for security)
Description: Search web interface
```

#### Rule 5: Qdrant gRPC (Optional - for advanced usage)
```
Type: Custom TCP
Protocol: TCP
Port Range: 6334
Source: Custom - Security Group ID (self-reference)
Description: Qdrant gRPC internal communication
```

#### Rule 6: HTTPS (Optional - for production)
```
Type: HTTPS
Protocol: TCP
Port Range: 443
Source: 0.0.0.0/0
Description: HTTPS traffic (with SSL certificate)
```

#### Rule 7: HTTP (Optional - for redirect to HTTPS)
```
Type: HTTP
Protocol: TCP
Port Range: 80
Source: 0.0.0.0/0
Description: HTTP traffic (redirect to HTTPS)
```

### Step 4: Outbound Rules

**Default outbound rules are usually sufficient, but you can restrict if needed:**

#### Allow All Outbound (Default - Recommended)
```
Type: All traffic
Protocol: All
Port Range: All
Destination: 0.0.0.0/0
Description: All outbound traffic
```

#### Or Specific Outbound Rules (Advanced)
```
Type: HTTPS
Protocol: TCP
Port Range: 443
Destination: 0.0.0.0/0
Description: HTTPS for package downloads

Type: HTTP
Protocol: TCP
Port Range: 80
Destination: 0.0.0.0/0
Description: HTTP for package downloads

Type: Custom TCP
Protocol: TCP
Port Range: 53
Destination: 0.0.0.0/0
Description: DNS resolution
```

---

## 🛡️ Security Configurations

### Option 1: Open Access (Development/Demo)
```
Inbound Rules:
✅ SSH (22) - My IP
✅ Qdrant (6333) - 0.0.0.0/0
✅ API (8000) - 0.0.0.0/0
✅ UI (8501) - 0.0.0.0/0
```
**Use Case:** Testing, development, demos
**Risk:** Medium - Services are publicly accessible

### Option 2: Restricted Access (Recommended)
```
Inbound Rules:
✅ SSH (22) - Your IP only
✅ Qdrant (6333) - Your company's IP range
✅ API (8000) - Your company's IP range
✅ UI (8501) - Your company's IP range
```
**Use Case:** Internal company use, limited external access
**Risk:** Low - Access limited to known IPs

### Option 3: Load Balancer Setup (Production)
```
Inbound Rules:
✅ SSH (22) - Your IP only
✅ Qdrant (6333) - Security Group of Load Balancer
✅ API (8000) - Security Group of Load Balancer
✅ UI (8501) - Security Group of Load Balancer
✅ HTTPS (443) - 0.0.0.0/0 (through Load Balancer)
✅ HTTP (80) - 0.0.0.0/0 (redirect to HTTPS)
```
**Use Case:** Production with load balancer and SSL
**Risk:** Very Low - Public access only through secured load balancer

---

## 🔧 Testing Port Configuration

### After Creating Security Group:

1. **Launch EC2 Instance** with the new security group
2. **Test each port** from your local machine:

```bash
# Test SSH (should work)
ssh -i your-key.pem ec2-user@your-ec2-ip

# Test Qdrant (after service starts)
curl http://your-ec2-ip:6333/health

# Test FastAPI (after service starts)
curl http://your-ec2-ip:8000/health

# Test Streamlit UI (after service starts)
curl -I http://your-ec2-ip:8501

# Test from browser
# Open: http://your-ec2-ip:8501
```

### Port Testing Script:

```bash
#!/bin/bash
# Port connectivity test script

EC2_IP="your-ec2-public-ip"
PORTS="22 6333 8000 8501"

echo "Testing port connectivity to $EC2_IP"
echo "======================================"

for port in $PORTS; do
    if nc -z -v -w5 $EC2_IP $port 2>/dev/null; then
        echo "✅ Port $port: OPEN"
    else
        echo "❌ Port $port: CLOSED/FILTERED"
    fi
done

echo
echo "Service-specific tests:"
echo "======================"

# Test Qdrant
if curl -s --max-time 5 http://$EC2_IP:6333/health > /dev/null 2>&1; then
    echo "✅ Qdrant (6333): Service responding"
else
    echo "❌ Qdrant (6333): Service not responding"
fi

# Test FastAPI
if curl -s --max-time 5 http://$EC2_IP:8000/health > /dev/null 2>&1; then
    echo "✅ FastAPI (8000): Service responding"
else
    echo "❌ FastAPI (8000): Service not responding"
fi

# Test Streamlit
if curl -s --max-time 5 -I http://$EC2_IP:8501 | grep -q "200 OK"; then
    echo "✅ Streamlit (8501): Service responding"
else
    echo "❌ Streamlit (8501): Service not responding"
fi
```

---

## 🚨 Common Issues & Solutions

### Issue 1: "Connection Refused" Errors

**Symptoms:**
```
curl: (7) Failed to connect to x.x.x.x port 8000: Connection refused
```

**Solutions:**
1. **Check Security Group:** Ensure the port is open in AWS Security Group
2. **Check Service Status:** `sudo systemctl status vector-api`
3. **Check Port Binding:** `netstat -tulpn | grep :8000`
4. **Check Firewall:** `sudo firewall-cmd --list-ports` (if firewalld is enabled)

### Issue 2: "Connection Timeout" Errors

**Symptoms:**
```
curl: (28) Failed to connect to x.x.x.x port 8000: Connection timed out
```

**Solutions:**
1. **Security Group:** Port not open in AWS Security Group
2. **Service Not Started:** Service might not be running
3. **Wrong IP:** Using private IP instead of public IP

### Issue 3: SSH Connection Issues

**Symptoms:**
```
ssh: connect to host x.x.x.x port 22: Connection refused
```

**Solutions:**
1. **Security Group:** SSH port (22) not open for your IP
2. **Key Permissions:** `chmod 400 your-key.pem`
3. **Wrong Username:** Use `ec2-user` for Amazon Linux, `ubuntu` for Ubuntu

### Issue 4: Services Start But Not Accessible

**Check List:**
```bash
# 1. Verify services are running
sudo systemctl status qdrant vector-api vector-ui

# 2. Check listening ports
sudo netstat -tulpn | grep -E "(6333|8000|8501)"

# 3. Check service logs
sudo journalctl -u vector-api -n 20
sudo journalctl -u qdrant -n 20

# 4. Test local connectivity
curl http://localhost:8000/health
curl http://localhost:6333/health

# 5. Check for binding issues
grep -r "host.*0.0.0.0" /etc/systemd/system/vector-*.service
```

---

## 🎯 Security Group Templates

### Copy-Paste Ready Configurations:

#### Template 1: Development/Testing
```json
{
  "GroupName": "vector-search-dev",
  "Description": "Vector Search Service - Development",
  "SecurityGroupRules": [
    {
      "IpPermissions": [
        {
          "IpProtocol": "tcp",
          "FromPort": 22,
          "ToPort": 22,
          "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "SSH access"}]
        },
        {
          "IpProtocol": "tcp",
          "FromPort": 6333,
          "ToPort": 6333,
          "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Qdrant API"}]
        },
        {
          "IpProtocol": "tcp",
          "FromPort": 8000,
          "ToPort": 8000,
          "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "FastAPI service"}]
        },
        {
          "IpProtocol": "tcp",
          "FromPort": 8501,
          "ToPort": 8501,
          "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Streamlit UI"}]
        }
      ]
    }
  ]
}
```

#### Template 2: Production (Replace x.x.x.x with your IP)
```json
{
  "GroupName": "vector-search-prod",
  "Description": "Vector Search Service - Production",
  "SecurityGroupRules": [
    {
      "IpPermissions": [
        {
          "IpProtocol": "tcp",
          "FromPort": 22,
          "ToPort": 22,
          "IpRanges": [{"CidrIp": "x.x.x.x/32", "Description": "SSH - Admin IP only"}]
        },
        {
          "IpProtocol": "tcp",
          "FromPort": 443,
          "ToPort": 443,
          "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTPS"}]
        },
        {
          "IpProtocol": "tcp",
          "FromPort": 80,
          "ToPort": 80,
          "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTP redirect"}]
        }
      ]
    }
  ]
}
```

---

## ✅ Final Verification Checklist

- [ ] Security Group created with correct name and description
- [ ] SSH port (22) open for your IP address
- [ ] Qdrant port (6333) open for required access
- [ ] FastAPI port (8000) open for required access
- [ ] Streamlit port (8501) open for required access
- [ ] Outbound rules allow necessary traffic
- [ ] Security Group attached to EC2 instance
- [ ] Port connectivity tested from external machine
- [ ] Services responding to health checks
- [ ] Web UI accessible from browser

**🎉 Your AWS Security Group is now properly configured for the Vector Search Service with parallel embedding generation and multi-mode support!**