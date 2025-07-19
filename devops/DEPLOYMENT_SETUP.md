# GitHub Runners Deployment Setup

This document explains how to set up the new GitHub runners-based CI/CD system that replaces the self-hosted runner setup.

## Overview

The new system uses:
- **GitHub-hosted runners** for CI and building Docker images
- **GitHub Container Registry (GHCR)** for storing Docker images
- **SSH deployment** to your production server
- **Pre-commit hooks** for local code quality checks

## Prerequisites

1. **Production Server Requirements:**
   - Ubuntu/Debian server with Docker and Docker Compose installed
   - SSH access for deployment user
   - Minimum 2GB RAM, 20GB disk space

2. **GitHub Repository Setup:**
   - Repository with packages permission enabled
   - Production environment configured in repository settings

## Required GitHub Secrets

Configure these secrets in your repository settings under `Settings > Secrets and variables > Actions`:

### Server Access Secrets
```bash
SSH_PRIVATE_KEY      # Private SSH key for deployment user
DEPLOY_HOST          # Server IP address or domain name
DEPLOY_USER          # SSH username for deployment (e.g., deploy, ubuntu)
```

### Database Configuration
```bash
DATABASE_URL         # PostgreSQL connection string
POSTGRES_USER        # Database username
POSTGRES_PASSWORD    # Database password
POSTGRES_DB          # Database name
```

### Redis Configuration
```bash
REDIS_URL           # Redis connection string (e.g., redis://localhost:6379)
```

### MinIO/S3 Configuration
```bash
MINIO_ACCESS_KEY    # MinIO/S3 access key
MINIO_SECRET_KEY    # MinIO/S3 secret key
MINIO_ENDPOINT      # MinIO/S3 endpoint URL
MINIO_BUCKET        # Storage bucket name
```

### Application Configuration
```bash
SECRET_KEY                    # FastAPI JWT secret key
ALGORITHM                     # JWT algorithm (default: HS256)
ACCESS_TOKEN_EXPIRE_MINUTES   # Token expiration time (default: 30)
NEXT_PUBLIC_API_URL          # Frontend API URL (e.g., https://api.yourdomain.com)
```

### Optional Notification Secrets
```bash
SLACK_WEBHOOK       # Slack webhook URL for deployment notifications
DISCORD_WEBHOOK     # Discord webhook URL for deployment notifications
```

## Server Setup

### 1. Create Deployment User
```bash
# On your production server
sudo adduser deploy
sudo usermod -aG docker deploy
sudo su - deploy
```

### 2. Setup SSH Access
```bash
# On your local machine, generate SSH key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/outfit_predict_deploy

# Copy public key to server
ssh-copy-id -i ~/.ssh/outfit_predict_deploy.pub deploy@your-server-ip

# Test connection
ssh -i ~/.ssh/outfit_predict_deploy deploy@your-server-ip
```

### 3. Add Private Key to GitHub Secrets
```bash
# Copy the private key content
cat ~/.ssh/outfit_predict_deploy

# Add this entire content to GitHub Secrets as SSH_PRIVATE_KEY
```

### 4. Prepare Server Directories
```bash
# On the production server as deploy user
mkdir -p ~/outfit-predict/{logs,backup,ssl-setup,monitoring}
```

## Local Development Setup

### 1. Install Pre-commit Hooks
```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install hooks in your repository
pre-commit install

# Run hooks on all files (first time)
pre-commit run --all-files
```

### 2. Install Development Dependencies
```bash
# Backend dependencies
cd backend
pip install -r requirements.txt

# Frontend dependencies
cd ../frontend
npm install

# Root development dependencies
cd ..
pip install -r requirements-dev.txt
```

## Workflow Configuration

### CI Workflow (`.github/workflows/ci.yml`)
- Runs on every push and pull request
- Performs code quality checks, security scanning, testing, and Docker builds
- Uses GitHub-hosted `ubuntu-latest` runners
- Creates test coverage reports and security scan results

### CD Workflow (`.github/workflows/cd-github-runners.yml`)
- Runs on pushes to `main` branch
- Builds and pushes Docker images to GitHub Container Registry
- Deploys to production server via SSH
- Includes health checks and automatic rollback on failure

## Migration from Self-Hosted Runner

### 1. Disable Old Workflow
```bash
# Rename or delete the old self-hosted workflow
mv .github/workflows/cd-self-hosted.yml .github/workflows/cd-self-hosted.yml.backup
```

### 2. Configure New Secrets
- Add all required secrets listed above to GitHub repository settings

### 3. Test Deployment
```bash
# Push a small change to main branch to trigger deployment
git commit --allow-empty -m "Test GitHub runners deployment"
git push origin main
```

### 4. Verify Services
After deployment, check that all services are running:
```bash
# SSH to your server
ssh deploy@your-server-ip

# Check running containers
cd ~/outfit-predict
docker compose ps

# Check service health
curl http://localhost:3000  # Frontend
curl http://localhost:8000  # Backend API
curl http://localhost:8000/docs  # API documentation
```

## Monitoring and Logs

The deployment includes container log monitoring:

- **Dozzle** (Port 9999): Real-time container logs

Access via nginx proxy (if configured):
- Logs: `https://yourdomain.com/logs/`

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Verify SSH key is correct and has proper permissions
   - Check firewall settings on server
   - Ensure deploy user exists and is in docker group

2. **Docker Login Failed**
   - Verify GITHUB_TOKEN has package read/write permissions
   - Check GitHub Container Registry is enabled for repository

3. **Health Check Failed**
   - Check container logs: `docker compose logs [service_name]`
   - Verify environment variables are set correctly
   - Check database connectivity

4. **Build Failed**
   - Review CI logs for specific error messages
   - Check Dockerfile syntax and dependencies
   - Verify base images are accessible

### Manual Deployment
If automated deployment fails, you can deploy manually:

```bash
# SSH to server
ssh deploy@your-server-ip
cd ~/outfit-predict

# Pull latest images
docker login ghcr.io -u your-github-username
docker compose pull

# Deploy
docker compose down
docker compose up -d
```

## Security Considerations

1. **SSH Keys**: Use dedicated SSH keys with minimal permissions
2. **Secrets Management**: Never commit secrets to repository
3. **Container Security**: Regularly update base images and scan for vulnerabilities
4. **Network Security**: Use firewall rules to limit exposed ports
5. **Access Control**: Limit GitHub repository access and use environment protection rules

## Backup and Recovery

The deployment automatically creates backups:
- Configuration backups before each deployment
- Docker image cleanup (keeps last 3 versions)
- Automatic rollback on deployment failure

Manual backup:
```bash
# On server
cd ~/outfit-predict
BACKUP_DIR="backup/manual_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp docker-compose.yml .env "$BACKUP_DIR/"
```

## Performance Optimization

1. **Docker Layer Caching**: The CI uses GitHub Actions cache for faster builds
2. **Image Registry**: Uses GHCR which is geographically distributed
3. **Multi-stage Builds**: Frontend and backend use optimized multi-stage Dockerfiles
4. **Resource Limits**: Configure appropriate CPU/memory limits in docker-compose.yml

---

For additional support, check the GitHub Actions logs or create an issue in the repository.
