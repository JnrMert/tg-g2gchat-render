import os
import time
import json
import re
import requests
import schedule
import threading
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, jsonify, render_template_string

# Çevresel değişkenlerden bilgileri al
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "7930326081:AAEciV70HcbcJuonGLli_RnQrT_tx9z-4-4")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1356415148")  # @m_swag1 için chat ID
G2G_USERNAME = os.environ.get("G2G_USERNAME", "")  # Çevresel değişkenden alınacak
G2G_PASSWORD = os.environ.get("G2G_PASSWORD", "")  # Çevresel değişkenden alınacak

# Flask uygulaması
app = Flask(__name__)

# Son işlenen mesajları saklayacak set
last_messages = set()

# Sistem durumunu takip etmek için global değişkenler
app_status = {
    "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "is_logged_in": False,
    "last_check": None,
    "new_messages_count": 0,
    "total_messages_found": 0,
    "unread_count": 0,
    "messages": [],
    "errors": []
}

class G2GScraper:
    def __init__(self):
        self.session = requests.Session()
        # Gerçek bir tarayıcı gibi görünmesi için User-Agent ve header'ları ayarla
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })
        self.logged_in = False
    
    def login(self):
        """G2G web sitesine giriş yap"""
        global app_status
        
        try:
            # Kullanıcı adı/şifre kontrolü
            if not G2G_USERNAME or not G2G_PASSWORD:
                log_message("G2G kullanıcı adı veya şifresi tanımlanmamış!")
                send_telegram_message("⚠️ G2G kullanıcı adı veya şifresi çevresel değişkenlerde tanımlanmamış! Lütfen doğru şekilde ayarlayın.")
                app_status["errors"].append("G2G kullanıcı adı veya şifresi tanımlanmamış")
                return False
            
            log_message("G2G.com'a giriş yapılıyor...")
            
            # Önce ana sayfaya git - cookie ve CSRF token almak için
            log_message("Ana sayfa yükleniyor...")
            main_page = self.session.get('https://www.g2g.com/', timeout=30)
            if main_page.status_code != 200:
                log_message(f"Ana sayfa yüklenemedi. Status code: {main_page.status_code}")
                app_status["errors"].append(f"Ana sayfa yüklenemedi. Status code: {main_page.status_code}")
                return False
            
            # Login sayfasına git
            log_message("Login sayfası yükleniyor...")
            login_page = self.session.get('https://www.g2g.com/login', timeout=30)
            if login_page.status_code != 200:
                log_message(f"Login sayfası yüklenemedi. Status code: {login_page.status_code}")
                app_status["errors"].append(f"Login sayfası yüklenemedi. Status code: {login_page.status_code}")
                return False
            
            # BeautifulSoup ile login sayfasını parse et
            soup = BeautifulSoup(login_page.content, 'html.parser')
            
            # CSRF token veya form input'ları ara
            csrf_token = None
            form_inputs = {}
            
            # Muhtemel form ve input'ları bul
            login_form = soup.find('form')
            if login_form:
                inputs = login_form.find_all('input')
                for input_field in inputs:
                    if input_field.get('name'):
                        if 'csrf' in input_field.get('name').lower():
                            csrf_token = input_field.get('value')
                        form_inputs[input_field.get('name')] = input_field.get('value', '')
            
            # Giriş verilerini hazırla
            login_data = {
                'email': G2G_USERNAME,
                'password': G2G_PASSWORD,
                'remember': 'on'
            }
            
            # Bulunan diğer form input'larını ekle
            for key, value in form_inputs.items():
                if key not in login_data:
                    login_data[key] = value
            
            # CSRF token varsa header'a ekle
            if csrf_token:
                self.session.headers.update({
                    'X-CSRF-TOKEN': csrf_token
                })
            
            # Referrer ayarla
            self.session.headers.update({
                'Referer': 'https://www.g2g.com/login'
            })
            
            # Giriş yap
            log_message("Giriş yapılıyor...")
            login_response = None
            
            # Form gönderim URL'si - login formundan alınabilir
            login_url = 'https://www.g2g.com/login'
            if login_form and login_form.get('action'):
                login_url = login_form.get('action')
                # Relative URL ise absolute URL'e çevir
                if login_url.startswith('/'):
                    login_url = 'https://www.g2g.com' + login_url
            
            # Giriş yapma denemesi - POST
            login_response = self.session.post(login_url, data=login_data, allow_redirects=True, timeout=30)
            
            # Giriş başarılı mı kontrol et
            # Başarılı bir giriş genellikle ana sayfaya veya dashboard'a yönlendirilir
            
            # Dashboard sayfasına erişmeyi dene
            log_message("Giriş kontrolü yapılıyor...")
            dashboard_page = self.session.get('https://www.g2g.com/dashboard', timeout=30)
            
            # Giriş başarılı mı kontrol et - kullanıcı adının sayfada görünüp görünmediğine bak
            soup = BeautifulSoup(dashboard_page.content, 'html.parser')
            user_elements = soup.find_all(string=re.compile('profile|account|logout', re.IGNORECASE))
            
            if dashboard_page.status_code == 200 and user_elements:
                self.logged_in = True
                app_status["is_logged_in"] = True
                log_message("G2G.com'a başarıyla giriş yapıldı.")
                return True
            else:
                # Chat sayfasına erişmeyi dene - bazı siteler dashboard yerine ana sayfaya yönlendirebilir
                chat_page = self.session.get('https://www.g2g.com/chat/#/', timeout=30)
                if chat_page.status_code == 200 and 'g-channel-item--main' in chat_page.text:
                    self.logged_in = True
                    app_status["is_logged_in"] = True
                    log_message("G2G.com'a başarıyla giriş yapıldı (chat erişimi başarılı).")
                    return True
                
                log_message("G2G.com'a giriş yapılamadı. Yetkilendirme başarısız.")
                app_status["errors"].append("G2G.com'a giriş yapılamadı. Yetkilendirme başarısız.")
                send_telegram_message("❌ G2G'ye giriş yapılamadı. Kullanıcı adı ve şifrenizi kontrol edin.")
                return False
            
        except Exception as e:
            log_message(f"Giriş sırasında hata: {str(e)}")
            app_status["errors"].append(f"Giriş sırasında hata: {str(e)}")
            send_telegram_message(f"❌ G2G giriş hatası: {str(e)[:100]}...")
            return False
    
    def check_for_new_messages(self):
        """G2G chat sayfasını kontrol ederek yeni mesajları bul"""
        global last_messages, app_status
        
        try:
            if not self.logged_in:
                if not self.login():
                    return
            
            log_message("G2G mesajları kontrol ediliyor...")
            app_status["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Chat sayfasını yükle
            chat_response = self.session.get('https://www.g2g.com/chat/#/', timeout=30)
            
            if chat_response.status_code != 200:
                log_message(f"Chat sayfası yüklenemedi. Status code: {chat_response.status_code}")
                app_status["errors"].append(f"Chat sayfası yüklenemedi. Status code: {chat_response.status_code}")
                # Oturum düşmüş olabilir
                self.logged_in = False
                app_status["is_logged_in"] = False
                return
            
            # BeautifulSoup ile sayfa içeriğini parse et
            soup = BeautifulSoup(chat_response.content, 'html.parser')
            
            # Chat içeriğini kontrol et
            chat_items = soup.select('.g-channel-item--main')
            
            if not chat_items:
                # JavaScript tabanlı sayfada elementler doğrudan görünmeyebilir
                # Bu durumda JavaScript kodundan veri çekmeyi deneyelim
                # Genellikle sayfa kaynak kodunda JSON verisi bulunabilir
                
                # window.__INITIAL_STATE__ veya benzer bir değişken içinde veri arayalım
                initial_state_pattern = re.compile(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', re.DOTALL)
                match = initial_state_pattern.search(chat_response.text)
                
                if match:
                    try:
                        # JSON veriyi parse et
                        json_data = json.loads(match.group(1))
                        
                        # JSON yapısına göre mesajları çıkarmayı dene
                        # Bu kısım G2G'nin spesifik veri yapısına göre özelleştirilmelidir
                        if 'chat' in json_data and 'channels' in json_data['chat']:
                            channels = json_data['chat']['channels']
                            
                            # Yeni mesajları topla
                            new_messages = []
                            unread_count = 0
                            
                            for channel_id, channel in channels.items():
                                if 'unreadCount' in channel and channel['unreadCount'] > 0:
                                    unread_count += channel['unreadCount']
                                    
                                    # Mesaj bilgilerini al
                                    sender_name = channel.get('name', 'Bilinmeyen')
                                    last_message = channel.get('lastMessage', {})
                                    message_text = last_message.get('text', 'Mesaj içeriği alınamadı')
                                    
                                    # Mesajı benzersiz bir ID ile tanımla
                                    message_id = f"{channel_id}:{message_text}"
                                    
                                    # Eğer bu mesajı daha önce görmediysen
                                    if message_id not in last_messages:
                                        new_messages.append({
                                            'sender': sender_name,
                                            'message': message_text,
                                            'channel_id': channel_id
                                        })
                                        last_messages.add(message_id)
                                        
                                        # Son 100 mesaj ile sınırla
                                        if len(last_messages) > 100:
                                            last_messages = set(list(last_messages)[-100:])
                            
                            app_status["unread_count"] = unread_count
                            
                            # Yeni mesajları bildir
                            if new_messages:
                                log_message(f"{len(new_messages)} yeni mesaj bulundu.")
                                send_telegram_notifications(new_messages)
                                app_status["new_messages_count"] += len(new_messages)
                                app_status["total_messages_found"] += len(new_messages)
                                return
                    except Exception as e:
                        log_message(f"JSON verisi işlenirken hata: {str(e)}")
                        app_status["errors"].append(f"JSON verisi işlenirken hata: {str(e)}")
                
                # Mesajlar bulunamadı - sayfa yapısı beklenenden farklı
                log_message("Chat mesajları bulunamadı. Sayfa yapısı beklenenden farklı olabilir.")
                # Hata olmasa da sayfanın XHR istekleri incelenebilir
                # G2G'nin API endpoint'lerini belirlemek için ağ trafiği analiz edilmeli
            else:
                # Chat itemleri bulundu, işle
                log_message(f"{len(chat_items)} chat öğesi bulundu.")
                
                new_messages = []
                unread_count = 0
                
                # Her bir chat öğesini işle
                for item in chat_items:
                    try:
                        # Göndereni bul
                        sender_element = item.select_one('.text-body1')
                        sender = sender_element.text.strip() if sender_element else "Bilinmeyen"
                        
                        # Mesaj metnini bul
                        message_element = item.select_one('.text-secondary')
                        message_text = message_element.text.strip() if message_element else "Mesaj içeriği alınamadı"
                        
                        # Okunmamış sayısını bul
                        badge_element = item.parent.select_one('.q-badge[role="alert"]')
                        if badge_element:
                            try:
                                unread_count += int(badge_element.text.strip())
                            except ValueError:
                                pass
                        
                        # Benzersiz ID oluştur - Gerçek channel ID alınamıyorsa
                        # gönderenin adı ve mesaj metni birleşimi kullanılabilir
                        message_id = f"{sender}:{message_text}"
                        
                        # Eğer yeni bir mesaj ise, ekle
                        if message_id not in last_messages:
                            new_messages.append({
                                'sender': sender,
                                'message': message_text
                            })
                            last_messages.add(message_id)
                            
                            # Son 100 mesaj ile sınırla
                            if len(last_messages) > 100:
                                last_messages = set(list(last_messages)[-100:])
                    except Exception as e:
                        log_message(f"Chat öğesi işlenirken hata: {str(e)}")
                        app_status["errors"].append(f"Chat öğesi işlenirken hata: {str(e)}")
                
                app_status["unread_count"] = unread_count
                
                # Yeni mesajları bildir
                if new_messages:
                    log_message(f"{len(new_messages)} yeni mesaj bulundu.")
                    send_telegram_notifications(new_messages)
                    app_status["new_messages_count"] += len(new_messages)
                    app_status["total_messages_found"] += len(new_messages)
                else:
                    log_message("Yeni mesaj bulunamadı.")
            
        except Exception as e:
            log_message(f"Mesaj kontrolü sırasında hata: {str(e)}")
            app_status["errors"].append(f"Mesaj kontrolü sırasında hata: {str(e)}")
            # Oturum düşmüş olabilir
            self.logged_in = False
            app_status["is_logged_in"] = False

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
        .error {
            padding: 10px;
            margin-bottom: 10px;
            border-left: 3px solid #e74c3c;
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
            <span class="status {{ 'running' if status.is_logged_in else 'error' }}">
                {{ 'Çalışıyor' if status.is_logged_in else 'Giriş Yapılamadı' }}
            </span>
        </p>
        <p><strong>Başlangıç Zamanı:</strong> {{ status.started_at }}</p>
        <p><strong>Son Kontrol:</strong> {{ status.last_check or 'Henüz kontrol edilmedi' }}</p>
        <p><strong>Okunmamış Mesaj Sayısı:</strong> {{ status.unread_count }}</p>
        <p><strong>Bulunan Toplam Mesaj:</strong> {{ status.total_messages_found }}</p>
        <p><strong>Son Kontrolde Bulunan Yeni Mesaj:</strong> {{ status.new_messages_count }}</p>
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
    
    {% if status.errors %}
    <div class="card">
        <h2>Hatalar</h2>
        <div class="messages">
            {% for error in status.errors %}
                <div class="error">
                    <div class="time">{{ error.time }}</div>
                    <div class="content">{{ error.message }}</div>
                </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}
    
    <div class="card">
        <h2>Manuel Kontroller</h2>
        <button onclick="location.href='/force-check'">Mesajları Kontrol Et</button>
        <button onclick="location.href='/force-login'">Yeniden Giriş Yap</button>
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
            app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                         "message": f"Telegram mesajı gönderilirken hata: {response.text}"})
            return False
    
    except Exception as e:
        log_message(f"Telegram mesajı gönderilirken hata: {e}")
        app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                     "message": f"Telegram mesajı gönderilirken hata: {e}"})
        return False

