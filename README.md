# 🚗 Bazoš Car Watcher - Kompletný návod

Automatický sledovač inzerátov áut na Bazoš.sk s webovým rozhraním pre jednoduchú správu.

## 📦 Čo obsahuje balík:

- `bazos_car_watcher.py` - Hlavný skript (sleduje Bazoš)
- `web_admin.py` - Webové rozhranie pre správu
- `config.yaml` - Konfiguračný súbor
- `install.sh` - Automatická inštalácia
- `README.md` - Tento návod

---

## 🚀 Inštalácia na VPS server

### Krok 1: Pripoj sa na server
```bash
ssh root@IP_ADRESA_SERVERA
```

### Krok 2: Nahraj súbory
```bash
# Vytvor priečinok
mkdir -p /opt/bazos-watcher
cd /opt/bazos-watcher

# Nahraj súbory (cez SCP z tvojho počítača):
# scp *.py *.yaml *.sh root@IP_ADRESA:/opt/bazos-watcher/
```

### Krok 3: Spusti inštaláciu
```bash
cd /opt/bazos-watcher
chmod +x install.sh
bash install.sh
```

Inštalácia automaticky:
- ✅ Nainštaluje Python a potrebné knižnice
- ✅ Vytvorí systemd služby
- ✅ Zapne autoštart
- ✅ Spustí sledovanie

---

## 🌐 Prístup do webového rozhrania

Po inštalácii otvor v prehliadači:
```
http://IP_ADRESA_SERVERA:5000
```

### Predvolené heslo:
```
bazos2025
```

**DÔLEŽITÉ:** Zmeň heslo po prvom prihlásení!

### Ako zmeniť heslo:
```bash
nano /opt/bazos-watcher/web_admin.py

# Nájdi riadok:
ADMIN_PASSWORD = "bazos2025"

# Zmeň na:
ADMIN_PASSWORD = "tvoje_nove_heslo"

# Ulož (Ctrl+O, Enter, Ctrl+X) a reštartuj:
systemctl restart bazos-web-admin
```

---

## ⚙️ Nastavenie Telegram bota

### 1. Vytvor bota
1. Otvor Telegram a nájdi **@BotFather**
2. Napíš: `/newbot`
3. Zadaj meno: napr. `Bazos Watcher`
4. Zadaj username: napr. `bazos_watcher_bot` (musí končiť na `_bot`)
5. Dostaneš **TOKEN** - ulož si ho!

### 2. Zisti svoje Chat ID
1. Napíš svojmu novému botovi `/start`
2. Otvor v prehliadači:
   ```
   https://api.telegram.org/bot<TOJ_TOKEN>/getUpdates
   ```
   (nahraď `<TOJ_TOKEN>` za tvoj token)
3. Nájdeš tam `"chat":{"id":123456789}` - to je tvoje Chat ID

### 3. Zadaj do webového rozhrania
1. Otvor web rozhranie
2. Sekcia "📱 Telegram"
3. Zadaj Bot Token a Chat ID
4. Klikni "📤 Test" - mali by ti prísť správa na Telegram
5. Klikni "💾 Uložiť nastavenia"

---

## 🎯 Ako nastaviť filtre

### Základné filtre:
- **Minimálny ročník**: Napr. 2015 (nebude hľadať staršie autá)
- **Maximálne km**: Napr. 190000 (nebude hľadať autá s vyšším stavom)
- **Minimálny score**: 2-4 body (koľko kritérií musí auto splniť)
  - Score 2 = veľa notifikácií
  - Score 3 = odporúčané (vyvážené)
  - Score 4 = len perfektné matche

### Značky a palivá:
- Zaklikni značky ktoré ťa zaujímajú
- Pre každú značku vyber povolené palivá (Benzín/Diesel)
- Napr. Toyota len benzín, VW benzín aj diesel

### Časovanie:
- Ako často kontrolovať Bazoš (30 min - 24 hodín)
- Odporúčam: 1 hodina

---

## 📊 Ako to funguje?

### Score systém (body):
Každý inzerát dostane 0-4 body:

1. **+1 bod** = Rok ≥ tvoj minimálny rok
2. **+1 bod** = Kilometre ≤ tvoj maximálny počet km
3. **+1 bod** = Značka je v tvojom zozname
4. **+1 bod** = Palivo sedí pre danú značku

**Príklad:**
- VW Golf, rok 2018, 120 000 km, diesel
- ✓ Rok OK (2018 ≥ 2015) = +1 bod
- ✓ Km OK (120000 ≤ 190000) = +1 bod
- ✓ Značka OK (VW je v zozname) = +1 bod
- ✓ Palivo OK (diesel je povolený pre VW) = +1 bod
- **= 4/4 body → Dostaneš notifikáciu!**

