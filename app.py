import os
import time
import requests
import schedule
import threading
import json
from datetime import datetime
from flask import Flask, jsonify, render_template_string

# Çevresel değişkenlerden bilgileri al
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "7930326081:AAEciV70HcbcJuonGLli_RnQrT_tx9z-4-4")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1356415148")  # @m_swag1 için chat ID
G2G_USERNAME = os.environ.get("G2G_USERNAME", "")  # Çevresel değişkenden alınacak
G2G_PASSWORD = os.environ.get("G2G_PASSWORD", "")  # Çevresel değişkenden alınacak

# Flask uygulaması
app = Flask(__name__)

# Sistem durumunu takip etmek için global değişkenler
app_status = {
    "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "is_running": True,
    "last_heartbeat": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "messages": []
}

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>G2G Telegram Bildirim Sistemi</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        .card {
            background: #f9f9f9;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 3px;
            color: white;
            font-weight: bold;
        }
        .status.running {
            background-color: #2ecc71;
        }
        .status.error {
            background-color: #e74c3c;
        }
        .messages {
            max-height: 300px;
            overflow-y: auto;
        }
        .message {
            padding: 10px;
            margin-bottom: 10px;
            border-left: 3px solid #3498db;
        }
        .message .time {
            color: #7f8c8d;
            font-size: 0.8em;
        }
        button {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 3px;
            cursor: pointer;
        }
        button:hover {
            background-color: #2980b9;
        }
    </style>
</head>
<body>
    <h1>G2G Telegram Bildirim Sistemi</h1>
    
    <div class="card">
        <h2>Sistem Durumu</h2>
        <p>
            <strong>Durum:</strong> 
            <span class="status running">Çalışıyor</span>
        </p>
        <p><strong>Başlangıç Zamanı:</strong> {{ status.started_at }}</p>
        <p><strong>Son Kalp Atışı:</strong> {{ status.last_heartbeat }}</p>
    </div>
    
    <div class="card">
        <h2>Sistem Mesajları</h2>
        <div class="messages">
            {% if status.messages %}
                {% for msg in status.messages %}
                    <div class="message">
                        <div class="time">{{ msg.time }}</div>
                        <div class="content">{{ msg.message }}</div>
                    </div>
                {% endfor %}
            {% else %}
                <p>Henüz mesaj yok.</p>
            {% endif %}
        </div>
    </div>
    
    <div class="card">
        <h2>Manuel Kontroller</h2>
        <button onclick="location.href='/send-heartbeat'">Kalp Atışı Gönder</button>
    </div>
</body>
</html>
"""

def send_telegram_message(message):
    """Telegram üzerinden mesaj gönder"""
    telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    try:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(telegram_api_url, data=payload)
        
        if response.status_code == 200:
            log_message(f"Telegram mesajı başarıyla gönderildi")
            return True
        else:
            log_message(f"Telegram mesajı gönderilirken hata: {response.text}")
            return False
    
    except Exception as e:
        log_message(f"Telegram mesajı gönderilirken hata: {e}")
        return False

def log_message(message):
    """Sistem mesajını logla"""
    print(message)
    app_status["messages"].insert(0, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": message
    })
    
    # En fazla 100 mesaj sakla
    if len(app_status["messages"]) > 100:
        app_status["messages"] = app_status["messages"][:100]

def send_heartbeat():
    """Telegram'a kalp atışı mesajı gönder"""
    global app_status
    
    app_status["last_heartbeat"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message("Kalp atışı gönderiliyor...")
    
    send_telegram_message("💓 G2G Bildirim Sistemi çalışıyor - Heartbeat")
    
    log_message("Kalp atışı gönderildi.")
    
    return True

# Flask route'ları
@app.route('/')
def index():
    """Ana sayfa - sistem durumunu gösterir"""
    return render_template_string(HTML_TEMPLATE, status=app_status)

@app.route('/api/status')
def api_status():
    """API endpoint - JSON formatında sistem durumunu döndürür"""
    return jsonify({
        "status": "running" if app_status["is_running"] else "stopped",
        "message": "G2G Telegram Bildirim Sistemi çalışıyor",
        "stats": app_status
    })

@app.route('/health')
def health():
    """Sağlık kontrolü - sistemin çalışıp çalışmadığını kontrol eder"""
    return jsonify({
        "status": "ok",
        "uptime": str(datetime.now() - datetime.strptime(app_status["started_at"], "%Y-%m-%d %H:%M:%S"))
    })

@app.route('/send-heartbeat')
def trigger_heartbeat():
    """Manuel olarak heartbeat gönder"""
    send_heartbeat()
    return jsonify({
        "status": "ok",
        "message": "Heartbeat gönderildi"
    })

def scheduler_thread():
    """Zamanlayıcı thread'i"""
    log_message("Zamanlayıcı başlatılıyor...")
    
    # Her 6 saatte bir heartbeat gönder
    schedule.every(6).hours.do(send_heartbeat)
    
    # Sürekli döngü
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Başlangıç bildirimi gönder
    log_message("G2G Telegram Bildirim Sistemi başlatılıyor...")
    send_telegram_message("🚀 G2G Telegram Bildirim Sistemi başlatıldı ve çalışıyor!")
    
    # İlk heartbeat
    send_heartbeat()
    
    # Zamanlayıcıyı ayrı bir thread'de başlat
    scheduler = threading.Thread(target=scheduler_thread)
    scheduler.daemon = True
    scheduler.start()
    
    # Flask uygulamasını başlat
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