def send_telegram_notifications(new_messages):
    """Telegram üzerinden bildirimleri gönder"""
    for msg in new_messages:
        # Mesaj metni
        message_text = f"🔔 *G2G.com Yeni Mesaj!*\n\n👤 *Gönderen:* {msg['sender']}\n💬 *Mesaj:* {msg['message']}\n\n🔗 Cevaplamak için: https://www.g2g.com/chat/#/"
        
        send_telegram_message(message_text)

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

# Flask route'ları
@app.route('/')
def index():
    """Ana sayfa - sistem durumunu gösterir"""
    return render_template_string(HTML_TEMPLATE, status=app_status)

@app.route('/api/status')
def api_status():
    """API endpoint - JSON formatında sistem durumunu döndürür"""
    return jsonify({
        "status": "running" if app_status["is_logged_in"] else "error",
        "message": "G2G Telegram Bildirim Sistemi çalışıyor",
        "stats": app_status
    })

@app.route('/health')
def health():
    """Sağlık kontrolü - sistemin çalışıp çalışmadığını kontrol eder"""
    return jsonify({
        "status": "ok",
        "uptime": str(datetime.now() - datetime.strptime(app_status["started_at"], "%Y-%m-%d %H:%M:%S")),
        "logged_in": app_status["is_logged_in"]
    })

