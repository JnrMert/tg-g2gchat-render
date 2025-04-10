import os
import time
import requests
import schedule
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv

# .env dosyasını yükle (eğer varsa)
load_dotenv()

# Çevresel değişkenlerden bilgileri al
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "7930326081:AAEciV70HcbcJuonGLli_RnQrT_tx9z-4-4")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1356415148")  # @m_swag1 için chat ID
G2G_USERNAME = os.environ.get("G2G_USERNAME", "")  # Çevresel değişkenden alınacak
G2G_PASSWORD = os.environ.get("G2G_PASSWORD", "")  # Çevresel değişkenden alınacak

# Son kontrol edildiğinde görülen mesaj sayısı
last_message_count = 0
# Son görülen mesajlar
last_seen_messages = set()

class G2GMonitor:
    def __init__(self):
        self.setup_driver()
        self.logged_in = False

    def setup_driver(self):
        # Render veya Heroku ortamı için Chrome ayarları
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Cloud ortamında çalışıyorsak ChromeDriver için özel ayarlar
        if os.environ.get('RENDER') or os.environ.get('HEROKU_APP_NAME'):
            chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
            self.driver = webdriver.Chrome(
                executable_path=os.environ.get("CHROMEDRIVER_PATH"),
                options=chrome_options
            )
        else:
            # Lokal ortamda normal çalıştır
            self.driver = webdriver.Chrome(options=chrome_options)

    def login(self):
        try:
            # Kullanıcı adı/şifre kontrolü
            if not G2G_USERNAME or not G2G_PASSWORD:
                print("G2G kullanıcı adı veya şifresi tanımlanmamış!")
                self.send_telegram_message("⚠️ G2G kullanıcı adı veya şifresi çevresel değişkenlerde tanımlanmamış! Lütfen doğru şekilde ayarlayın.")
                return False
                
            self.driver.get("https://www.g2g.com/login")
            
            # Login sayfasının yüklenmesini bekle
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'].q-field__native"))
            )
            
            # E-mail ve şifre alanlarını bul
            email_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'].q-field__native")
            password_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password'].q-field__native")
            
            if not email_inputs or not password_inputs:
                print("E-mail veya şifre alanları bulunamadı.")
                return False
            
            # E-mail ve şifre gir
            email_inputs[0].send_keys(G2G_USERNAME)
            password_inputs[0].send_keys(G2G_PASSWORD)
            
            # Giriş butonunu bul ve tıkla
            login_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Giriş')]")
            
            if not login_buttons:
                login_buttons = self.driver.find_elements(By.CSS_SELECTOR, "form button[type='submit']")
            
            if not login_buttons:
                print("Giriş butonu bulunamadı.")
                return False
            
            login_buttons[0].click()
            
            # 2FA'yı kaldırdığınız için direk giriş yapmalı
            # Giriş başarılı mı kontrol et - birkaç farklı yöntem deneyelim
            try:
                # Dashboard'a yönlendirme kontrolü
                WebDriverWait(self.driver, 30).until(
                    EC.url_contains("g2g.com/dashboard")
                )
                self.logged_in = True
                print("G2G.com'a başarıyla giriş yapıldı.")
                return True
            except TimeoutException:
                # Ana sayfaya yönlendirme kontrolü
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.url_contains("g2g.com")
                    )
                    # Herhangi bir profil veya kullanıcı menüsü var mı kontrol et
                    if self.driver.find_elements(By.XPATH, "//*[contains(text(), 'My Profile') or contains(text(), 'Profilim') or contains(text(), 'Account')]"):
                        self.logged_in = True
                        print("G2G.com'a başarıyla giriş yapıldı.")
                        return True
                except:
                    pass
                
                # Son kontrol: Oturum açma sayfa URL'sinde değilsek ve hata mesajı yoksa giriş başarılı olabilir
                if "/login" not in self.driver.current_url:
                    self.logged_in = True
                    print("G2G.com'a giriş yapılmış olabilir.")
                    return True
                    
                print("G2G.com'a giriş yapılamadı.")
                self.send_telegram_message("❌ G2G.com'a giriş yapılamadı. Lütfen kullanıcı adı ve şifrenizi kontrol edin.")
                return False
        
        except Exception as e:
            print(f"G2G.com'a giriş yapılırken hata oluştu: {e}")
            self.send_telegram_message(f"❌ G2G giriş hatası: {str(e)[:100]}...")
            return False

    def check_for_new_messages(self):
        global last_message_count, last_seen_messages
        
        try:
            if not self.logged_in:
                if not self.login():
                    return
            
            # Sohbet sayfasına git
            self.driver.get("https://www.g2g.com/chat/#/")
            
            # Sayfanın yüklenmesini bekle
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".g-channel-item--main"))
            )
            
            # Mesaj sayısı bildirimini kontrol et
            try:
                badge_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[role='alert'].q-badge--floating")
                
                if badge_elements:
                    message_count = int(badge_elements[0].text.strip())
                    
                    # Eğer son kontrol edilenden fazla mesaj varsa
                    if message_count > last_message_count:
                        print(f"Yeni mesajlar tespit edildi: {message_count}")
                        
                        # Yeni mesajları al
                        message_elements = self.driver.find_elements(By.CSS_SELECTOR, ".g-channel-item--main")
                        new_messages = []
                        
                        for element in message_elements:
                            try:
                                sender = element.find_element(By.CSS_SELECTOR, ".text-body1").text.strip()
                                message_text_element = element.find_element(By.CSS_SELECTOR, ".text-secondary")
                                message_text = message_text_element.text.strip()
                                
                                # Mesajı benzersiz bir stringge çevir
                                message_key = f"{sender}:{message_text}"
                                
                                # Eğer bu mesajı daha önce görmediysen
                                if message_key not in last_seen_messages:
                                    new_messages.append({"sender": sender, "message": message_text})
                                    last_seen_messages.add(message_key)
                                    
                                    # Son 100 mesaj ile sınırla
                                    if len(last_seen_messages) > 100:
                                        last_seen_messages = set(list(last_seen_messages)[-100:])
                            except Exception as e:
                                print(f"Mesaj ayrıştırılırken hata: {e}")
                        
                        # Son mesaj sayısını güncelle
                        last_message_count = message_count
                        
                        # Yeni mesajları bildir
                        if new_messages:
                            self.send_telegram_notifications(new_messages)
                else:
                    print("Bildirim rozeti bulunamadı. Muhtemelen yeni mesaj yok.")
                
            except Exception as e:
                print(f"Bildirim kontrolü sırasında hata: {e}")
                
        except Exception as e:
            print(f"Mesaj kontrolü sırasında hata: {e}")
            self.logged_in = False  # Oturum düşmüş olabilir, tekrar giriş yapmayı dene
    
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
                print(f"Telegram mesajı gönderilirken hata: {response.text}")
                return False
        
        except Exception as e:
            print(f"Telegram mesajı gönderilirken hata: {e}")
            return False
    
    def close(self):
        """Tarayıcıyı kapat"""
        try:
            self.driver.quit()
        except:
            pass

def check_messages():
    """Zamanlayıcı tarafından çağrılacak fonksiyon"""
    monitor = G2GMonitor()
    try:
        monitor.check_for_new_messages()
    except Exception as e:
        print(f"Kontrol sırasında beklenmeyen hata: {e}")
    finally:
        monitor.close()

def main():
    """Ana program döngüsü"""
    print("G2G Telegram Bildirim Sistemi başlatılıyor...")
    print(f"Ortam: {'Render/Heroku' if os.environ.get('RENDER') or os.environ.get('HEROKU_APP_NAME') else 'Lokal'}")
    
    # İlk kontrol
    check_messages()
    
    # Her 5 dakikada bir kontrol et
    schedule.every(5).minutes.do(check_messages)
    
    # Sürekli döngü
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()