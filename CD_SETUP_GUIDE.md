# CD (Continuous Deployment) Setup Guide

## Overview

Your project has a **GitHub-hosted CD pipeline** that automatically deploys your application when you push to the `main` branch. Here's how to set it up and make it work.

## 🚀 How the CD Workflow Works

### Current Workflow: GitHub Runners + SSH Deployment

**File**: `.github/workflows/cd-github-runners.yml`

**Process**:
1. **Trigger**: Pushes to `main` branch or manual dispatch
2. **Build**: Creates Docker images for backend/frontend
3. **Push**: Images pushed to GitHub Container Registry (GHCR)
4. **Deploy**: SSH into your server and deploy new images
5. **Health Check**: Verify all services are running
6. **Rollback**: Automatic rollback if deployment fails

### Backup Workflow: Self-Hosted (Currently Disabled)

**File**: `.github/workflows/cd-self-hosted.yml.backup`
- Runs directly on your server
- No SSH needed, but requires GitHub runner installed on server
- Currently disabled due to permission issues

## 🔧 Required Setup Steps

### 1. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these **Repository Secrets**:

#### SSH Configuration
```
SSH_PRIVATE_KEY     # Private key for SSH access to your server
SSH_PUBLIC_KEY      # Public key (optional, for reference)
DEPLOY_HOST         # Your server IP: 178.215.238.69
DEPLOY_USER         # SSH user: deploy
```

#### Database Configuration
```
DATABASE_URL        # postgresql+asyncpg://outfit_user:password@localhost:5432/outfit_predict
POSTGRES_USER       # outfit_user (or your database user)
POSTGRES_PASSWORD   # your_database_password
POSTGRES_DB         # outfit_predict
```

#### Redis Configuration
```
REDIS_URL           # redis://localhost:6379
```

#### MinIO Configuration
```
MINIO_ACCESS_KEY    # your_minio_access_key
MINIO_SECRET_KEY    # your_minio_secret_key
MINIO_ENDPOINT      # localhost:9000
MINIO_BUCKET        # outfit-images
```

#### Application Secrets
```
SECRET_KEY          # your_fastapi_secret_key (generate with: openssl rand -hex 32)
ALGORITHM           # HS256
ACCESS_TOKEN_EXPIRE_MINUTES  # 30
```

#### Frontend Configuration
```
NEXT_PUBLIC_API_URL # https://outfitpredict.ru/api
```

### 2. Generate SSH Key for Deployment

On your **local machine** or **server**:

```bash
# Generate SSH key pair for deployment
ssh-keygen -t ed25519 -C "github-deployment" -f ~/.ssh/github_deploy

# Display private key (copy to GitHub secret SSH_PRIVATE_KEY)
cat ~/.ssh/github_deploy

# Display public key
cat ~/.ssh/github_deploy.pub
```

**On your server** (`178.215.238.69`):
```bash
# Add the public key to authorized_keys
echo "your_public_key_here" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 3. Test SSH Connection

From your local machine:
```bash
ssh -i ~/.ssh/github_deploy deploy@178.215.238.69
```

Should connect without password.

### 4. Update Docker Compose for Production

The CD workflow expects your `docker-compose.yml` to use **image references** rather than **build contexts** for production deployment.

Current `docker-compose.yml` should have sections like:
```yaml
services:
  backend:
    image: ghcr.io/yourusername/outfit_predict-backend:latest  # Will be updated by CD
    # build: ./backend  # Remove this for production

  frontend:
    image: ghcr.io/yourusername/outfit_predict-frontend:latest  # Will be updated by CD
    # build: ./frontend  # Remove this for production
```

## 🎯 How to Use the CD Pipeline

### Automatic Deployment
```bash
# Make your changes
git add .
git commit -m "Your changes"
git push origin main