@app.route('/force-check')
def force_check():
    """Manuel mesaj kontrolü başlat"""
    log_message("Manuel mesaj kontrolü başlatılıyor...")
    threading.Thread(target=check_messages).start()
    return jsonify({
        "status": "ok",
        "message": "Mesaj kontrolü başlatıldı"
    })

@app.route('/force-login')
def force_login():
    """Manuel olarak yeniden giriş yap"""
    log_message("Yeniden giriş yapılıyor...")
    scraper = G2GScraper()
    if scraper.login():
        return jsonify({
            "status": "ok",
            "message": "Giriş başarılı"
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Giriş başarısız"
        })

def check_messages():
    """Zamanlayıcı tarafından çağrılacak fonksiyon"""
    try:
        scraper = G2GScraper()
        scraper.check_for_new_messages()
    except Exception as e:
        log_message(f"Mesaj kontrolü sırasında beklenmeyen hata: {str(e)}")
        app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                     "message": f"Mesaj kontrolü sırasında beklenmeyen hata: {str(e)}"})
        send_telegram_message(f"❌ Kritik hata: {str(e)}")

def scheduler_thread():
    """Zamanlayıcı thread'i"""
    log_message("Zamanlayıcı başlatılıyor...")
    
    # Her 5 dakikada bir mesajları kontrol et
    schedule.every(5).minutes.do(check_messages)
    
    # Heartbeat mesajı - sistemin hala çalıştığından emin olmak için
    def send_heartbeat():
        log_message("Günlük durum raporu gönderiliyor...")
        
        status_message = f"📊 *G2G Bildirim Sistemi Durum Raporu*\n\n" \
                         f"• Durum: {'✅ Çalışıyor' if app_status['is_logged_in'] else '❌ Giriş Yapılamadı'}\n" \
                         f"• Çalışma Süresi: {str(datetime.now() - datetime.strptime(app_status['started_at'], '%Y-%m-%d %H:%M:%S')).split('.')[0]}\n" \
                         f"• Toplam Bulunan Mesaj: {app_status['total_messages_found']}\n" \
                         f"• Okunmamış Mesaj: {app_status['unread_count']}\n\n" \
                         f"🔗 Kontrol Paneli: https://[your-render-url]/"
        
        send_telegram_message(status_message)
        
    schedule.every(24).hours.do(send_heartbeat)
    
    # Sürekli döngü
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Başlangıç bildirimi gönder
    log_message("G2G Telegram Bildirim Sistemi başlatılıyor...")
    send_telegram_message("🚀 G2G Telegram Bildirim Sistemi başlatıldı! Mesajlarınız artık takip ediliyor.")
    
    # İlk mesaj kontrolü
    check_messages()
    
    # Zamanlayıcıyı ayrı bir thread'de başlat
    scheduler = threading.Thread(target=scheduler_thread)
    scheduler.daemon = True
    scheduler.start()
    
    # Flask uygulamasını başlat
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
