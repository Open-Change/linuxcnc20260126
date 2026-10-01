#!/bin/bash
echo "🔹 udp_proxy durduruluyor..."
sudo pkill -f udp_proxy 2>/dev/null
sleep 0.5
sudo rm -f /var/run/udp_enc.fifo 2>/dev/null
echo "✅ udp_proxy tamamen durdu ve temizlendi."
