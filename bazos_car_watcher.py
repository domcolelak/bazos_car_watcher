import csv
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup

# =========================
# PATHS
# =========================
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.yaml"
DATA_DIR = BASE_DIR / "bazos_data"
SEEN_FILE = DATA_DIR / "seen.json"
MATCHES_CSV = DATA_DIR / "matches.csv"

USER_AGENT = "Mozilla/5.0 (compatible; BazosCarWatcher/1.2; +local-script)"


# =========================
# CONFIG LOADER
# =========================
class Config:
    """Načíta a spravuje konfiguráciu z config.yaml"""
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.reload()
    
    def reload(self):
        """Načíta konfiguráciu zo súboru."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Telegram
            self.telegram_bot_token = data.get('telegram', {}).get('bot_token', '')
            self.telegram_chat_id = data.get('telegram', {}).get('chat_id', '')
            
            # Timing
            self.check_every_hours = data.get('timing', {}).get('check_every_hours', 1)
            
            # Filters
            filters = data.get('filters', {})
            self.min_year = filters.get('min_year', 2015)
            self.max_km = filters.get('max_km', 190000)
            self.min_price = filters.get('min_price', 1500)  # NOVÉ - minimálna cena
            self.min_score = filters.get('min_score', 3)
            self.pages_per_list = filters.get('pages_per_list', 3)
            
            # Brands
            self.brands = data.get('brands', {})
            
            # URLs
            self.bazos_urls = data.get('bazos_urls', [])
            
            print(f"✓ Config načítaný: {len(self.brands)} značiek, {len(self.bazos_urls)} URL")
            
        except Exception as e:
            print(f"CHYBA pri načítaní config.yaml: {e}")
            print("Používam predvolené nastavenia...")
            self._set_defaults()
    
    def _set_defaults(self):
        """Nastaví predvolené hodnoty ak config zlyhá."""
        self.telegram_bot_token = ""
        self.telegram_chat_id = ""
        self.check_every_hours = 1
        self.min_year = 2015
        self.max_km = 190000
        self.min_price = 1500  # NOVÉ
        self.min_score = 3
        self.pages_per_list = 3
        self.brands = {
            "volkswagen": ["benz", "dies"],
            "škoda": ["benz", "dies"],
            "skoda": ["benz", "dies"],
        }
        self.bazos_urls = ["https://auto.bazos.sk/inzeraty/prievidza-1/97101/"]


# =========================
# DÁTOVÉ TRIEDY
# =========================
@dataclass
class Ad:
    title: str
    url: str


@dataclass
class Extracted:
    year: Optional[int]
    km: Optional[int]
    brand: Optional[str]
    fuel: Optional[str]
    price: Optional[str]
    location: Optional[str]


# =========================
# STORAGE
# =========================
def ensure_storage():
    """Vytvorí potrebné priečinky a súbory, ak neexistujú."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if not SEEN_FILE.exists():
        SEEN_FILE.write_text(
            json.dumps({"seen": []}, ensure_ascii=False, indent=2), 
            encoding="utf-8"
        )

    if not MATCHES_CSV.exists():
        with MATCHES_CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "timestamp", "title", "price", "location", "year", 
                "km", "brand", "fuel", "url", "score", "reasons"
            ])


def load_seen() -> Set[str]:
    """Načíta zoznam už videných inzerátov."""
    try:
        data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        return set(data.get("seen", []))
    except Exception as e:
        print(f"Chyba pri načítaní seen.json: {e}")
        return set()


def save_seen(seen: Set[str]):
    """Uloží zoznam videných inzerátov."""
    try:
        SEEN_FILE.write_text(
            json.dumps({"seen": sorted(list(seen))}, ensure_ascii=False, indent=2), 
            encoding="utf-8"
        )
    except Exception as e:
        print(f"Chyba pri ukladaní seen.json: {e}")


