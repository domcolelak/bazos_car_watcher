#!/bin/bash

# ============================================
# Bazoš Car Watcher - Inštalačný skript
# ============================================

set -e  # Zastav pri chybe

echo "============================================"
echo "🚗 Bazoš Car Watcher - Inštalácia"
echo "============================================"
echo

# Farby
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Kontrola root prístupu
if [ "$EUID" -ne 0 ]; then 
    print_error "Musíš spustiť tento skript ako root!"
    echo "Spusti: sudo bash install.sh"
    exit 1
fi

print_info "Inštalujem potrebné balíčky..."
apt update -qq
apt install -y python3 python3-pip python3-venv lxml-dev libxml2-dev libxslt1-dev > /dev/null 2>&1
print_success "Balíčky nainštalované"

# Vytvor priečinok
INSTALL_DIR="/opt/bazos-watcher"
print_info "Vytváram priečinok $INSTALL_DIR..."
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR
print_success "Priečinok vytvorený"

# Virtuálne prostredie
print_info "Vytváram virtuálne Python prostredie..."
python3 -m venv venv
source venv/bin/activate
print_success "Virtuálne prostredie vytvorené"

# Nainštaluj závislosti
print_info "Inštalujem Python knižnice..."
pip install --quiet --upgrade pip
pip install --quiet requests beautifulsoup4 lxml pyyaml flask
print_success "Knižnice nainštalované"

# Skontroluj či existujú súbory
if [ ! -f "bazos_car_watcher.py" ]; then
    print_error "Súbor bazos_car_watcher.py nebol nájdený!"
    echo "Skopíruj všetky súbory do $INSTALL_DIR"
    exit 1
fi

if [ ! -f "web_admin.py" ]; then
    print_error "Súbor web_admin.py nebol nájdený!"
    exit 1
fi

if [ ! -f "config.yaml" ]; then
    print_error "Súbor config.yaml nebol nájdený!"
    exit 1
fi

print_success "Všetky súbory nájdené"

# Nastav práva
chmod +x bazos_car_watcher.py
chmod +x web_admin.py

# Vytvor systemd službu pre hlavný skript
print_info "Vytváram systemd službu bazos-watcher..."
cat > /etc/systemd/system/bazos-watcher.service << EOF
[Unit]
Description=Bazos Car Watcher
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/bazos_car_watcher.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
print_success "Služba bazos-watcher vytvorená"

# Vytvor systemd službu pre web admin
print_info "Vytváram systemd službu web-admin..."
cat > /etc/systemd/system/bazos-web-admin.service << EOF
[Unit]
Description=Bazos Car Watcher Web Admin
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/web_admin.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
print_success "Služba web-admin vytvorená"

# Reload systemd
print_info "Reloadujem systemd..."
systemctl daemon-reload
print_success "Systemd reloadnutý"

# Spusti služby
print_info "Spúšťam služby..."
systemctl start bazos-watcher
systemctl start bazos-web-admin
sleep 2
print_success "Služby spustené"

# Zapni autoštart
print_info "Zapínam autoštart..."
systemctl enable bazos-watcher > /dev/null 2>&1
systemctl enable bazos-web-admin > /dev/null 2>&1
print_success "Autoštart zapnutý"

# Získaj IP adresu
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "SERVER_IP")

echo
echo "============================================"
echo -e "${GREEN}✓ Inštalácia dokončená!${NC}"
echo "============================================"
echo
echo "📋 Informácie:"
echo "   Inštalačný priečinok: $INSTALL_DIR"
echo "   Config súbor: $INSTALL_DIR/config.yaml"
echo "   Dáta: $INSTALL_DIR/bazos_data/"
echo
echo "🌐 Web rozhranie:"
echo "   URL: http://$SERVER_IP:5000"
echo "   Heslo: bazos2025"
echo "   (Zmeň heslo v súbore web_admin.py)"
echo
echo "🔧 Užitočné príkazy:"
echo "   Stav služby:      systemctl status bazos-watcher"
echo "   Logy:             journalctl -u bazos-watcher -f"
echo "   Reštart:          systemctl restart bazos-watcher"
echo "   Zastaviť:         systemctl stop bazos-watcher"
echo "   Web admin logy:   journalctl -u bazos-web-admin -f"
echo
echo "📝 Ďalšie kroky:"
echo "   1. Otvor: http://$SERVER_IP:5000"
echo "   2. Prihlás sa heslom: bazos2025"
echo "   3. Nastav Telegram Bot Token a Chat ID"
echo "   4. Uprav filtre podľa potreby"
echo "   5. Klikni 'Uložiť nastavenia'"
echo
echo "============================================"
