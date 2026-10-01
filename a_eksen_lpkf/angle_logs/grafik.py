#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grafik.py
angle_log.csv dosyasini (4 sutunlu: t_sec, angle, delta, jump) 
numpy + matplotlib ile analiz edip gosterir.

Kullanim:
    python3 grafik.py
    python3 grafik.py <csv_dosyasi_yolu>
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# ============ AYARLAR ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# grafik.py ve angle_log.csv dosyalari ayni klasordeyse:
DEFAULT_CSV = os.path.join(SCRIPT_DIR, "angle_log.csv")

# Eger angle_log.csv bir alt klasordeyse (opsiyonel kontrol):
if not os.path.exists(DEFAULT_CSV):
    alt_yol = os.path.join(SCRIPT_DIR, "angle_logs", "angle_log.csv")
    if os.path.exists(alt_yol):
        DEFAULT_CSV = alt_yol

JUMP_THRESHOLD = 0.5   # Sicrama esigi (derece)
# =================================

csv_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV

if not os.path.isfile(csv_file):
    print(f"HATA: Dosya bulunamadi: {csv_file}")
    sys.exit(1)

print(f"Okunuyor: {csv_file}")

# --- CSV'yi Oku (4 Sutun: t_sec, angle, delta, jump) ---
try:
    raw_data = np.loadtxt(csv_file, delimiter=",", skiprows=1)
except Exception as e:
    print(f"HATA: CSV okunurken hata olustu: {e}")
    sys.exit(1)

if raw_data.size == 0:
    print("HATA: CSV dosyasi bos.")
    sys.exit(1)

# Tek satir veriyi 2D array yap
if raw_data.ndim == 1:
    raw_data = np.expand_dims(raw_data, axis=0)

# Sutunlari ayir (t_sec, angle, delta, jump)
t_sec = raw_data[:, 0]
angle = raw_data[:, 1]
delta = raw_data[:, 2]
jump  = raw_data[:, 3].astype(int)

total_samples = len(t_sec)
total_jumps = int(np.sum(jump))

print(f"----------------------------------------")
print(f"Toplam Veri Satiri : {total_samples}")
print(f"Toplam Sicrama      : {total_jumps}")
print(f"----------------------------------------")

# ============ GRAFIK ============
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
fig.suptitle(f"Manyetik Enkoder Aci Analizi - {os.path.basename(csv_file)}", fontsize=13, fontweight="bold")

ax1, ax2 = axes[0], axes[1]

# --- 1. GRAFIK: ACI (ANGLE) ---
ax1.plot(t_sec, angle, color="#1f77b4", linewidth=1.2, label="Aci (°)")

# Sıçramaları vurgula (Kırmızı noktalarla)
jump_mask = jump == 1
if np.any(jump_mask):
    ax1.scatter(t_sec[jump_mask], angle[jump_mask],
                color="red", s=45, zorder=5, marker="o",
                edgecolors="black", label=f"Sicrama ({total_jumps})")

ax1.set_ylabel("Aci (°)", fontsize=11)
ax1.grid(True, linestyle="--", alpha=0.5)
ax1.legend(loc="upper right", frameon=True)
ax1.set_title("Toplam X Acisi (udp.toplamXacisi)", fontsize=11, loc="left")

# --- 2. GRAFIK: DELTA (DEGISIM) ---
ax2.plot(t_sec, delta, color="#2ca02c", linewidth=0.8, alpha=0.85, label="Anlik Degisim (Delta)")

# Esik cizgileri
ax2.axhline(y=JUMP_THRESHOLD, color="crimson", linestyle="--", linewidth=1.2, label=f"+{JUMP_THRESHOLD}° Esik")
ax2.axhline(y=-JUMP_THRESHOLD, color="crimson", linestyle="--", linewidth=1.2, label=f"-{JUMP_THRESHOLD}° Esik")

ax2.set_xlabel("Zaman (Saniye)", fontsize=11)
ax2.set_ylabel("Delta (°/ornek)", fontsize=11)
ax2.grid(True, linestyle="--", alpha=0.5)
ax2.legend(loc="upper right", frameon=True)
ax2.set_title("Ornekler Arasi Aci Degisimi (Anlik Fark)", fontsize=11, loc="left")

plt.tight_layout()
plt.show()
