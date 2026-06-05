#!/usr/bin/env python3
"""
Web Admin rozhranie pre Bazoš Car Watcher
Umožňuje upravovať nastavenia cez webový prehliadač
"""

import csv
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import yaml
from flask import Flask, render_template_string, request, jsonify, send_file, redirect, session

# =========================
# CONFIG
# =========================
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.yaml"
DATA_DIR = BASE_DIR / "bazos_data"
MATCHES_CSV = DATA_DIR / "matches.csv"
SEEN_FILE = DATA_DIR / "seen.json"

# Web admin heslo
ADMIN_PASSWORD = "bazos2025"

app = Flask(__name__)
app.secret_key = "bazos-secret-key-change-this"

# =========================
# HELPER FUNCTIONS
# =========================
def load_config():
    """Načíta config.yaml"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Chyba pri načítaní config: {e}")
        return {}

def save_config(config):
    """Uloží config.yaml"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"Chyba pri ukladaní config: {e}")
        return False

def get_service_status():
    """Zistí či beží systemd služba"""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'bazos-watcher'],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() == 'active'
    except:
        return False

def restart_service():
    """Reštartuje systemd službu"""
    try:
        subprocess.run(['systemctl', 'restart', 'bazos-watcher'], check=True)
        return True
    except:
        return False

def stop_service():
    """Zastaví systemd službu"""
    try:
        subprocess.run(['systemctl', 'stop', 'bazos-watcher'], check=True)
        return True
    except:
        return False

