#!/bin/bash
# ============================================================
# DSTAIR — VPS First-Time Setup Script
# Tested on: Ubuntu 22.04 / Debian 11
#
# Run as root or with sudo:
#   chmod +x deploy/setup_vps.sh
#   sudo bash deploy/setup_vps.sh
#
# What this does:
#   1. Updates system packages
#   2. Installs Python 3.11, pip, nginx, certbot
#   3. Creates a dedicated system user (dstair)
#   4. Creates a Python virtualenv
#   5. Installs app dependencies
#   6. Creates log directory
#   7. Copies systemd service and nginx config
# ============================================================

set -e  # Exit immediately on any error

APP_DIR="/home/dstair/app"
DOMAIN="YOUR_DOMAIN"   # <-- CHANGE THIS

echo "==> [1/8] Updating system packages..."
apt-get update -qq && apt-get upgrade -y -qq

echo "==> [2/8] Installing Python 3.11, Nginx, Certbot..."
apt-get install -y -qq python3.11 python3.11-venv python3-pip nginx certbot python3-certbot-nginx

echo "==> [3/8] Creating system user 'dstair'..."
id -u dstair &>/dev/null || useradd --system --shell /bin/bash --create-home dstair

echo "==> [4/8] Creating app directory and copying files..."
mkdir -p $APP_DIR
# You should upload your app files to $APP_DIR before running this.
# Example: scp -r ./main-dstair/* root@YOUR_SERVER:$APP_DIR/
chown -R dstair:dstair $APP_DIR

echo "==> [5/8] Creating Python virtual environment..."
sudo -u dstair python3.11 -m venv $APP_DIR/venv

echo "==> [6/8] Installing Python dependencies..."
sudo -u dstair $APP_DIR/venv/bin/pip install --upgrade pip -q
sudo -u dstair $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt -q

echo "==> [7/8] Creating log directory..."
mkdir -p /var/log/dstair
chown -R dstair:www-data /var/log/dstair

echo "==> [8/8] Installing systemd service and nginx config..."
cp $APP_DIR/deploy/dstair.service /etc/systemd/system/dstair.service
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" $APP_DIR/deploy/nginx.conf
cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/dstair
ln -sf /etc/nginx/sites-available/dstair /etc/nginx/sites-enabled/dstair
rm -f /etc/nginx/sites-enabled/default   # remove default nginx page

systemctl daemon-reload
systemctl enable dstair
nginx -t && systemctl reload nginx

echo ""
echo "==> Setup complete!"
echo ""
echo "NEXT STEPS:"
echo "  1. Upload your .env file to $APP_DIR/.env"
echo "  2. sudo systemctl start dstair"
echo "  3. sudo certbot --nginx -d $DOMAIN   (free SSL)"
echo "  4. sudo systemctl status dstair"