# =========================
# TELEGRAM
# =========================
def telegram_send(config: Config, text: str):
    """Pošle správu cez Telegram bot."""
    if not config.telegram_bot_token or not config.telegram_chat_id:
        return
    
    try:
        url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
        response = requests.post(
            url, 
            data={"chat_id": config.telegram_chat_id, "text": text}, 
            timeout=10
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Chyba pri odosielaní Telegram správy: {e}")


# =========================
# HTTP / PARSE HELPERS
# =========================
def http_get(url: str) -> str:
    """Stiahne HTML obsah z danej URL."""
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=25)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"HTTP chyba pri {url}: {e}")
        raise


def norm(s: str) -> str:
    """Normalizuje text - lowercase a jedno medzera."""
    return re.sub(r"\s+", " ", s.strip().lower())


def extract_price(text: str) -> Optional[str]:
    """Vytiahne cenu vo formáte 'XXXXX €' z textu."""
    t = text.replace("\xa0", " ")
    m = re.search(r"(\d[\d\s]{2,})\s*€", t)
    if m:
        val = re.sub(r"\s+", " ", m.group(1)).strip()
        return f"{val} €"
    return None


def extract_price_value(price_str: Optional[str]) -> Optional[int]:
    """NOVÉ - Konvertuje cenu '8 900 €' na číslo 8900."""
    if not price_str:
        return None
    try:
        num_str = re.sub(r'[^\d]', '', price_str)
        return int(num_str) if num_str else None
    except:
        return None


def extract_location_from_text(text: str) -> Optional[str]:
    """Skúsi nájsť lokalitu (mesto) v texte."""
    cities = [
        "prievidza", "bojnice", "handlová", "handlova", 
        "nováky", "novaky", "partizánske", "partizanske"
    ]
    
    text_lower = text.lower()
    for city in cities:
        if city in text_lower:
            return city.capitalize()
    
    return None


def extract_year(text: str) -> Optional[int]:
    """Vytiahne rok výroby vozidla z textu."""
    t = norm(text)
    
    # Najprv hľadaj kontextové roky
    ctx = re.search(
        r"(rok\s*výroby|rok\s*vyroby|ročník|rocnik|r\.v\.|rv\.?|r\.v\b)\D{0,25}?(19\d{2}|20\d{2})", 
        t
    )
    if ctx:
        try:
            year = int(ctx.group(2))
            current_year = datetime.now().year
            if 1980 <= year <= current_year:
                return year
        except (ValueError, IndexError):
            pass
    
    # Ak nie, hľadaj všetky roky a vyber najvyšší
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", t)
    if not years:
        return None
    
    current_year = datetime.now().year
    candidates = [int(y) for y in years if 1980 <= int(y) <= current_year]
    
    if not candidates:
        return None
    
    return max(candidates)


def extract_km(text: str) -> Optional[int]:
    """Vytiahne počet kilometrov z textu."""
    t = norm(text)

    # Formát: 123 456 km alebo 123.456 km alebo 123456 km
    m = re.search(r"\b(\d{1,3}(?:[ .]\d{3})+|\d{5,6})\s*km\b", t)
    if m:
        raw = m.group(1).replace(" ", "").replace(".", "")
        try:
            return int(raw)
        except ValueError:
            pass

    # Formát: 123 tis km alebo 123 t km
    m2 = re.search(r"\b(\d{2,3})\s*(tis|t)\s*km\b", t)
    if m2:
        try:
            return int(m2.group(1)) * 1000
        except ValueError:
            pass

    # Formát: 123tkm
    m3 = re.search(r"\b(\d{2,3})\s*tkm\b", t)
    if m3:
        try:
            return int(m3.group(1)) * 1000
        except ValueError:
            pass

    return None


def extract_brand(text: str, title: str, brands: Dict[str, List[str]]) -> Optional[str]:
    """Vytiahne značku auta z textu a titulku."""
    combined = norm(text + " " + title)
    
    # Hľadaj najdlhšie zhody najprv
    for brand in sorted(brands.keys(), key=len, reverse=True):
        if brand in combined:
            return brand
    
    return None


