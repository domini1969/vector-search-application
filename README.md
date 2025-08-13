# 🚀 Vector Search Application

**AI-powered search with FastAPI, Streamlit, and Qdrant vector database**

---

## ⚡ Quick Deploy (2 Commands)

### Step 1: Windows → GitHub
```bash
# Run in Git Bash on Windows
cd deploy
bash ULTIMATE-DEPLOY.sh
```

### Step 2: GitHub → AWS
```bash
# Run on AWS Linux instance  
git clone https://github.com/domini1969/vector-search-application.git
cd vector-search-application/deploy
./ULTIMATE-AWS-DEPLOY.sh
```

---

## 🌐 Access Your App

After deployment, access at:
- **🔍 Search UI**: `http://your-aws-ip:8501`
- **📚 API Docs**: `http://your-aws-ip:8000/docs`  
- **🗄️ Database**: `http://your-aws-ip:6333/dashboard`

---

## 📖 Documentation

- **[📋 Complete Deployment Guide](DEPLOYMENT-GUIDE.md)** - Step-by-step instructions
- **[🔧 Troubleshooting](DEPLOYMENT-GUIDE.md#troubleshooting)** - Common issues and solutions

---

## 🎯 Features

- **Multi-Method Search**: Dense, sparse, and hybrid search modes
- **Interactive UI**: Beautiful Streamlit interface
- **REST API**: FastAPI with automatic documentation  
- **Vector Database**: Qdrant v1.15 with Docker deployment
- **Production Ready**: Systemd services, logging, monitoring
- **Auto-Scaling**: Optimized for different instance sizes

---

## 🛠️ Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Streamlit  │    │   FastAPI   │    │   Qdrant    │
│     UI      │───▶│     API     │───▶│  Database   │
│   :8501     │    │   :8000     │    │   :6333     │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## 🚨 Need Help?

### Quick Health Check
```bash
curl http://localhost:6333/health  # Database
curl http://localhost:8000/health  # API
curl http://localhost:8501         # UI
```

### Service Management  
```bash
sudo systemctl status qdrant vector-api vector-ui
sudo systemctl restart vector-api vector-ui
```

### Reset Everything
```bash
./ULTIMATE-AWS-DEPLOY.sh --clean
```

---

**🎊 Happy Searching!**