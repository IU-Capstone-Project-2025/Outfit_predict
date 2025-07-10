#!/usr/bin/env bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="outfitpredict.ru"
EMAIL="admin@outfitpredict.ru"  # Change this to your email
STAGING=false
NGINX_SITE="/etc/nginx/sites-available/outfitpredict.ru"
WEBROOT="/var/www/certbot"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_status "Checking prerequisites..."

    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi

    # Check if nginx is installed and running
    if ! systemctl is-active --quiet nginx; then
        print_error "Nginx is not running. Please start nginx first."
        exit 1
    fi

    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        print_error "Certbot is not installed. Installing..."
        apt update && apt install -y certbot python3-certbot-nginx
    fi

    # Check if site config exists
    if [[ ! -f "$NGINX_SITE" ]]; then
        print_error "Nginx site configuration not found at $NGINX_SITE"
        exit 1
    fi

    print_success "Prerequisites check passed!"
}

check_domain_dns() {
    print_status "Checking DNS configuration for $DOMAIN..."

    # Get server's public IP
    SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || echo "unknown")
    print_status "Server IP: $SERVER_IP"

    # Check A record
    DOMAIN_IP=$(dig +short A $DOMAIN | tail -n1)
    print_status "Domain $DOMAIN resolves to: $DOMAIN_IP"

    if [ "$SERVER_IP" != "$DOMAIN_IP" ]; then
        print_warning "Domain does not point to this server."
        print_warning "Add an A record: $DOMAIN -> $SERVER_IP"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "DNS configuration looks correct!"
    fi
}

setup_webroot() {
    print_status "Setting up webroot for ACME challenges..."

    # Create webroot directory
    mkdir -p "$WEBROOT"

    # Add ACME challenge location to existing nginx config
    if ! grep -q "\.well-known/acme-challenge" "$NGINX_SITE"; then
        print_status "Adding ACME challenge location to nginx config..."

        # Create temporary file with updated config
        cat > "/tmp/nginx_temp.conf" << EOF
server {
    listen 80;
    server_name $DOMAIN;

    # ACME challenge location for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root $WEBROOT;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade \$http_upgrade;
        proxy_set_header   Connection 'upgrade';
        proxy_set_header   Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location = /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location = /openapi.json {
        proxy_pass http://localhost:8000/openapi.json;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

        # Backup original and replace
        cp "$NGINX_SITE" "${NGINX_SITE}.backup"
        mv "/tmp/nginx_temp.conf" "$NGINX_SITE"

        # Test nginx configuration
        if nginx -t; then
            systemctl reload nginx
            print_success "Nginx configuration updated and reloaded"
        else
            print_error "Nginx configuration test failed"
            mv "${NGINX_SITE}.backup" "$NGINX_SITE"
            exit 1
        fi
    else
        print_status "ACME challenge location already configured"
    fi
}

obtain_certificates() {
    print_status "Obtaining SSL certificates for $DOMAIN..."

    # Determine if we should use staging
    STAGING_FLAG=""
    if [ "$STAGING" = true ]; then
        STAGING_FLAG="--staging"
        print_warning "Using Let's Encrypt staging environment for testing"
    fi

    # Request certificate using webroot
    certbot certonly \
        --webroot \
        --webroot-path="$WEBROOT" \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        $STAGING_FLAG \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"

    if [ $? -eq 0 ]; then
        print_success "SSL certificates obtained successfully!"
    else
        print_error "Failed to obtain SSL certificates"
        exit 1
    fi
}

setup_ssl_nginx() {
    print_status "Updating nginx configuration for SSL..."

    # Create SSL-enabled nginx configuration
    cat > "$NGINX_SITE" << EOF
# HTTP server - redirects to HTTPS and handles ACME challenges
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    # ACME challenge location for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root $WEBROOT;
    }

    # Redirect all other HTTP traffic to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    # Frontend application
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # API routes
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Increase timeout for API requests
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # API documentation
    location = /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # OpenAPI specification
    location = /openapi.json {
        proxy_pass http://localhost:8000/openapi.json;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Health check endpoint
    location = /health {
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
}
EOF

    # Test nginx configuration
    if nginx -t; then
        systemctl reload nginx
        print_success "Nginx SSL configuration applied and reloaded!"
    else
        print_error "Nginx SSL configuration test failed"
        mv "${NGINX_SITE}.backup" "$NGINX_SITE"
        systemctl reload nginx
        exit 1
    fi
}

test_ssl() {
    print_status "Testing SSL configuration..."

    sleep 5  # Give nginx time to reload

    # Test HTTPS connection
    if curl -s -I "https://$DOMAIN/health" | grep -q "200 OK"; then
        print_success "HTTPS is working correctly!"
    else
        print_warning "HTTPS test failed, but certificates may still be working"
    fi

    # Test HTTP to HTTPS redirect
    if curl -s -I "http://$DOMAIN/health" | grep -q "301\|302"; then
        print_success "HTTP to HTTPS redirect is working!"
    else
        print_warning "HTTP to HTTPS redirect test failed"
    fi
}

setup_auto_renewal() {
    print_status "Setting up automatic certificate renewal..."

    # Check if renewal cron job already exists
    if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
        # Add renewal cron job
        (crontab -l 2>/dev/null; echo "0 0,12 * * * /usr/bin/certbot renew --quiet && systemctl reload nginx") | crontab -
        print_success "Automatic renewal cron job added!"
    else
        print_status "Automatic renewal cron job already exists"
    fi

    # Test renewal
    print_status "Testing certificate renewal (dry run)..."
    if certbot renew --dry-run; then
        print_success "Certificate renewal test passed!"
    else
        print_warning "Certificate renewal test failed, but certificates should still work"
    fi
}

print_final_instructions() {
    print_success "SSL setup completed successfully!"
    echo
    print_status "Your site is now available at:"
    echo "  - https://$DOMAIN"
    echo "  - https://www.$DOMAIN"
    echo
    print_status "What was done:"
    echo "  ✅ SSL certificates obtained from Let's Encrypt"
    echo "  ✅ Nginx configured with HTTPS and security headers"
    echo "  ✅ HTTP to HTTPS redirects enabled"
    echo "  ✅ Automatic renewal cron job set up"
    echo
    print_status "Certificate info:"
    echo "  📂 Certificate location: /etc/letsencrypt/live/$DOMAIN/"
    echo "  📅 Renewal: Automatic (twice daily)"
    echo "  🔄 Manual renewal: sudo certbot renew"
    echo
    print_status "Backup files:"
    echo "  📄 Original nginx config: ${NGINX_SITE}.backup"
}

main() {
    echo
    print_status "SSL Setup for $DOMAIN (System Nginx)"
    print_status "====================================="
    echo

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --staging)
                STAGING=true
                shift
                ;;
            --email)
                EMAIL="$2"
                shift 2
                ;;
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --staging          Use Let's Encrypt staging environment"
                echo "  --email EMAIL      Email for Let's Encrypt registration"
                echo "  --domain DOMAIN    Domain name (default: outfitpredict.ru)"
                echo "  --help             Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    print_status "Domain: $DOMAIN"
    print_status "Email: $EMAIL"
    print_status "Staging: $STAGING"
    print_status "Nginx config: $NGINX_SITE"
    echo

    # Main setup process
    check_prerequisites
    check_domain_dns
    setup_webroot
    obtain_certificates
    setup_ssl_nginx
    test_ssl
    setup_auto_renewal
    print_final_instructions
}

# Handle interrupts gracefully
trap 'print_error "Setup interrupted"; exit 1' INT TERM

# Run main function
main "$@"
