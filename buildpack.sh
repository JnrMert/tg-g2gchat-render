#!/bin/bash

# Chrome ve ChromeDriver kurulumu
# Bu script Render ve benzeri servislerde çalışacak şekilde tasarlanmıştır

# Güncelleme: Kurulan versiyonları loglama için bash komutları eklendi

echo "========== Chrome ve ChromeDriver Kurulumu =========="

# Gerekli araçların kurulumu
echo "Gerekli paketler yükleniyor..."
apt-get update
apt-get install -y wget unzip gnupg curl

# Google Chrome repository ekleme
echo "Google Chrome repo ekleniyor..."
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Chrome kurulumu
echo "Google Chrome kuruluyor..."
apt-get update
apt-get install -y google-chrome-stable

# Chrome sürümünü kontrol et
CHROME_VERSION=$(google-chrome-stable --version)
echo "Kurulu Chrome sürümü: $CHROME_VERSION"

# Chrome sürüm numarasını al
CHROME_MAJOR_VERSION=$(echo "$CHROME_VERSION" | cut -d ' ' -f 3 | cut -d '.' -f 1)
echo "Chrome ana sürüm: $CHROME_MAJOR_VERSION"

# ChromeDriver kurulumu - Chrome sürümüne uygun
echo "ChromeDriver indiriliyor... (Chrome $CHROME_MAJOR_VERSION ile uyumlu)"

# En son ChromeDriver sürümünü al
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_MAJOR_VERSION")
echo "ChromeDriver sürümü: $CHROMEDRIVER_VERSION"

# ChromeDriver'ı indir, kur ve çalıştır
wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip -q chromedriver_linux64.zip
mv chromedriver /usr/local/bin/chromedriver
chmod +x /usr/local/bin/chromedriver

# Test et
echo "ChromeDriver test ediliyor..."
CHROMEDRIVER_INSTALLED_VERSION=$(/usr/local/bin/chromedriver --version)
echo "Kurulu ChromeDriver: $CHROMEDRIVER_INSTALLED_VERSION"

# Çevre değişkenlerinin ayarlanması
echo "Çevre değişkenleri ayarlanıyor..."
echo "export GOOGLE_CHROME_BIN=/usr/bin/google-chrome-stable" >> ~/.profile
echo "export CHROMEDRIVER_PATH=/usr/local/bin/chromedriver" >> ~/.profile

# Bu çalıştırmada da değişkenleri ayarla
export GOOGLE_CHROME_BIN=/usr/bin/google-chrome-stable
export CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# Özet bilgileri göster
echo "========== Kurulum Tamamlandı =========="
echo "Chrome konumu: $GOOGLE_CHROME_BIN"
echo "ChromeDriver konumu: $CHROMEDRIVER_PATH"
echo "Chrome sürümü: $CHROME_VERSION"
echo "ChromeDriver sürümü: $CHROMEDRIVER_INSTALLED_VERSION"

# Geçici dosyaları temizle
rm -rf chromedriver_linux64.zip

echo "Chrome ve ChromeDriver kurulumu başarıyla tamamlandı."
