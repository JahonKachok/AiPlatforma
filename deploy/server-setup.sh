#!/bin/sh
# Yangi Ubuntu 22.04/24.04 VPS'ni tayyorlash va himoyalash. Bir marta,
# root sifatida ishga tushiriladi:  sudo sh deploy/server-setup.sh
#
# Nima qiladi:
#   * tizimni yangilaydi va xavfsizlik yangilanishlarini avtomatik o'rnatadi;
#   * Docker o'rnatadi;
#   * 2 GB swap qo'shadi (2 GB RAM'li serverda build va backup paytida
#     xotira yetmay qolmasin);
#   * firewall (ufw): faqat SSH, 80 va 443 portlar ochiq;
#   * fail2ban: SSH parolini tanlashga urinayotgan IP'larni bloklaydi;
#   * SSH kalit allaqachon qo'shilgan bo'lsa — parol bilan kirishni o'chiradi.
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "root sifatida ishga tushiring: sudo sh deploy/server-setup.sh" >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "### Tizim yangilanmoqda..."
apt-get update
apt-get -y upgrade
apt-get install -y ufw fail2ban unattended-upgrades ca-certificates curl

echo "### Avtomatik xavfsizlik yangilanishlari yoqilmoqda..."
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

if ! command -v docker >/dev/null 2>&1; then
    echo "### Docker o'rnatilmoqda..."
    curl -fsSL https://get.docker.com | sh
fi

if ! swapon --show | grep -q .; then
    echo "### 2 GB swap qo'shilmoqda..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "### Firewall sozlanmoqda (SSH, 80, 443)..."
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "### fail2ban yoqilmoqda..."
cat > /etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban

# SSH parol bilan kirishni faqat kalit bilan kirish imkoni bo'lsagina
# o'chiramiz — aks holda serverdan butunlay qulflanib qolish mumkin.
has_key=0
for keys in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do
    if [ -s "$keys" ]; then
        has_key=1
    fi
done

if [ "$has_key" = "1" ]; then
    echo "### SSH: parol bilan kirish o'chirilmoqda (faqat kalit)..."
    cat > /etc/ssh/sshd_config.d/99-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
EOF
    systemctl reload ssh 2>/dev/null || systemctl reload sshd
    echo "Joriy SSH oynasini yopmasdan, yangi oynada kalit bilan kira olishingizni tekshiring."
else
    echo "DIQQAT: SSH kaliti topilmadi — parol bilan kirish YOQIQ qoldi."
    echo "Kalit qo'shing (ssh-copy-id) va skriptni qayta ishga tushiring."
fi

echo "Server tayyor."
