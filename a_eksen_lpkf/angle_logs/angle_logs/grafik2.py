#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grafik_gelismis.py
angle_log.csv dosyasını analiz ederek Açı, Delta, Açısal Hız ve Açısal İvme 
grafiklerini zamana bağlı olarak çizer.

Kullanım:
    python3 grafik_gelismis.py
    python3 grafik_gelismis.py <csv_dosyasi_yolu>
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# ============ AYARLAR ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CSV = os.path.join(SCRIPT_DIR, "angle_log.csv")
if not os.path.exists(DEFAULT_CSV):
    alt_yol = os.path.join(SCRIPT_DIR, "angle_logs", "angle_log.csv")
    if os.path.exists(alt_yol):
        DEFAULT_CSV = alt_yol

JUMP_THRESHOLD = 0.5  # Sıçrama eşiği (derece)
# =================================

csv_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV

if not os.path.isfile(csv_file):
    print(f"HATA: Dosya bulunamadı: {csv_file}")
    sys.exit(1)

print(f"Okunuyor: {csv_file}")

# --- CSV Verisini Oku ---
try:
    raw_data = np.loadtxt(csv_file, delimiter=",", skiprows=1)
except Exception as e:
    print(f"HATA: CSV okunurken hata oluştu: {e}")
    sys.exit(1)

if raw_data.size == 0:
    print("HATA: CSV dosyası boş.")
    sys.exit(1)

if raw_data.ndim == 1:
    raw_data = np.expand_dims(raw_data, axis=0)

# Sütunları ayır (t_sec, angle, delta, jump)
t_sec = raw_data[:, 0]
angle = raw_data[:, 1]

if raw_data.shape[1] >= 4:
    delta = raw_data[:, 2]
    jump = raw_data[:, 3].astype(int)
else:
    # CSV'de delta ve jump yoksa otomatik hesapla
    delta = np.zeros_like(angle)
    delta[1:] = np.diff(angle)
    jump = (np.abs(delta) > JUMP_THRESHOLD).astype(int)

total_samples = len(t_sec)
total_jumps = int(np.sum(jump))

# --- Hız ve İvme Hesaplamaları ---
# dt: Örnekler arası zaman farkı (Sıfıra bölünme hatasını önlemek için np.maximum kullanıldı)
dt = np.diff(t_sec)
dt = np.where(dt <= 0, 1e-6, dt)  # Sıfır veya negatif dt durumlarını engelle

# Açısal Hız (deg/s): w = d_angle / dt
velocity = np.zeros_like(angle)
velocity[1:] = np.diff(angle) / dt

# Açısal İvme (deg/s²): a = d_velocity / dt
acceleration = np.zeros_like(velocity)
acceleration[1:] = np.diff(velocity) / dt

print(f"----------------------------------------")
print(f"Toplam Veri Satırı : {total_samples}")
print(f"Toplam Sıçrama      : {total_jumps}")
print(f"Maksimum Hız        : {np.max(np.abs(velocity)):.2f} °/s")
print(f"Maksimum İvme       : {np.max(np.abs(acceleration)):.2f} °/s²")
print(f"----------------------------------------")

# ============ GRAFİK OLUŞTURMA ============
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
fig.suptitle(f"Enkoder Kinematik Analizi - {os.path.basename(csv_file)}", fontsize=14, fontweight="bold")

jump_mask = jump == 1

# --- 1. GRAFİK: AÇI (ANGLE) ---
ax1 = axes[0]
ax1.plot(t_sec, angle, color="#1f77b4", linewidth=1.2, label="Okunan Açı (°)")
if np.any(jump_mask):
    ax1.scatter(t_sec[jump_mask], angle[jump_mask], color="red", s=30, zorder=5, 
                marker="o", edgecolors="black", label=f"Sıçrama ({total_jumps})")
ax1.set_ylabel("Açı (°)", fontsize=10)
ax1.grid(True, linestyle="--", alpha=0.5)
ax1.legend(loc="upper right", frameon=True)
ax1.set_title("AÇI (Pozisyon)", fontsize=10, fontweight="bold", loc="left")

# --- 2. GRAFİK: DELTA (ANLIK DEĞİŞİM) ---
ax2 = axes[1]
ax2.plot(t_sec, delta, color="#2ca02c", linewidth=0.9, alpha=0.85, label="Anlık Değişim (Delta)")
ax2.axhline(y=JUMP_THRESHOLD, color="crimson", linestyle="--", linewidth=1, label=f"Eşik (±{JUMP_THRESHOLD}°)")
ax2.axhline(y=-JUMP_THRESHOLD, color="crimson", linestyle="--", linewidth=1)
ax2.set_ylabel("Delta (°/örnek)", fontsize=10)
ax2.grid(True, linestyle="--", alpha=0.5)
ax2.legend(loc="upper right", frameon=True)
ax2.set_title("ANLIK AÇI FARKILILIĞI (Delta)", fontsize=10, fontweight="bold", loc="left")

# --- 3. GRAFİK: AÇISAL HIZ (VELOCITY) ---
ax3 = axes[2]
ax3.plot(t_sec, velocity, color="#ff7f0e", linewidth=1.0, label="Açısal Hız (°/s)")
if np.any(jump_mask):
    ax3.scatter(t_sec[jump_mask], velocity[jump_mask], color="red", s=25, zorder=5)
ax3.set_ylabel("Hız (°/s)", fontsize=10)
ax3.grid(True, linestyle="--", alpha=0.5)
ax3.legend(loc="upper right", frameon=True)
ax3.set_title("AÇISAL HIZ ($\omega = d\\theta/dt$)", fontsize=10, fontweight="bold", loc="left")

# --- 4. GRAFİK: AÇISAL İVME (ACCELERATION) ---
ax4 = axes[3]
ax4.plot(t_sec, acceleration, color="#9467bd", linewidth=0.8, alpha=0.8, label="Açısal İvme (°/s²)")
ax4.set_xlabel("Zaman (Saniye)", fontsize=11)
ax4.set_ylabel("İvme (°/s²)", fontsize=10)
ax4.grid(True, linestyle="--", alpha=0.5)
ax4.legend(loc="upper right", frameon=True)
ax4.set_title("AÇISAL İVME ($\\alpha = dw/dt$)", fontsize=10, fontweight="bold", loc="left")

plt.tight_layout()
plt.show()
