# SSL Setup for outfitpredict.ru

This directory contains everything needed to set up SSL certificates using system nginx and Let's Encrypt.

## Files

- **`setup-ssl-system-nginx.sh`** - Automated setup script for SSL certificates
- **`SSL-SETUP-SYSTEM-NGINX.md`** - Detailed documentation and manual setup instructions
- **`README.md`** - This file

## Quick Setup

For automated setup (recommended):

```bash
sudo ./setup-ssl-system-nginx.sh --email your-email@domain.com
```

For staging/testing first:

```bash
sudo ./setup-ssl-system-nginx.sh --email your-email@domain.com --staging
```

## What This Sets Up

-  SSL certificates from Let's Encrypt
-  HTTP to HTTPS redirects
-  Security headers (HSTS, XSS protection, etc.)
-  Rate limiting
-  Automatic certificate renewal
-  Modern SSL/TLS configuration

## Requirements

- System nginx already installed and running
- Domain pointing to your server
- Certbot installed
- Root/sudo access

For detailed instructions, see `SSL-SETUP-SYSTEM-NGINX.md`.
