#!/bin/sh
# Birinchi marta HTTPS sertifikatini olish (Let's Encrypt). Bir marta,
# loyiha papkasida ishga tushiriladi:  sh deploy/init-letsencrypt.sh
#
# Talablar: .env da DOMAIN va LETSENCRYPT_EMAIL to'ldirilgan, domenning
# (va LETSENCRYPT_WWW=1 bo'lsa www.domen ning ham) DNS A-yozuvi shu server
# IP'siga qaratilgan, 80 va 443 portlar ochiq.
#
# nginx sertifikatsiz ishga tushmaydi, shuning uchun avval vaqtinchalik
# o'z-o'zidan imzolangan sertifikat qo'yiladi, nginx yoqiladi, keyin u
# haqiqiy sertifikat bilan almashtiriladi. Keyingi yangilanishlarni certbot
# konteyneri o'zi bajaradi.
set -eu

env_value() {
    grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | tr -d '\r'
}

DOMAIN="$(env_value DOMAIN)"
EMAIL="$(env_value LETSENCRYPT_EMAIL)"
WITH_WWW="$(env_value LETSENCRYPT_WWW)"
WITH_WWW="${WITH_WWW:-1}"

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo ".env da DOMAIN va LETSENCRYPT_EMAIL ni to'ldiring." >&2
    exit 1
fi

domain_args="-d $DOMAIN"
if [ "$WITH_WWW" = "1" ]; then
    domain_args="$domain_args -d www.$DOMAIN"
fi
live="/etc/letsencrypt/live/$DOMAIN"

echo "### Vaqtinchalik sertifikat yaratilmoqda ($DOMAIN)..."
docker compose run --rm --entrypoint sh certbot -c "\
    mkdir -p '$live' && \
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout '$live/privkey.pem' -out '$live/fullchain.pem' -subj '/CN=localhost'"

echo "### nginx ishga tushirilmoqda..."
docker compose up -d nginx

echo "### Vaqtinchalik sertifikat o'chirilmoqda..."
docker compose run --rm --entrypoint sh certbot -c "\
    rm -rf '/etc/letsencrypt/live/$DOMAIN' '/etc/letsencrypt/archive/$DOMAIN' \
           '/etc/letsencrypt/renewal/$DOMAIN.conf'"

echo "### Let's Encrypt sertifikati so'ralmoqda..."
# shellcheck disable=SC2086
docker compose run --rm --entrypoint certbot certbot certonly \
    --webroot -w /var/www/certbot $domain_args \
    --email "$EMAIL" --agree-tos --no-eff-email --rsa-key-size 4096

echo "### nginx qayta yuklanmoqda..."
docker compose exec nginx nginx -s reload

echo "Tayyor: https://$DOMAIN"
