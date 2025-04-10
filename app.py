import os
import time
import requests
import schedule
import threading
import json
from datetime import datetime
from flask import Flask, jsonify
from dotenv import load_dotenv

# .env dosyasını yükle (eğer varsa)
load_dotenv()

# Çevresel değişkenlerden bilgileri al
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "7930326081:AAEciV70HcbcJuonGLli_RnQrT_tx9z-4-4")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1356415148")  # @m_swag1 için chat ID
G2G_USERNAME = os.environ.get("G2G_USERNAME", "")  # Çevresel değişkenden alınacak
G2G_PASSWORD = os.environ.get("G2G_PASSWORD", "")  # Çevresel değişkenden alınacak

# Son kontrol edildiğinde görülen mesaj sayısı
last_messages = set()
# Session ve cookies
session = requests.Session()

# Flask uygulaması
app = Flask(__name__)

# Sistem durumunu takip etmek için global değişkenler
app_status = {
    "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "is_logged_in": False,
    "last_check": None,
    "new_messages_count": 0,
    "total_messages_found": 0,
    "errors": []
}

class G2GAPIMonitor:
    def __init__(self):
        self.logged_in = False
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.g2g.com',
            'Referer': 'https://www.g2g.com/'
        })
    
    def login(self):
        """G2G'ye API üzerinden giriş yap"""
        global app_status
        
        try:
            # Kullanıcı adı/şifre kontrolü
            if not G2G_USERNAME or not G2G_PASSWORD:
                print("G2G kullanıcı adı veya şifresi tanımlanmamış!")
                self.send_telegram_message("⚠️ G2G kullanıcı adı veya şifresi çevresel değişkenlerde tanımlanmamış! Lütfen doğru şekilde ayarlayın.")
                app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                           "error": "G2G kullanıcı adı veya şifresi tanımlanmamış"})
                return False
            
            print(f"G2G.com'a giriş yapılıyor...")
            
            # Önce ana sayfaya giderek CSRF token veya gerekli cookieleri alalım
            response = self.session.get('https://www.g2g.com/')
            if response.status_code != 200:
                error_msg = f"Ana sayfa yüklenemedi. Status code: {response.status_code}"
                print(error_msg)
                app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                           "error": error_msg})
                return False
            
            # Login endpoint'i
            login_url = 'https://www.g2g.com/api/login'
            
            # Login verisi
            login_data = {
                'email': G2G_USERNAME,
                'password': G2G_PASSWORD,
                'rememberMe': True
            }
            
            # Login isteği gönderme
            login_response = self.session.post(login_url, json=login_data)
            
            # Giriş başarılı mı kontrol et
            if login_response.status_code == 200:
                try:
                    json_response = login_response.json()
                    if json_response.get('status') == 'success':
                        self.logged_in = True
                        app_status["is_logged_in"] = True
                        print("G2G.com'a başarıyla giriş yapıldı.")
                        return True
                    else:
                        error_msg = f"Giriş başarısız. Hata: {json_response.get('message', 'Bilinmeyen hata')}"
                        print(error_msg)
                        self.send_telegram_message(f"❌ G2G giriş başarısız: {json_response.get('message', 'Bilinmeyen hata')}")
                        app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                                   "error": error_msg})
                        return False
                except Exception as e:
                    error_msg = f"JSON yanıtı işlenirken hata: {e}"
                    print(error_msg)
                    app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                               "error": error_msg})
            else:
                error_msg = f"Giriş başarısız. Status code: {login_response.status_code}"
                print(error_msg)
                self.send_telegram_message(f"❌ G2G giriş başarısız. Status code: {login_response.status_code}")
                app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                           "error": error_msg})
                return False
            
            return False
        
        except Exception as e:
            error_msg = f"G2G.com'a giriş yapılırken hata oluştu: {e}"
            print(error_msg)
            self.send_telegram_message(f"❌ G2G giriş hatası: {str(e)[:100]}...")
            app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                       "error": error_msg})
            return False

    def check_for_new_messages(self):
        """API üzerinden mesajları kontrol et"""
        global last_messages, app_status
        
        try:
            if not self.logged_in:
                if not self.login():
                    return
            
            print("G2G mesajları kontrol ediliyor...")
            app_status["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Mesajları almak için API endpoint
            messages_url = 'https://www.g2g.com/api/chat/channel/list'
            
            # İsteği gönder
            response = self.session.get(messages_url)
            
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    
                    # Yanıtın doğru formatta olduğunu kontrol et
                    if json_response.get('status') == 'success' and 'data' in json_response:
                        channels = json_response['data'].get('channels', [])
                        
                        # Yeni mesajları kontrol et
                        new_messages = []
                        
                        for channel in channels:
                            # Okunmamış mesaj sayısı
                            unread_count = channel.get('unreadCount', 0)
                            
                            if unread_count > 0:
                                # Mesaj bilgilerini al
                                channel_id = channel.get('id')
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
                        
                        # Yeni mesajları bildir
                        if new_messages:
                            print(f"{len(new_messages)} yeni mesaj bulundu.")
                            self.send_telegram_notifications(new_messages)
                            app_status["new_messages_count"] += len(new_messages)
                            app_status["total_messages_found"] += len(new_messages)
                        else:
                            print("Yeni mesaj bulunmadı.")
                    else:
                        print("Mesajlar alınamadı. API yanıtı beklenen formatta değil.")
                        if 'message' in json_response:
                            print(f"API mesajı: {json_response['message']}")
                            
                        # Oturum düşmüş olabilir, tekrar login olmayı dene
                        self.logged_in = False
                        app_status["is_logged_in"] = False
                        
                except Exception as e:
                    error_msg = f"JSON yanıtı işlenirken hata: {e}"
                    print(error_msg)
                    app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                               "error": error_msg})
            else:
                error_msg = f"Mesajlar alınamadı. Status code: {response.status_code}"
                print(error_msg)
                app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                           "error": error_msg})
                # Oturum düşmüş olabilir, tekrar login olmayı dene
                self.logged_in = False
                app_status["is_logged_in"] = False
                
        except Exception as e:
            error_msg = f"Mesaj kontrolü sırasında hata: {e}"
            print(error_msg)
            app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                       "error": error_msg})
            self.logged_in = False
            app_status["is_logged_in"] = False
    
    def send_telegram_notifications(self, new_messages):
        """Telegram üzerinden bildirimleri gönder"""
        for msg in new_messages:
            # Mesaj metni
            message_text = f"🔔 *G2G.com Yeni Mesaj!*\n\n👤 *Gönderen:* {msg['sender']}\n💬 *Mesaj:* {msg['message']}\n\n🔗 Cevaplamak için: https://www.g2g.com/chat/#/"
            
            self.send_telegram_message(message_text)
    
    def send_telegram_message(self, message):
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
                print(f"Telegram mesajı başarıyla gönderildi")
                return True
            else:
                error_msg = f"Telegram mesajı gönderilirken hata: {response.text}"
                print(error_msg)
                app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                           "error": error_msg})
                return False
        
        except Exception as e:
            error_msg = f"Telegram mesajı gönderilirken hata: {e}"
            print(error_msg)
            app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                       "error": error_msg})
            return False
    
    @staticmethod
    def send_telegram_message_static(message):
        """Statik method olarak Telegram mesajı gönder (instance olmadan çağrılabilir)"""
        telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        try:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(telegram_api_url, data=payload)
            
            if response.status_code == 200:
                print(f"Telegram mesajı başarıyla gönderildi")
                return True
            else:
                print(f"Telegram mesajı gönderilirken hata: {response.text}")
                return False
        
        except Exception as e:
            print(f"Telegram mesajı gönderilirken hata: {e}")
            return False

