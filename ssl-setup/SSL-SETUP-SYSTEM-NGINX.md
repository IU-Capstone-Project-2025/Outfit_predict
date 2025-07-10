# SSL Setup for Existing System Nginx

Since you already have nginx running on your system at `/etc/nginx/`, this guide will help you add SSL certificates to your existing nginx configuration.

##  **Current Setup Detected**

 Nginx installed and running on system
 Configuration for `outfitpredict.ru` exists
 Certbot installed
 Docker services expose ports 3000 and 8000

## 🚀 **Quick Start**

### 1. **Run the SSL Setup Script**

```bash
# Test with staging certificates first (recommended)
sudo ./setup-ssl-system-nginx.sh --email your-email@example.com --staging

# If staging works, run for production certificates
sudo ./setup-ssl-system-nginx.sh --email your-email@example.com
```

### 2. **What the Script Does**

- ✅ **Backups** your existing nginx configuration
-  **Adds ACME challenge** support for Let's Encrypt
-  **Obtains SSL certificates** for outfitpredict.ru and www.outfitpredict.ru
-  **Updates nginx config** with SSL and security headers
-  **Sets up HTTP to HTTPS** redirects
-  **Configures automatic renewal** via cron job
-  **Tests the setup** to ensure everything works

##  **After SSL Setup**

Your site will be accessible at:
- **Frontend**: https://outfitpredict.ru
- **API**: https://outfitpredict.ru/api/v1/
- **Docs**: https://outfitpredict.ru/docs
- **Health**: https://outfitpredict.ru/health

## 🔧 **Manual Commands (if needed)**

### Check SSL Certificate Status
```bash
sudo certbot certificates
```

### Test Certificate Renewal
```bash
sudo certbot renew --dry-run
```

### Manual Certificate Renewal
```bash
sudo certbot renew
sudo systemctl reload nginx
```

### View Current Nginx Configuration
```bash
sudo cat /etc/nginx/sites-available/outfitpredict.ru
```

### Test Nginx Configuration
```bash
sudo nginx -t
```

### Reload Nginx
```bash
sudo systemctl reload nginx
```

##  **File Locations**

- **Nginx Config**: `/etc/nginx/sites-available/outfitpredict.ru`
- **SSL Certificates**: `/etc/letsencrypt/live/outfitpredict.ru/`
- **Backup Config**: `/etc/nginx/sites-available/outfitpredict.ru.backup`
- **ACME Webroot**: `/var/www/certbot`

##  **Automatic Renewal**

The script sets up a cron job that runs twice daily:
```
0 0,12 * * * /usr/bin/certbot renew --quiet && systemctl reload nginx
```

##  **Troubleshooting**

### If SSL Setup Fails
```bash
# Restore original configuration
sudo cp /etc/nginx/sites-available/outfitpredict.ru.backup /etc/nginx/sites-available/outfitpredict.ru
sudo systemctl reload nginx
```

### Check Nginx Logs
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Check Certbot Logs
```bash
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

### Verify DNS Resolution
```bash
dig +short A outfitpredict.ru
dig +short A www.outfitpredict.ru
```

##  **Benefits of This Approach**

-  **Uses your existing nginx** - no Docker container conflicts
-  **Preserves your current setup** - minimal changes to working config
-  **Automatic backups** - original config is saved
-  **Production-ready** - includes security headers and best practices
-  **Auto-renewal** - certificates renew automatically
-  **Easy rollback** - can restore original config if needed

##  **Security Features Added**

- **TLS 1.2/1.3** encryption protocols
- **HSTS** (HTTP Strict Transport Security) headers
- **Security headers** (X-Frame-Options, XSS-Protection, etc.)
- **Perfect Forward Secrecy** cipher suites
- **HTTP to HTTPS** automatic redirects

---

**Note**: The script requires root privileges (`sudo`) to modify nginx configuration and obtain SSL certificates.