def extract_fuel(text: str) -> Optional[str]:
    """Vytiahne typ paliva z textu."""
    t = norm(text)

    # Benzín
    if any(x in t for x in ["benzín", "benzin", "benz"]):
        return "benz"
    
    # Diesel
    if any(x in t for x in ["diesel", "nafta", "tdi", "dci", "cdti", "dies"]):
        return "dies"
    
    return None


# =========================
# LIST SCRAPE + PAGINATION
# =========================
def list_page_urls(start_url: str, max_pages: int) -> List[str]:
    """Zoberie start_url a vytiahne URL strán 1..max_pages z navigácie."""
    urls = [start_url]
    if max_pages <= 1:
        return urls

    try:
        html = http_get(start_url)
        soup = BeautifulSoup(html, "lxml")
    except Exception as e:
        print(f"Chyba pri načítaní pagination z {start_url}: {e}")
        return urls

    page_links = []
    for a in soup.select("a[href]"):
        txt = a.get_text(" ", strip=True).lower()
        href = a.get("href", "").strip()
        if not href:
            continue
        
        if txt.isdigit() or "ďalš" in txt or "dalš" in txt:
            page_links.append(urljoin(start_url, href))

    seen = {start_url}
    result = [start_url]
    
    for u in page_links:
        if u not in seen and len(result) < max_pages:
            seen.add(u)
            result.append(u)

    return result


def fetch_ads_from_list(list_url: str, max_pages: int) -> List[Ad]:
    """Načíta všetky inzeráty zo zadaného listu."""
    ads: Dict[str, Ad] = {}

    for page_url in list_page_urls(list_url, max_pages):
        try:
            html = http_get(page_url)
            soup = BeautifulSoup(html, "lxml")
        except Exception as e:
            print(f"Chyba pri načítaní stránky {page_url}: {e}")
            continue

        for a in soup.select("a[href*='inzerat/']"):
            href = a.get("href", "").strip()
            title = a.get_text(" ", strip=True)
            if not href or not title:
                continue

            full = urljoin(page_url, href)
            
            if full not in ads:
                ads[full] = Ad(title=title, url=full)

        time.sleep(1)

    return list(ads.values())


# =========================
# DETAIL EXTRACT
# =========================
def fetch_and_extract(ad: Ad, config: Config) -> Extracted:
    """Načíta detail inzerátu a vytiahne všetky relevantné informácie."""
    html = http_get(ad.url)
    soup = BeautifulSoup(html, "lxml")
    page_text = soup.get_text("\n", strip=True)

    year = extract_year(page_text)
    km = extract_km(page_text)
    brand = extract_brand(page_text, ad.title, config.brands)
    fuel = extract_fuel(page_text)
    price = extract_price(page_text)
    location = extract_location_from_text(page_text)

    return Extracted(
        year=year, 
        km=km, 
        brand=brand, 
        fuel=fuel, 
        price=price, 
        location=location
    )


# =========================
# FILTER LOGIKA (score)
# =========================
def score_match(ex: Extracted, config: Config) -> Tuple[int, List[str]]:
    """Ohodnotí inzerát bodmi podľa splnených kritérií."""
    score = 0
    reasons = []

    # Kritérium 1: Ročník
    if ex.year is not None and ex.year >= config.min_year:
        score += 1
        reasons.append(f"ročník≥{config.min_year} ({ex.year})")

    # Kritérium 2: Kilometre
    if ex.km is not None and ex.km <= config.max_km:
        score += 1
        reasons.append(f"km≤{config.max_km:,} ({ex.km:,})")

    # Kritérium 3: Značka
    if ex.brand is not None:
        score += 1
        reasons.append(f"značka ({ex.brand})")

        # Kritérium 4: Palivo
        allowed = config.brands.get(ex.brand, [])
        if ex.fuel is not None and ex.fuel in allowed:
            score += 1
            reasons.append(f"palivo OK ({ex.fuel})")

    return score, reasons


