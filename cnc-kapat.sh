#!/bin/bash
# cnc-kapat.sh - LinuxCNC Tam İzole Modu (I2C, Ses ve Seri Port Kapalı)

echo "=========================================="
echo "   LinuxCNC Modu Aktif Ediliyor...       "
echo "=========================================="

# 1. Wi-Fi ve Kablosuz Ağları Kapat
echo "[1/7] Wi-Fi kapatılıyor..."
sudo nmcli radio wifi off 2>/dev/null
sudo systemctl stop wpa_supplicant.service 2>/dev/null

# 2. I2C (Sensör/SMBus/DDC) Modüllerini Kaldır
echo "[2/7] I2C donanım modülleri pasifleştiriliyor..."
sudo modprobe -r i2c_dev i2c_algo_bit i2c_piix4 i2c_designware_platform i2c_designware_core 2>/dev/null

# 3. Ses Kartı Sürücülerini ve Servislerini Durdur
echo "[3/7] Ses kartı (ALSA/Audio) pasifleştiriliyor..."
sudo systemctl stop pulseaudio.service pipewire.service pipewire-pulse.service 2>/dev/null
sudo modprobe -r snd_hda_intel snd_pcm 2>/dev/null

# 4. Seri Port (UART/COM) Sürücüsünü Boşa Çıkar
echo "[4/7] Seri port (8250/UART) modülü kaldırılıyor..."
sudo modprobe -r 8250_serial 8250 2>/dev/null

# 5. Latens Oluşturan Arka Plan Servislerini Durdur
echo "[5/7] Arka plan servisleri durduruluyor..."
sudo systemctl stop \
  ModemManager.service \
  cups.service \
  cups-browsed.service \
  avahi-daemon.service \
  colord.service \
  upower.service \
  cron.service \
  smartmontools.service 2>/dev/null

# 6. CPU Güç Yönetimini 'Performance' Moduna Al
echo "[6/7] İşlemci Performance moduna alınıyor..."
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1

# 7. RAM Önbelleğini Temizle
echo "[7/7] RAM Önbelleği temizleniyor..."
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

echo "=========================================="
echo "   Sistem LinuxCNC İçin Hazır!           "
echo "=========================================="
