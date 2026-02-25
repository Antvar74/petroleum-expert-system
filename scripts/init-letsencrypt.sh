#!/bin/bash
# ============================================================
# PETROEXPERT — Let's Encrypt Certificate Provisioning
#
# Usage:
#   bash scripts/init-letsencrypt.sh your-domain.com [email@example.com]
#
# Prerequisites:
#   - Docker and docker compose running
#   - Port 80 accessible from the internet
#   - DNS A record pointing to this server's IP
#
# After running this script:
#   1. Uncomment the HTTPS server block in nginx/nginx.conf
#   2. Uncomment the HTTP→HTTPS redirect in nginx/nginx.conf
#   3. Remove the HTTP application serving block
#   4. Uncomment the certbot service in docker-compose.yml
#   5. Replace YOUR_DOMAIN.com with your actual domain
#   6. docker compose restart nginx
# ============================================================

set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain> [email]}"
EMAIL="${2:-}"
COMPOSE="docker compose"

echo "=== PETROEXPERT Let's Encrypt Setup ==="
echo "Domain: $DOMAIN"
echo ""

# 1. Start nginx if not running
echo "[1/4] Starting nginx..."
$COMPOSE up -d nginx

# 2. Request certificate via certbot
echo "[2/4] Requesting certificate for $DOMAIN..."

CERTBOT_ARGS="certonly --webroot -w /var/www/certbot -d $DOMAIN --agree-tos --non-interactive"
if [ -n "$EMAIL" ]; then
    CERTBOT_ARGS="$CERTBOT_ARGS --email $EMAIL"
else
    CERTBOT_ARGS="$CERTBOT_ARGS --register-unsafely-without-email"
fi

$COMPOSE run --rm certbot $CERTBOT_ARGS

# 3. Verify certificate
echo "[3/4] Verifying certificate..."
$COMPOSE exec nginx ls /etc/letsencrypt/live/$DOMAIN/fullchain.pem && \
    echo "Certificate installed successfully!" || \
    { echo "ERROR: Certificate not found"; exit 1; }

# 4. Instructions
echo ""
echo "[4/4] Certificate provisioned! Next steps:"
echo ""
echo "  1. Edit nginx/nginx.conf:"
echo "     - Replace YOUR_DOMAIN.com with: $DOMAIN"
echo "     - Uncomment the HTTPS server block"
echo "     - Uncomment the HTTP→HTTPS redirect"
echo "     - Remove the HTTP application serving block"
echo ""
echo "  2. Edit docker-compose.yml:"
echo "     - Uncomment the certbot service"
echo ""
echo "  3. Restart: docker compose restart nginx"
echo ""
echo "  4. Test: curl -I https://$DOMAIN"
echo ""
