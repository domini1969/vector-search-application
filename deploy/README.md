# 🚀 Deployment Scripts

**Clean, organized deployment automation for Vector Search Application**

---

## 📁 Directory Contents

| File | Platform | Purpose |
|------|----------|---------|
| **deploy-ToGit-from-windows.sh** | Windows | ✅ Deploy from Windows to GitHub |
| **deploy-RunAt-aws.sh** | AWS Linux | ✅ Complete AWS deployment orchestration |
| **setup-aws.sh** | AWS Linux | ✅ Infrastructure setup (Qdrant 1.15.2, Docker) |
| **setup-application-services-aws.sh** | AWS Linux | ✅ Application deployment from GitHub |
| **cleanup-aws.sh** | AWS Linux | ✅ Environment cleanup (optional) |
| **docker-compose.yml** | AWS Linux | ✅ Qdrant database configuration (v1.15.2) |
| **Dockerfile** | AWS Linux | ✅ Container configuration |

---

## ⚡ Quick Deploy

### Windows → GitHub
```bash
cd deploy
bash deploy-ToGit-from-windows.sh
```

### GitHub → AWS
```bash
git clone https://github.com/domini1969/vector-search-application.git
cd vector-search-application/deploy
./deploy-RunAt-aws.sh
```

---

## 🔧 Individual Components

```bash
# Manual step-by-step (if needed)
./cleanup-aws.sh              # Optional: Clean existing installation
./setup-aws.sh                # Install infrastructure  
./setup-application-services-aws.sh  # Deploy application
```

---

**📋 See [../DEPLOYMENT-GUIDE.md](../DEPLOYMENT-GUIDE.md) for complete instructions**