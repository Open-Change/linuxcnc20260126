#!/bin/bash
cd "$(dirname "$0")"
echo "🔹 Dizin: $(pwd)"
sudo mkdir -p /var/run
echo "🔹 FIFO dizini hazır"
sudo ./udp_proxy &
echo "🔹 udp_proxy arka planda başlatıldı"
sleep 1
if pgrep -f udp_proxy >/dev/null; then
    echo "✅ Başarılı: Süreç çalışıyor"
    ls -l /var/run/udp_enc.fifo 2>/dev/null && echo "✅ FIFO dosyası oluşturuldu"
else
    echo "❌ Hata: Süreç başlatılamadı"
fi