def append_match(ad: Ad, ex: Extracted, score: int, reasons: List[str]):
    """Pridá match do CSV súboru."""
    ts = datetime.now().isoformat(timespec="seconds")
    
    try:
        with MATCHES_CSV.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                ts, 
                ad.title, 
                ex.price or "", 
                ex.location or "", 
                ex.year or "", 
                ex.km or "",
                ex.brand or "", 
                ex.fuel or "", 
                ad.url, 
                score, 
                " | ".join(reasons)
            ])
    except Exception as e:
        print(f"Chyba pri zapisovaní do CSV: {e}")


# =========================
# MAIN LOOP
# =========================
def main():
    """Hlavný loop - beží kontinuálne a kontroluje nové inzeráty."""
    print("=" * 60)
    print("🚗 Bazoš Car Watcher v1.2")
    print("=" * 60)
    
    # Načítaj config
    config = Config(CONFIG_FILE)
    
    print(f"⏱️  Kontrola každých {config.check_every_hours}h")
    print(f"🎯 Min. rok: {config.min_year}, Max. km: {config.max_km:,}")
    print(f"💰 Min. cena: {config.min_price:,} €")  # NOVÉ
    print(f"📊 Min. score: {config.min_score}/4")
    print(f"📱 Telegram: {'✓' if config.telegram_bot_token and config.telegram_chat_id else '✗ (nie je nastavený)'}")
    print(f"🔗 Sledovaných URL: {len(config.bazos_urls)}")
    print("=" * 60)
    
    ensure_storage()
    seen = load_seen()

    iteration = 0
    while True:
        iteration += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Iterácia #{iteration}")
        
        # Reload config každú iteráciu (ak sa zmenil cez web GUI)
        config.reload()
        
        new_matches = 0
        new_ads = 0

        for list_url in config.bazos_urls:
            print(f"  Kontrolujem: {list_url}")
            
            try:
                ads = fetch_ads_from_list(list_url, config.pages_per_list)
                print(f"  Nájdených inzerátov: {len(ads)}")
            except Exception as e:
                error_msg = f"Bazoš: chyba pri načítaní listu\n{list_url}\n{e}"
                print(f"  CHYBA: {e}")
                telegram_send(config, error_msg)
                continue

            for ad in ads:
                if ad.url in seen:
                    continue
                
                seen.add(ad.url)
                new_ads += 1

                time.sleep(1)

                try:
                    ex = fetch_and_extract(ad, config)
                except Exception as e:
                    print(f"  Chyba pri spracovaní {ad.url}: {e}")
                    continue

                # NOVÉ - Check min_price
                price_value = extract_price_value(ex.price)
                if price_value and price_value < config.min_price:
                    continue  # Skip - príliš lacné (pravdepodobne diel)

                score, reasons = score_match(ex, config)
                
                if score >= config.min_score:
                    new_matches += 1
                    append_match(ad, ex, score, reasons)

                    print(f"  ✓ MATCH (score {score}): {ad.title[:50]}...")

                    msg = (
                        f"🚗 Match (score {score}/4)\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 {ad.title}\n\n"
                        f"💰 Cena: {ex.price or 'nezistená'}\n"
                        f"📅 Rok: {ex.year or '?'} | 🛣️ Km: {ex.km or '?'}\n"
                        f"🏷️ Značka: {ex.brand or '?'} | ⛽ Palivo: {ex.fuel or '?'}\n"
                        f"📍 Lokalita: {ex.location or 'nezistená'}\n\n"
                        f"✅ Dôvody: {', '.join(reasons)}\n\n"
                        f"🔗 {ad.url}"
                    )
                    telegram_send(config, msg)

        save_seen(seen)
        print(f"  Nové inzeráty: {new_ads}, Nové matches: {new_matches}")
        print(f"  Spolu videných: {len(seen)}")
        
        sleep_seconds = int(config.check_every_hours * 3600)
        print(f"  Ďalšia kontrola o {config.check_every_hours}h...")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Skript ukončený používateľom (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ FATÁLNA CHYBA: {e}")
        raise