#!/bin/sh
# Devbot'ni serverga o'rnatadi yoki yangilaydi (root sifatida):
#   sudo sh deploy/devbot/setup-devbot.sh
#
# Nima qiladi:
#   * python venv + python-telegram-bot o'rnatadi;
#   * devbot.py va Dockerfile.runner ni /opt/aiplatforma-devbot ga nusxalaydi
#     (Claude repodagi devbot fayllarini o'zgartirsa ham, ishlab turgan bot
#     o'zgarmaydi — yangilash uchun shu skriptni qayta ishga tushiring);
#   * /etc/aiplatforma-devbot.env ni yaratadi (bo'lmasa);
#   * systemd xizmatini (aiplatforma-devbot) yoqadi.
#
# Bot tokeni, username va Claude kaliti shu yerda EMAS — platformadagi
# Profil → Integratsiyalar → Devbot bo'limida kiritiladi.
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "root sifatida ishga tushiring: sudo sh deploy/devbot/setup-devbot.sh" >&2
    exit 1
fi

SRC_DIR=$(cd "$(dirname "$0")" && pwd)
PROD_DIR=$(cd "$SRC_DIR/../.." && pwd)
DEVBOT_USER=${DEVBOT_USER:-$(stat -c %U "$PROD_DIR")}
DEVBOT_HOME=$(getent passwd "$DEVBOT_USER" | cut -d: -f6)
INSTALL_DIR=/opt/aiplatforma-devbot
ENV_FILE=/etc/aiplatforma-devbot.env

echo "### Platforma: $PROD_DIR, devbot foydalanuvchisi: $DEVBOT_USER"

if [ "$DEVBOT_USER" != "root" ] && ! id -nG "$DEVBOT_USER" | grep -qw docker; then
    echo "### $DEVBOT_USER docker guruhiga qo'shilmoqda..."
    usermod -aG docker "$DEVBOT_USER"
fi

apt-get install -y python3-venv git >/dev/null

echo "### $INSTALL_DIR tayyorlanmoqda..."
mkdir -p "$INSTALL_DIR"
[ -x "$INSTALL_DIR/venv/bin/python" ] || python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -q "python-telegram-bot==21.9"
install -m 644 "$SRC_DIR/devbot.py" "$INSTALL_DIR/devbot.py"
install -m 644 "$SRC_DIR/Dockerfile.runner" "$INSTALL_DIR/Dockerfile.runner"
chown -R "$DEVBOT_USER" "$INSTALL_DIR"

if [ ! -f "$ENV_FILE" ]; then
    sed "s#^DEVBOT_PROD_DIR=.*#DEVBOT_PROD_DIR=$PROD_DIR#" "$SRC_DIR/devbot.env.example" > "$ENV_FILE"
    echo "### $ENV_FILE yaratildi."
fi
chown "$DEVBOT_USER" "$ENV_FILE"
chmod 600 "$ENV_FILE"

cat > /etc/systemd/system/aiplatforma-devbot.service <<EOF
[Unit]
Description=AiPlatforma devbot (Telegram orqali kodni o'zgartirish)
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=$DEVBOT_USER
EnvironmentFile=$ENV_FILE
Environment=HOME=$DEVBOT_HOME
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/devbot.py
# Panelda token o'zgarsa bot o'zi chiqadi (kod 3) va shu yerda qayta yoqiladi.
Restart=always
RestartSec=5
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable aiplatforma-devbot >/dev/null
systemctl restart aiplatforma-devbot

echo
echo "Devbot ishga tushdi:  journalctl -u aiplatforma-devbot -f"
echo "Endi platformada: Profil → Integratsiyalar → Devbot — token, username va Claude kalitini kiriting."
echo "Buyruq berish uchun adminning Telegram'i platformadagi profilga ulangan bo'lishi kerak."
