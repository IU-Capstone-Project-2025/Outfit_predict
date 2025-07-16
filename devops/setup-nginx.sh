#!/usr/bin/env bash
set -e

DOMAIN="outfitpredict.ru"
if [ -n "$1" ]; then
  DOMAIN="$1"
fi

apt update
apt install -y nginx

CONF_PATH="/etc/nginx/sites-available/$DOMAIN"

tee "$CONF_PATH" > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Allow larger uploads (100MB for images and API responses)
    client_max_body_size 100M;

    # Increase proxy buffers for large responses
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    proxy_busy_buffers_size 8k;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade \$http_upgrade;
        proxy_set_header   Connection 'upgrade';
        proxy_set_header   Host \$host;
        proxy_cache_bypass \$http_upgrade;

        # Increase timeouts for large uploads
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Increase timeouts for API requests (especially ML processing)
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location = /api/docs {
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

ln -sf "$CONF_PATH" /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

echo "Nginx set up for $DOMAIN"