# Flask route'ları
@app.route('/')
def index():
    """Ana sayfa - sistem durumunu gösterir"""
    return jsonify({
        "status": "running",
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

@app.route('/force-check')
def force_check():
    """Manuel kontrol - hemen bir kontrol yapar"""
    threading.Thread(target=check_messages).start()
    return jsonify({
        "status": "ok",
        "message": "Mesaj kontrolü başlatıldı"
    })

def check_messages():
    """Zamanlayıcı tarafından çağrılacak fonksiyon"""
    try:
        monitor = G2GAPIMonitor()
        monitor.check_for_new_messages()
    except Exception as e:
        error_msg = f"Mesaj kontrolü sırasında beklenmeyen hata: {e}"
        print(error_msg)
        app_status["errors"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                   "error": error_msg})
        # Statik yöntemle Telegram'a hata mesajı gönder
        G2GAPIMonitor.send_telegram_message_static(f"❌ Kritik hata: {str(e)}")

def scheduler_thread():
    """Zamanlayıcı thread'i"""
    print("Zamanlayıcı başlatılıyor...")
    
    # Her 5 dakikada bir kontrol et
    schedule.every(5).minutes.do(check_messages)
    
    # Heartbeat mesajı - sistemin hala çalıştığından emin olmak için
    def send_heartbeat():
        G2GAPIMonitor.send_telegram_message_static("💓 G2G Bildirim Sistemi çalışıyor - Günlük kontrol")
        
    schedule.every(24).hours.do(send_heartbeat)
    
    # Sürekli döngü
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Başlangıç bildirimi gönder
    G2GAPIMonitor.send_telegram_message_static("🚀 G2G Telegram Bildirim Sistemi başlatıldı! Mesajlarınız artık takip ediliyor.")
    
    # İlk kontrol
    check_messages()
    
    # Zamanlayıcıyı ayrı bir thread'de başlat
    scheduler = threading.Thread(target=scheduler_thread)
    scheduler.daemon = True
    scheduler.start()
    
    # Flask uygulamasını başlat
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
