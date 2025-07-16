# Deployment Setup Guide

This guide walks you through setting up Continuous Deployment (CD) for the Outfit Predict application using GitHub Actions.

## 📋 Prerequisites

1. **Server Requirements:**
   - Linux server with Docker and Docker Compose installed
   - SSH access to the server
   - Git and Git LFS installed on the server
   - Nginx configured (use the existing `devops/setup-nginx.sh` script)

2. **GitHub Repository:**
   - Admin access to configure secrets
   - GitHub Container Registry enabled

## 🔐 Required GitHub Secrets

Navigate to your repository **Settings → Secrets and variables → Actions** and add these secrets:

### Server Connection Secrets

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `DEPLOY_HOST` | Your server's IP address or domain | `outfitpredict.ru` or `192.168.1.100` |
| `DEPLOY_USER` | SSH username for deployment | `ubuntu` or `deploy` |
| `DEPLOY_SSH_KEY` | Private SSH key for server access | `-----BEGIN OPENSSH PRIVATE KEY-----\n...` |

### Application Configuration

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `NEXT_PUBLIC_API_URL` | Frontend API URL | `https://outfitpredict.ru/api` or `http://localhost:8000` |

### Optional Notifications

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `SLACK_WEBHOOK` | Slack webhook URL for deployment notifications | No |

## 🔑 Setting Up SSH Key

### 1. Generate SSH Key Pair (if you don't have one)

```bash
# On your local machine
ssh-keygen -t ed25519 -f ~/.ssh/outfit_deploy_key -C "outfit-deploy"
```

### 2. Add Public Key to Server

```bash
# Copy public key to server
ssh-copy-id -i ~/.ssh/outfit_deploy_key.pub user@your-server.com

# Or manually add to ~/.ssh/authorized_keys on server
cat ~/.ssh/outfit_deploy_key.pub | ssh user@your-server.com "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 3. Add Private Key to GitHub Secrets

```bash
# Display private key (copy this to DEPLOY_SSH_KEY secret)
cat ~/.ssh/outfit_deploy_key
```

## 🚀 Server Setup

### 1. Clone Repository on Server

```bash
# SSH into your server
ssh user@your-server.com

# Clone the repository
git lfs clone https://github.com/IU-Capstone-Project-2025/Outfit_predict.git
cd Outfit_predict

# Set up environment
cp .env.example .env
# Edit .env with your production values
nano .env
```

### 2. Create Log Directory

```bash
# Create log directory for deployment script
sudo mkdir -p /var/log
sudo touch /var/log/outfit-deploy.log
sudo chown $USER:$USER /var/log/outfit-deploy.log
```

### 3. Make Deployment Script Executable

```bash
chmod +x devops/deploy.sh
```

### 4. Initial Manual Deployment

```bash
# Run initial deployment to verify everything works
./devops/deploy.sh deploy
```

## 📁 Environment Variables (.env)

Create a `.env` file on your server with the following variables:

```bash
# Database Configuration
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=outfit_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=outfit

# MinIO Configuration
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your_secure_minio_password

# Qdrant Configuration
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_HOST=your_qdrant_host

# Application Configuration
NEXT_PUBLIC_API_URL=https://outfitpredict.ru/api
```

## 🔄 How the CD Pipeline Works

1. **Trigger:** Push to `main` branch or manual workflow dispatch
2. **Build:** Builds Docker images for frontend and backend
3. **Push:** Pushes images to GitHub Container Registry
4. **Deploy:** SSH into server and run deployment script
5. **Health Check:** Verifies all services are running correctly
6. **Notify:** Sends deployment status to Slack (if configured)

## 📊 Monitoring Deployment

### View Deployment Logs

```bash
# SSH into server and check logs
tail -f /var/log/outfit-deploy.log
```

### Check Service Status

```bash
# Run health check
./devops/deploy.sh health

# Check running containers
docker-compose ps

# View container logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Manual Rollback

```bash
# If something goes wrong, rollback to previous version
./devops/deploy.sh rollback
```

## 🐛 Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Verify SSH key is correctly added to GitHub secrets
   - Check server firewall allows SSH connections
   - Ensure public key is in server's `~/.ssh/authorized_keys`

2. **Docker Images Not Found**
   - Check if GitHub Container Registry is enabled
   - Verify repository visibility settings
   - Ensure `GITHUB_TOKEN` has package write permissions

3. **Health Checks Failing**
   - Check if all required environment variables are set
   - Verify database and MinIO services are running
   - Check server resources (memory, disk space)

4. **Permission Denied**
   - Ensure deployment user has Docker permissions: `sudo usermod -aG docker $USER`
   - Verify log file permissions: `sudo chown $USER:$USER /var/log/outfit-deploy.log`

### Debug Commands

```bash
# Check Docker daemon status
sudo systemctl status docker

# Check available disk space
df -h

# Check memory usage
free -h

# View detailed container information
docker-compose ps
docker-compose logs
```

## 🔄 Manual Deployment

If you need to deploy manually without GitHub Actions:

```bash
# SSH into server
ssh user@your-server.com
cd Outfit_predict

# Pull latest changes
git pull origin main
git lfs pull

# Run deployment
./devops/deploy.sh deploy
```

## 📧 Support

If you encounter issues:

1. Check the deployment logs: `tail -f /var/log/outfit-deploy.log`
2. Review GitHub Actions workflow logs
3. Verify all secrets are correctly configured
4. Ensure server meets all prerequisites

For additional help, refer to the main project documentation or contact the development team.