# ✅ CD pipeline will automatically:
# 1. Build new Docker images
# 2. Push to GitHub Container Registry
# 3. SSH to your server
# 4. Pull new images
# 5. Restart services
# 6. Run health checks
```

### Manual Deployment
1. Go to GitHub Actions in your repository
2. Select "CD - GitHub Runners Deployment"
3. Click "Run workflow" → "Run workflow"

### Monitor Deployment
1. Go to GitHub Actions → Latest workflow run
2. Watch real-time logs for each step
3. Check deployment summary at the end

## 📊 Deployment Features

### ✅ What the CD Pipeline Includes

1. **Zero-Downtime Deployment**
   - Builds new images while old ones run
   - Switches traffic only after successful health checks

2. **Automatic Rollback**
   - If health checks fail, automatically restores previous version
   - Creates backups before each deployment

3. **Health Monitoring**
   - Checks frontend (port 3000)
   - Checks backend API (port 8000/health)
   - Verifies API documentation (port 8000/docs)

4. **Container Registry**
   - Images stored in GitHub Container Registry (GHCR)
   - Automatic cleanup of old images
   - Version tagging with git commit SHA

5. **Security**
   - Encrypted secrets management
   - SSH key-based authentication
   - Container vulnerability scanning

6. **Monitoring Integration**
   - Preserves container log monitoring (Dozzle)
   - Maintains nginx proxy configuration

### 📁 Deployment Structure

On your server after CD setup:
```
/home/deploy/outfit-predict/
├── docker-compose.yml          # Updated with new image tags
├── .env                        # Generated from GitHub secrets
├── devops/                     # Deployment scripts
├── monitoring/                 # Monitoring configurations
├── ssl-setup/                  # SSL certificates setup
├── backup/                     # Automatic backups
│   ├── 20250716_190000/        # Backup before deployment
│   └── latest_backup.txt       # Points to latest backup
└── logs/                       # Application logs
```

## 🔍 Troubleshooting

### Check Current Deployment Status
```bash
ssh deploy@178.215.238.69
cd ~/outfit-predict
docker compose ps
docker compose logs -f
```

### Common Issues

1. **SSH Permission Denied**
   ```bash
   # Fix: Check SSH key is added to server
   ssh-copy-id -i ~/.ssh/github_deploy.pub deploy@178.215.238.69
   ```

2. **Docker Login Failed**
   ```bash
   # Fix: GitHub token needs package write permissions
   # Check GitHub repo → Settings → Actions → General → Workflow permissions
   ```

3. **Health Check Failed**
   ```bash
   # Check logs for specific service
   docker compose logs backend
   docker compose logs frontend
   ```

4. **Environment Variables Missing**
   ```bash
   # Fix: Verify all required secrets are set in GitHub
   # Settings → Secrets and variables → Actions
   ```

### Manual Recovery
If deployment fails and rollback doesn't work:
```bash
ssh deploy@178.215.238.69
cd ~/outfit-predict

# Restore from backup
BACKUP_DIR=$(cat backup/latest_backup.txt)
cp $BACKUP_DIR/docker-compose.yml .
cp $BACKUP_DIR/.env .

# Restart services
docker compose down
docker compose up -d
```

## 🎉 Benefits of This Setup

1. **Professional Deployment**: Industry-standard CI/CD pipeline
2. **Zero Manual Work**: Push to main → automatic deployment
3. **Safe Deployments**: Automatic rollback on failure
4. **Version Control**: All deployments tracked and versioned
5. **Security**: Encrypted secrets, no manual credential handling
6. **Monitoring**: Full integration with your monitoring stack
7. **Scalability**: Easy to add staging environments, multiple servers

## 🚀 Next Steps

1. **Configure all GitHub secrets** (most important!)
2. **Test the workflow** with a small change
3. **Monitor first deployment** in GitHub Actions
4. **Set up notifications** (optional) for deployment status

Once configured, you'll have a **professional-grade deployment pipeline** that automatically deploys your application with zero downtime and full monitoring! 🎉
