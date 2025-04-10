#!/bin/bash

# Chrome ve ChromeDriver kurulumu
# Bu script Render ve Heroku gibi servislerde çalışacak şekilde tasarlanmıştır

# Google Chrome kurulumu
apt-get update
apt-get install -y wget gnupg

# Google Chrome repository ekleme
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Chrome kurulumu
apt-get update
apt-get install -y google-chrome-stable

# ChromeDriver kurulumu
CHROME_VERSION=$(google-chrome-stable --version | cut -d ' ' -f 3 | cut -d '.' -f 1)
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip
mv chromedriver /usr/local/bin/chromedriver
chmod +x /usr/local/bin/chromedriver

# Çevre değişkenlerinin ayarlanması
echo "export GOOGLE_CHROME_BIN=/usr/bin/google-chrome-stable" >> ~/.profile
echo "export CHROMEDRIVER_PATH=/usr/local/bin/chromedriver" >> ~/.profile

# Geçici dosyaları temizle
rm -rf chromedriver_linux64.zip

echo "Chrome ve ChromeDriver kurulumu tamamlandı."