#!/bin/bash
# cnc-ac.sh - Normal Masaüstü Moduna Dönüş

echo "=========================================="
echo "   Normal Masaüstü Moduna Dönülüyor...  "
echo "=========================================="

# 1. Durdurulan Servisleri Yeniden Başlat
echo "[1/6] Arka plan servisleri tekrar başlatılıyor..."
sudo systemctl start \
  ModemManager.service \
  cups.service \
  cups-browsed.service \
  avahi-daemon.service \
  colord.service \
  upower.service \
  cron.service \
  smartmontools.service 2>/dev/null

# 2. I2C Sürücülerini Geri Yükle
echo "[2/6] I2C modülleri geri yükleniyor..."
sudo modprobe i2c_dev 2>/dev/null

# 3. Seri Port Sürücüsünü Geri Yükle
echo "[3/6] Seri port sürücüleri yükleniyor..."
sudo modprobe 8250_serial 2>/dev/null

# 4. Ses Kartı Sürücülerini ve Servislerini Geri Yükle
echo "[4/6] Ses kartı sürücüleri başlatılıyor..."
sudo modprobe snd_hda_intel 2>/dev/null
sudo systemctl start pulseaudio.service pipewire.service pipewire-pulse.service 2>/dev/null

# 5. Wi-Fi ve Kablosuz Ağları Aç
echo "[5/6] Wi-Fi servisleri tekrar açılıyor..."
sudo systemctl start wpa_supplicant.service 2>/dev/null
sudo nmcli radio wifi on 2>/dev/null

# 6. CPU Güç Yönetimini Standart Moda Al
echo "[6/6] İşlemci varsayılan güç moduna çekiliyor..."
if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors ]; then
  if grep -q "powersave" /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors; then
    echo powersave | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1
  else
    echo schedutil | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1
  fi
fi

echo "=========================================="
echo "   Sistem Normal Moda Döndü!             "
echo "=========================================="
