## 📋 Prerequisites

-  Linux server with root access
-  Docker and Docker Compose installed
-  Git and Git LFS installed
-  GitHub repository access

##  Step-by-Step Setup

### Step 1: Prepare Your Environment

```bash
# Ensure you're in the project directory
cd /home/Outfit_predict

# Make scripts executable
chmod +x devops/setup-self-hosted-runner.sh
chmod +x devops/initial-deploy.sh

# Create environment file
cp devops/env.production.template .env
```

### Step 2: Configure Environment Variables

Edit your `.env` file with real values:

```bash
nano .env
```

**Essential configurations:**
```bash
# Database
POSTGRES_PASSWORD=your_secure_db_password_here
POSTGRES_USER=outfit_user
POSTGRES_DB=outfit

# MinIO (Object Storage)
MINIO_ACCESS_KEY=your_minio_access_key
MINIO_SECRET_KEY=your_secure_minio_secret

# Qdrant (Vector Database) - Get from https://qdrant.tech/
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_HOST=your_qdrant_host

# Application
NEXT_PUBLIC_API_URL=https://outfitpredict.ru/api
SECRET_KEY=your_32_char_secret_key  # Generate: openssl rand -hex 32
```

### Step 3: Install Self-Hosted Runner

```bash
# Run as root to install the runner
sudo ./devops/setup-self-hosted-runner.sh
```

This will:
-  Create `github-runner` user
-  Download GitHub Actions runner
-  Set up systemd service
-  Configure permissions

### Step 4: Get GitHub Runner Token

1. **Go to GitHub Settings:**
   ```
   https://github.com/IU-Capstone-Project-2025/Outfit_predict/settings/actions/runners
   ```

2. **Click "New self-hosted runner"**

3. **Copy the token** from the configuration command (looks like `AXXXXXXXXXXXXXXXXXXXXXXXXXXXX`)

### Step 5: Configure the Runner

```bash
# Use the token from Step 4
sudo -u github-runner /home/github-runner/configure-runner.sh \
  https://github.com/IU-Capstone-Project-2025/Outfit_predict YOUR_TOKEN_HERE
```

### Step 6: Start the Runner Service

```bash
# Start the runner
sudo systemctl start github-actions-runner

# Enable auto-start on boot
sudo systemctl enable github-actions-runner

# Check status
sudo systemctl status github-actions-runner
```

You should see: `Active: active (running)`

### Step 7: Verify Runner Connection

1. **Check GitHub:** Go back to the runners page - you should see your runner listed as "Online"

2. **Check logs:**
   ```bash
   sudo journalctl -u github-actions-runner -f
   ```

### Step 8: Test Deployment

```bash
# Make a small change and push
echo "# CD Setup Complete" >> README.md
git add README.md
git commit -m "test: trigger CD deployment"
git push origin main
```



### Step 9: Monitor Deployment

**Check GitHub Actions:**
- Go to your repository → Actions tab
- You should see a workflow running

**Check server logs:**
```bash
# Runner logs
sudo journalctl -u github-actions-runner -f

# Deployment logs (if using fallback)
tail -f /var/log/outfit-deploy.log

# Container status
docker-compose ps
```

## 🎉 Success Indicators

When everything works, you'll see:

1. **GitHub Runner Status:** Online
2. **Workflow Runs:** Successfully completing
3. **Services Running:** All containers healthy
4. **Application Access:**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - MinIO: http://localhost:9001

## 🔧 Useful Commands

### Runner Management
```bash
# Check runner status
sudo systemctl status github-actions-runner

# View runner logs
sudo journalctl -u github-actions-runner -f

# Restart runner
sudo systemctl restart github-actions-runner

# Stop runner
sudo systemctl stop github-actions-runner
```

### Application Management
```bash
# Check containers
docker-compose ps

# View application logs
docker-compose logs -f

# Restart specific service
docker-compose restart backend

# Full restart
docker-compose down && docker-compose up -d
```

### Emergency Procedures
```bash
# Manual deployment (if CD fails)
./devops/initial-deploy.sh

# Check disk space
df -h

# Check memory
free -h

# Check processes
htop
```

##  Troubleshooting

### Issue 1: Runner Not Starting

**Symptoms:** Service fails to start or goes offline

**Solution:**
```bash
# Check service status
sudo systemctl status github-actions-runner

# View detailed logs
sudo journalctl -u github-actions-runner -f

# Restart service
sudo systemctl restart github-actions-runner

# Check if runner user has docker access
sudo usermod -aG docker github-runner
sudo systemctl restart github-actions-runner
```

### Issue 2: Workflow Not Triggering

**Symptoms:** Push to main doesn't trigger deployment

**Check:**
1. Runner is online in GitHub settings
2. Workflow file exists: `.github/workflows/cd-self-hosted.yml`
3. Runner has correct labels: `self-hosted`, `linux`, `outfit-predict`

**Fix:**
```bash
# Check runner configuration
sudo -u github-runner cat /home/github-runner/actions-runner/.runner

# Reconfigure if needed (get new token first)
sudo -u github-runner /home/github-runner/configure-runner.sh \
  https://github.com/IU-Capstone-Project-2025/Outfit_predict NEW_TOKEN
```

### Issue 3: Deployment Fails

**Symptoms:** Workflow runs but fails during deployment

**Debug:**
```bash
# Check container status
docker-compose ps

# Check container logs
docker-compose logs backend
docker-compose logs frontend

# Check environment file
cat .env | grep -v PASSWORD | grep -v SECRET | grep -v KEY

# Manual deployment
./devops/initial-deploy.sh
```

### Issue 4: Permission Denied Errors

**Symptoms:** Docker or file permission errors

**Fix:**
```bash
# Add runner to docker group
sudo usermod -aG docker github-runner

# Fix file ownership
sudo chown -R github-runner:github-runner /home/github-runner/

# Restart runner
sudo systemctl restart github-actions-runner
```

##  Security Notes

-  Runner runs as dedicated `github-runner` user
-  Limited sudo permissions for Docker only
-  All secrets stored in `.env` file (not committed)
-  Automatic backups before each deployment
-  Health checks with automatic rollback

##  Support

If you encounter issues:

1. **Check logs:** `sudo journalctl -u github-actions-runner -f`
2. **Verify environment:** Ensure `.env` file is properly configured
3. **Test manual deployment:** `./devops/initial-deploy.sh`
4. **Check resources:** `df -h && free -h`

##  What Happens on Each Push

1. **Trigger:** Push to `main` branch
2. **Runner:** Picks up the job on your server
3. **Checkout:** Downloads latest code
4. **Backup:** Creates backup of current state
5. **Build:** Builds Docker images locally
6. **Deploy:** Starts new containers
7. **Health Check:** Verifies services are working
8. **Success:** Deployment complete! 🎉

**Total deployment time:** ~3-5 minutes

---


You now have a fully automated CD pipeline that:
-  Deploys on every push to main
-  Automatically rolls back on failure
-  Provides comprehensive monitoring
-  Maintains security best practices
-  Uses your server's full resources