def get_recent_matches(limit=10):
    """Načíta posledné matches z CSV"""
    if not MATCHES_CSV.exists():
        return []
    
    try:
        with open(MATCHES_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            matches = list(reader)
            return matches[-limit:][::-1]  # Posledných N, v opačnom poradí
    except:
        return []

# =========================
# HTML TEMPLATE
# =========================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bazoš Car Watcher - Admin</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        
        .status {
            display: inline-block;
            padding: 8px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            font-size: 14px;
            margin-top: 10px;
        }
        
        .status.running { background: #10b981; }
        .status.stopped { background: #ef4444; }
        
        .content { padding: 30px; }
        
        .section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f9fafb;
            border-radius: 12px;
            border-left: 4px solid #667eea;
        }
        
        .section h2 {
            font-size: 18px;
            margin-bottom: 15px;
            color: #1f2937;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #374151;
        }
        
        .form-group input, .form-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
        }
        
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .form-group small {
            display: block;
            margin-top: 5px;
            color: #6b7280;
            font-size: 12px;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .brand-item {
            padding: 12px;
            background: white;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .brand-name {
            font-weight: 500;
            min-width: 120px;
        }
        
        .fuel-checks {
            display: flex;
            gap: 15px;
        }
        
        .fuel-checks label {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
        }
        
        .button-primary {
            background: #667eea;
            color: white;
        }
        
        .button-primary:hover {
            background: #5568d3;
        }
        
        .button-success {
            background: #10b981;
            color: white;
        }
        
        .button-danger {
            background: #ef4444;
            color: white;
        }
        
        .button-secondary {
            background: #6b7280;
            color: white;
        }
        
        .buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 20px;
        }
        
        .match-item {
            padding: 15px;
            background: white;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        
        .match-title {
            font-weight: 500;
            margin-bottom: 8px;
        }
        
        .match-details {
            display: flex;
            gap: 15px;
            font-size: 13px;
            color: #6b7280;
            flex-wrap: wrap;
        }
        
        .match-score {
            background: #667eea;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
        }
        
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .alert-success {
            background: #d1fae5;
            color: #065f46;
        }
        
        .alert-error {
            background: #fee2e2;
            color: #991b1b;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚗 Bazoš Car Watcher</h1>
            <div class="status {{ 'running' if is_running else 'stopped' }}">
                {{ '🟢 Beží' if is_running else '🔴 Zastavené' }}
            </div>
        </div>
        
        <div class="content">
            {% if message %}
            <div class="alert alert-{{ message_type }}">
                {{ message }}
            </div>
            {% endif %}
            
            <form method="POST" action="/save">
                <!-- Lokalita -->
                <div class="section">
                    <h2>📍 Lokalita</h2>
                    <div class="form-row">
                        <div class="form-group">
                            <label>PSČ (Poštové smerovacie číslo):</label>
                            <input type="text" name="hlokalita" value="{{ config.location.hlokalita }}" placeholder="97101" required>
                            <small>Napr. 97101 pre Prievidzu</small>
                        </div>
                        <div class="form-group">
                            <label>Okolie (km):</label>
                            <input type="number" name="humkreis" value="{{ config.location.humkreis }}" min="1" max="50" required>
                            <small>Vzdialenosť okolo PSČ</small>
                        </div>
                    </div>
                </div>
                
                <!-- Filtre -->
                <div class="section">
                    <h2>🎯 Filtre</h2>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Minimálny rok:</label>
                            <input type="number" name="min_year" value="{{ config.filters.min_year }}" min="1990" max="2030">
                        </div>
                        <div class="form-group">
                            <label>Maximum kilometrov:</label>
                            <input type="number" name="max_km" value="{{ config.filters.max_km }}" min="0" step="10000">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Minimálna cena (€):</label>
                            <input type="number" name="min_price" value="{{ config.filters.min_price }}" min="0" step="100">
                            <small>Vylúči diely (odporúčané 1500+)</small>
                        </div>
                        <div class="form-group">
                            <label>Minimálny score (z 4):</label>
                            <select name="min_score">
                                <option value="2" {{ 'selected' if config.filters.min_score == 2 }}>2 - veľa notifikácií</option>
                                <option value="3" {{ 'selected' if config.filters.min_score == 3 }}>3 - odporúčané</option>
                                <option value="4" {{ 'selected' if config.filters.min_score == 4 }}>4 - len perfektné</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Strán na kontrolu (1-10):</label>
                        <input type="number" name="pages_per_list" value="{{ config.filters.pages_per_list }}" min="1" max="10">
                        <small>Každá strana = 20 inzerátov</small>
                    </div>
                </div>
                
                <!-- Značky -->
                <div class="section">
                    <h2>🏷️ Značky a palivá</h2>
                    <div id="brands-container">
                        {% for brand, fuels in config.brands.items() %}
                        <div class="brand-item">
                            <input type="checkbox" name="brand_enabled_{{ brand }}" checked>
                            <span class="brand-name">{{ brand }}</span>
                            <div class="fuel-checks">
                                <label>
                                    <input type="checkbox" name="brand_{{ brand }}_benz" {{ 'checked' if 'benz' in fuels }}>
                                    Benzín
                                </label>
                                <label>
                                    <input type="checkbox" name="brand_{{ brand }}_dies" {{ 'checked' if 'dies' in fuels }}>
                                    Diesel
                                </label>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                
                <!-- Telegram -->
                <div class="section">
                    <h2>📱 Telegram</h2>
                    <div class="form-group">
                        <label>Bot Token:</label>
                        <input type="text" name="bot_token" value="{{ config.telegram.bot_token }}" placeholder="1234567890:ABCdef...">
                    </div>
                    <div class="form-group">
                        <label>Chat ID:</label>
                        <input type="text" name="chat_id" value="{{ config.telegram.chat_id }}" placeholder="123456789">
                    </div>
                </div>
                
                <!-- Buttons -->
                <div class="buttons">
                    <button type="submit" class="button button-primary">💾 Uložiť nastavenia</button>
                    <button type="button" class="button button-success" onclick="window.location.href='/restart'">🔄 Reštartovať</button>
                    <button type="button" class="button button-secondary" onclick="window.location.href='/download'">📥 Stiahnuť CSV</button>
                    <button type="button" class="button button-danger" onclick="window.location.href='/stop'">⏹️ Zastaviť</button>
                    <a href="/logout" class="button button-secondary">🚪 Odhlásiť</a>
                </div>
            </form>
            
            <!-- Recent Matches -->
            {% if recent_matches %}
            <div class="section">
                <h2>📋 Posledných {{ recent_matches|length }} matchov</h2>
                {% for match in recent_matches %}
                <div class="match-item">
                    <div class="match-title">{{ match.title }}</div>
                    <div class="match-details">
                        <span class="match-score">Score: {{ match.score }}/4</span>
                        <span>💰 {{ match.price }}</span>
                        <span>📅 {{ match.year }}</span>
                        <span>🛣️ {{ match.km }} km</span>
                        <span>⏰ {{ match.timestamp }}</span>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prihlásenie - Bazoš Car Watcher</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 400px;
        }
        
        .login-box h1 {
            text-align: center;
            margin-bottom: 30px;
            color: #1f2937;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #374151;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .button {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
        }
        
        .button:hover {
            background: #5568d3;
        }
        
        .error {
            color: #ef4444;
            text-align: center;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🚗 Bazoš Car Watcher</h1>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="form-group">
                <label>Heslo:</label>
                <input type="password" name="password" required autofocus>
            </div>
            <button type="submit" class="button">🔓 Prihlásiť</button>
        </form>
    </div>
</body>
</html>
"""

# =========================
# ROUTES
# =========================
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect('/login')
    
    config = load_config()
    is_running = get_service_status()
    recent_matches = get_recent_matches(10)
    
    message = session.pop('message', None)
    message_type = session.pop('message_type', 'success')
    
    return render_template_string(
        HTML_TEMPLATE,
        config=config,
        is_running=is_running,
        recent_matches=recent_matches,
        message=message,
        message_type=message_type
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/')
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Nesprávne heslo!")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

@app.route('/save', methods=['POST'])
def save():
    if not session.get('logged_in'):
        return redirect('/login')
    
    config = load_config()
    
    # Location
    config['location'] = {
        'hlokalita': request.form.get('hlokalita', '97101'),
        'humkreis': int(request.form.get('humkreis', 5))
    }
    
    # Filters
    config['filters'] = {
        'min_year': int(request.form.get('min_year', 2005)),
        'max_km': int(request.form.get('max_km', 300000)),
        'min_price': int(request.form.get('min_price', 1500)),
        'min_score': int(request.form.get('min_score', 2)),
        'pages_per_list': int(request.form.get('pages_per_list', 10))
    }
    
    # Brands
    new_brands = {}
    for brand in config.get('brands', {}).keys():
        if request.form.get(f'brand_enabled_{brand}'):
            fuels = []
            if request.form.get(f'brand_{brand}_benz'):
                fuels.append('benz')
            if request.form.get(f'brand_{brand}_dies'):
                fuels.append('dies')
            if fuels:
                new_brands[brand] = fuels
    config['brands'] = new_brands
    
    # Telegram
    config['telegram'] = {
        'bot_token': request.form.get('bot_token', ''),
        'chat_id': request.form.get('chat_id', '')
    }
    
    # Save
    if save_config(config):
        session['message'] = "✅ Nastavenia uložené!"
        session['message_type'] = 'success'
    else:
        session['message'] = "❌ Chyba pri ukladaní!"
        session['message_type'] = 'error'
    
    return redirect('/')

@app.route('/restart')
def restart():
    if not session.get('logged_in'):
        return redirect('/login')
    
    if restart_service():
        session['message'] = "✅ Služba reštartovaná!"
        session['message_type'] = 'success'
    else:
        session['message'] = "❌ Chyba pri reštartovaní!"
        session['message_type'] = 'error'
    
    return redirect('/')

@app.route('/stop')
def stop():
    if not session.get('logged_in'):
        return redirect('/login')
    
    if stop_service():
        session['message'] = "✅ Služba zastavená!"
        session['message_type'] = 'success'
    else:
        session['message'] = "❌ Chyba pri zastavovaní!"
        session['message_type'] = 'error'
    
    return redirect('/')

@app.route('/download')
def download():
    if not session.get('logged_in'):
        return redirect('/login')
    
    if MATCHES_CSV.exists():
        return send_file(MATCHES_CSV, as_attachment=True, download_name='matches.csv')
    else:
        session['message'] = "❌ CSV súbor neexistuje!"
        session['message_type'] = 'error'
        return redirect('/')

# =========================
# MAIN
# =========================
if __name__ == '__main__':
    print("=" * 60)
    print("🌐 Bazoš Car Watcher - Web Admin")
    print("=" * 60)
    print("📍 URL: http://0.0.0.0:5000")
    print(f"🔑 Heslo: {ADMIN_PASSWORD}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
