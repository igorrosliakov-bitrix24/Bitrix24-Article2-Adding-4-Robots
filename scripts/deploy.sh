#!/bin/bash
# =============================================================================
# deploy.sh — Deploy Bitrix24 Robots app to VPS
# Usage: ./scripts/deploy.sh [--with-queue]
# =============================================================================
set -euo pipefail

# Load .env if present
if [ -f .env ]; then
  set -a; source .env; set +a
fi

DOMAIN="${VIRTUAL_HOST:-}"
WITH_QUEUE=0
PROFILE_FLAGS="--profile frontend --profile python --profile db-postgres"

# Parse args
for arg in "$@"; do
  case $arg in
    --with-queue) WITH_QUEUE=1 ;;
  esac
done

if [ "$WITH_QUEUE" = "1" ]; then
  PROFILE_FLAGS="--profile frontend --profile python --profile python-worker --profile queue --profile db-postgres"
fi

echo "=========================================="
echo "  Bitrix24 Robots — Production Deploy"
echo "=========================================="

# 1. Check required env vars
if [ -z "${VIRTUAL_HOST:-}" ]; then
  echo "ERROR: VIRTUAL_HOST is not set in .env"
  exit 1
fi
if [ -z "${CLIENT_ID:-}" ] || [ -z "${CLIENT_SECRET:-}" ]; then
  echo "ERROR: CLIENT_ID or CLIENT_SECRET is not set in .env"
  exit 1
fi

# 2. Pull latest code
echo ""
echo "[1/6] Pulling latest code..."
if ! git diff --quiet || ! git diff --cached --quiet; then
  git stash
  git pull origin "$(git branch --show-current)"
  git stash pop
else
  git pull origin "$(git branch --show-current)"
fi

# 3. Ensure nginx cert dirs exist
echo ""
echo "[2/6] Preparing Nginx directories..."
mkdir -p infrastructure/nginx/certs
mkdir -p infrastructure/nginx/certbot-webroot

# 4. Substitute domain in nginx.conf
DOMAIN=$(echo "$VIRTUAL_HOST" | sed 's|https://||' | sed 's|http://||')
echo "[3/6] Configuring Nginx for domain: $DOMAIN"
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" infrastructure/nginx/nginx.conf

# 5. Issue SSL certificate (first-time only — skip if cert already exists)
CERT_PATH="infrastructure/nginx/certs/live/$DOMAIN/fullchain.pem"
SELF_SIGNED_MARKER="infrastructure/nginx/certs/.self-signed"

if [ ! -f "$CERT_PATH" ] || [ -f "$SELF_SIGNED_MARKER" ]; then
  echo ""
  echo "[4/6] Issuing Let's Encrypt certificate..."
  echo "      (Nginx will start on port 80 for ACME challenge)"

  # Create a temporary self-signed cert so nginx can start (it needs a cert
  # file to load the SSL server block, even before the real cert is issued)
  if [ ! -f "$CERT_PATH" ]; then
    mkdir -p "infrastructure/nginx/certs/live/$DOMAIN"
    openssl req -x509 -nodes -newkey rsa:2048 \
      -keyout "infrastructure/nginx/certs/live/$DOMAIN/privkey.pem" \
      -out   "infrastructure/nginx/certs/live/$DOMAIN/fullchain.pem" \
      -days 1 -subj "/CN=$DOMAIN" 2>/dev/null
    touch "$SELF_SIGNED_MARKER"
    echo "  (temporary self-signed cert created for nginx startup)"
  fi

  # Remove any stale nginx container and start fresh so the new cert is visible
  docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    $PROFILE_FLAGS rm -sf nginx 2>/dev/null || true
  docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    $PROFILE_FLAGS up -d nginx

  # Wait until Nginx actually responds on port 80 (restart backoff can be slow)
  echo "  Waiting for Nginx to be ready..."
  NGINX_READY=0
  for i in $(seq 1 30); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://localhost/ 2>/dev/null)
    if [ -n "$HTTP_CODE" ] && [ "$HTTP_CODE" != "000" ]; then
      echo "  Nginx is up (HTTP $HTTP_CODE)."
      NGINX_READY=1
      break
    fi
    sleep 2
  done
  if [ "$NGINX_READY" = "0" ]; then
    echo "ERROR: Nginx failed to start within 60 s. Last logs:"
    docker logs nginx --tail 20 2>&1
    exit 1
  fi

  docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    $PROFILE_FLAGS run --rm --entrypoint certbot certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "admin@$DOMAIN" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

  rm -f "$SELF_SIGNED_MARKER"
  echo "Certificate issued successfully."

  # Reload nginx so it picks up the real cert
  docker exec nginx nginx -s reload || true
else
  echo "[4/6] SSL certificate already exists, skipping."
fi

# 6. Build and start all services
echo ""
echo "[5/6] Building production images..."
BUILD_TARGET=production docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  $PROFILE_FLAGS \
  build --no-cache

echo ""
echo "[6/6] Starting all services..."
BUILD_TARGET=production docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  $PROFILE_FLAGS \
  up -d

# 7. Run Django migrations and collectstatic
echo ""
echo "[+] Running migrations..."
docker exec api python manage.py migrate --noinput

echo "[+] Collecting static files..."
docker exec api python manage.py collectstatic --noinput

# 8. Create Django superuser (only on first deploy)
if [ ! -f ".superuser_created" ]; then
  echo "[+] Creating Django superuser..."
  docker exec api python manage.py createsuperuser --noinput || true
  touch .superuser_created
fi

echo ""
echo "=========================================="
echo "  Deploy complete!"
echo "  App:   https://$DOMAIN"
echo "  Admin: https://$DOMAIN/admin"
echo "  API:   https://$DOMAIN/api/public/health"
echo "=========================================="
