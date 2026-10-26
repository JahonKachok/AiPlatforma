#!/bin/sh
# Postgres bazasining kunlik nusxasi (db-backup konteynerida ishlaydi).
#
# Saytdagi "Backups" sahifasi faqat media fayllarni va eng oxirgi shu
# nusxani zip qiladi; bazaning o'zini esa shu skript oladi. Nusxalar
# db_backups volume'ida, BACKUP_KEEP_DAYS kundan eskilari o'chiriladi.
#
# Tiklash (restore):
#   docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < db_YYYYmmdd_HHMMSS.dump
set -eu

KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"

until pg_isready -q; do
    sleep 5
done

while :; do
    file="/backups/db_$(date +%Y%m%d_%H%M%S).dump"
    # Avval vaqtinchalik nomga: yarim yozilgan fayl "eng oxirgi nusxa" bo'lib
    # qolmasin.
    if pg_dump --format=custom --file="$file.part"; then
        mv "$file.part" "$file"
        echo "backup tayyor: $file"
    else
        rm -f "$file.part"
        echo "XATO: pg_dump muvaffaqiyatsiz" >&2
    fi
    find /backups -name 'db_*.dump' -mtime "+$KEEP_DAYS" -delete
    sleep "$INTERVAL"
done