---

## 📱 Telegram notifikácie

Keď nájde match, dostaneš správu:
```
🚗 Match (score 4/4)
━━━━━━━━━━━━━━━━━━━━
📌 VW Golf 1.6 TDI

💰 Cena: 8,900 €
📅 Rok: 2018 | 🛣️ Km: 120,000
🏷️ Značka: volkswagen | ⛽ Palivo: dies
📍 Lokalita: Prievidza

✅ Dôvody: ročník≥2015 (2018), km≤190,000 (120,000), značka (volkswagen), palivo OK (dies)

🔗 https://auto.bazos.sk/inzerat/...
```

---

## 🔧 Užitočné príkazy

### Sledovanie logov v reálnom čase:
```bash
journalctl -u bazos-watcher -f
```
(Vypneš cez Ctrl+C)

### Kontrola stavu:
```bash
systemctl status bazos-watcher
```

### Reštart:
```bash
systemctl restart bazos-watcher
```

### Zastavenie:
```bash
systemctl stop bazos-watcher
```

### Spustenie:
```bash
systemctl start bazos-watcher
```

### Web admin logy:
```bash
journalctl -u bazos-web-admin -f
```

---

## 📥 Stiahnutie CSV s matchmi

### Cez web rozhranie:
Klikni na tlačidlo **"📥 Stiahnuť CSV"**

### Cez terminál:
```bash
# Zobraz obsah:
cat /opt/bazos-watcher/bazos_data/matches.csv

# Stiahni na svoj počítač:
scp root@IP_ADRESA:/opt/bazos-watcher/bazos_data/matches.csv ~/Desktop/
```

---

## 🔄 Aktualizácia nastavení

### Cez web rozhranie (ODPORÚČANÉ):
1. Otvor http://IP_ADRESA:5000
2. Uprav nastavenia
3. Klikni "💾 Uložiť nastavenia"
4. Klikni "🔄 Reštartovať" (voliteľné - automaticky sa načíta pri ďalšej kontrole)

### Manuálne (cez SSH):
```bash
nano /opt/bazos-watcher/config.yaml
# Uprav hodnoty
# Ulož: Ctrl+O, Enter, Ctrl+X
systemctl restart bazos-watcher
```

---

## ❓ Riešenie problémov

### Služba nebeží?
```bash
systemctl status bazos-watcher
journalctl -u bazos-watcher -n 50  # Posledných 50 riadkov logov
```

### Web rozhranie nie je dostupné?
```bash
systemctl status bazos-web-admin
journalctl -u bazos-web-admin -n 50

# Skontroluj firewall:
ufw allow 5000/tcp
```

### Telegram notifikácie nefungujú?
1. Skontroluj Token a Chat ID
2. Klikni "📤 Test" v web rozhraní
3. Skontroluj že si napísal botovi `/start`

### Nenachádza žiadne inzeráty?
1. Skontroluj že URL v nastaveniach je správna
2. Skús otvoriť URL v prehliadači - funguje?
3. Skontroluj logy: `journalctl -u bazos-watcher -f`

---

## 🔒 Zabezpečenie

### Zmeň heslo do web rozhrania!
```bash
nano /opt/bazos-watcher/web_admin.py
# Zmeň ADMIN_PASSWORD
systemctl restart bazos-web-admin
```

### Nastav firewall:
```bash
# Povol len SSH a web rozhranie
ufw allow 22/tcp
ufw allow 5000/tcp
ufw enable
```

### Voliteľne: Nastav HTTPS
Odporúčam použiť Nginx reverse proxy s Let's Encrypt certifikátom.

---

## 📞 Kontakt a podpora

Ak máš problém:
1. Skontroluj logy: `journalctl -u bazos-watcher -f`
2. Skontroluj nastavenia v web rozhraní
3. Kontaktuj vývojára/dodávateľa

---

## 🎁 Bonusové tipy

### Pridanie viacerých URL:
V web rozhraní môžeš pridať viac Bazoš URL (napr. rôzne mestá):
- Klikni "➕ Pridať URL"
- Zadaj ďalšiu URL
- Uloži

### Kontrola len konkrétnych modelov:
Ak chceš napr. len VW Golf a Škodu Octavia:
1. Názov inzerátu musí obsahovať model (väčšinou áno)
2. Skript to automaticky vyfiltruje podľa značky

### Zníženie počtu notifikácií:
- Zvýš "Minimálny score" na 4
- Zníž "Max. km"
- Zvýš "Min. rok"

---

**Verzia:** 1.2  
**Posledná aktualizácia:** 2025-01-15
