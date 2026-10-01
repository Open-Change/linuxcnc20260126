# -*- coding: utf-8 -*-
"""
AS5600 + Trapez Mil (1 tur = 360° = 6.35 mm)
Ham açı vs Fourier (1-3 harmonik) düzeltilmiş açı analizi
Pandas'sız sürüm: sadece numpy + matplotlib
"""

import numpy as np
import matplotlib.pyplot as plt
import csv

# ----------------------------------------------------------------------
# 0) Sabitler
# ----------------------------------------------------------------------
PITCH_MM     = 6.35                 # 1 tur = 6.35 mm
MM_PER_DEG   = PITCH_MM / 360.0     # 0.0176389 mm/°
DEG_PER_MM   = 360.0 / PITCH_MM     # 56.6929 °/mm
CSV_FILE     = "angle_log (kopya 1).csv"

# ----------------------------------------------------------------------
# 1) CSV oku (pandas yok, saf Python + numpy)
# ----------------------------------------------------------------------
t_list      = []
angle_list  = []
posfb_list  = []
delta_list  = []
jump_list   = []

with open(CSV_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            t_list.append(float(row["t_sec"]))
            angle_list.append(float(row["angle"]))
            posfb_list.append(float(row["position_fb"]))
            delta_list.append(float(row["delta"]))
            jump_list.append(int(float(row["jump"])))
        except (ValueError, KeyError):
            # bozuk satırları atla
            continue

t       = np.array(t_list,     dtype=float)
angle   = np.array(angle_list, dtype=float)
pos_fb  = np.array(posfb_list, dtype=float)
delta   = np.array(delta_list, dtype=float)
jump    = np.array(jump_list,  dtype=int)

print(f"Toplam örnek: {len(t)}")
print(f"Süre: {t[-1]-t[0]:.3f} s")
dt_ort = np.mean(np.diff(t))
print(f"Ortalama örnekleme: {dt_ort*1000:.3f} ms ({1/dt_ort:.2f} Hz)")
print(f"jump=1 sayısı: {np.sum(jump)}")

# ----------------------------------------------------------------------
# 2) Unwrap (360 -> 0 geçişini düzelt)
# ----------------------------------------------------------------------
angle_unwrap = np.unwrap(np.deg2rad(angle)) * 180.0 / np.pi  # derece
pos_from_angle = (angle_unwrap / 360.0) * PITCH_MM           # mm

# Ham hata (referans: position_fb)
hata_ham_deg = angle_unwrap - (pos_fb * DEG_PER_MM)
hata_ham_mm  = pos_from_angle - pos_fb

print(f"\nHam hata (derece): RMS={np.sqrt(np.mean(hata_ham_deg**2)):.4f}°, "
      f"PtP={np.ptp(hata_ham_deg):.4f}°")
print(f"Ham hata (mm)    : RMS={np.sqrt(np.mean(hata_ham_mm**2)):.6f} mm, "
      f"PtP={np.ptp(hata_ham_mm):.6f} mm")

# ----------------------------------------------------------------------
# 3) Fourier harmonik düzeltme (1-3 harmonik)
#    Model: theta_duz = theta_raw - sum_k [ a_k*sin(k*theta) + b_k*cos(k*theta) ]
# ----------------------------------------------------------------------
theta = np.deg2rad(angle_unwrap)
K_MAX = 3

A_mat = [np.ones_like(theta)]
for k in range(1, K_MAX + 1):
    A_mat.append(np.sin(k * theta))
    A_mat.append(np.cos(k * theta))
A_mat = np.column_stack(A_mat)

hedef = angle_unwrap - (pos_fb * DEG_PER_MM)

coef, *_ = np.linalg.lstsq(A_mat, hedef, rcond=None)
a0 = coef[0]

harmonikler = []
for k in range(1, K_MAX + 1):
    a_k = coef[2*k - 1]   # sin
    b_k = coef[2*k]       # cos
    A_k = np.sqrt(a_k**2 + b_k**2)
    phi_k = np.arctan2(b_k, a_k) * 180.0 / np.pi
    harmonikler.append((k, A_k, phi_k, a_k, b_k))

print("\n--- Fourier Harmonik Katsayıları (derece) ---")
print(f"a0 (offset) = {a0:.4f}°")
for k, A_k, phi_k, a_k, b_k in harmonikler:
    print(f"  k={k}: A={A_k:.4f}°, φ={phi_k:+.2f}°, "
          f"a={a_k:+.4f}, b={b_k:+.4f}  "
          f"({A_k*MM_PER_DEG:.6f} mm)")

# ----------------------------------------------------------------------
# 4) Düzeltilmiş açı (derece)
# ----------------------------------------------------------------------
theta_duz = theta.copy()
for k, A_k, phi_k, a_k, b_k in harmonikler:
    theta_duz = theta_duz - (a_k * np.sin(k * theta) + b_k * np.cos(k * theta))

angle_duz = np.rad2deg(theta_duz)
pos_duz   = (angle_duz / 360.0) * PITCH_MM

hata_duz_deg = angle_duz - (pos_fb * DEG_PER_MM)
hata_duz_mm  = pos_duz - pos_fb

print(f"\nDüzeltilmiş hata (derece): RMS={np.sqrt(np.mean(hata_duz_deg**2)):.4f}°, "
      f"PtP={np.ptp(hata_duz_deg):.4f}°")
print(f"Düzeltilmiş hata (mm)    : RMS={np.sqrt(np.mean(hata_duz_mm**2)):.6f} mm, "
      f"PtP={np.ptp(hata_duz_mm):.6f} mm")

# İyileşme yüzdesi
rms_ham = np.sqrt(np.mean(hata_ham_deg**2))
rms_duz = np.sqrt(np.mean(hata_duz_deg**2))
ptp_ham = np.ptp(hata_ham_deg)
ptp_duz = np.ptp(hata_duz_deg)
print(f"\nİyileşme: RMS %{(1-rms_duz/rms_ham)*100:.1f}, "
      f"PtP %{(1-ptp_duz/ptp_ham)*100:.1f}")

# ----------------------------------------------------------------------
# 5) Hareketli bölgeler
# ----------------------------------------------------------------------
hareket = np.abs(delta) > 0.01
if np.any(hareket):
    print(f"\n--- Sadece hareketli bölgeler ({np.sum(hareket)} örnek) ---")
    print(f"Ham   RMS: {np.sqrt(np.mean(hata_ham_deg[hareket]**2)):.4f}°")
    print(f"Düz.  RMS: {np.sqrt(np.mean(hata_duz_deg[hareket]**2)):.4f}°")

# ----------------------------------------------------------------------
# 6) Grafikler
# ----------------------------------------------------------------------
plt.rcParams["figure.figsize"] = (14, 10)
plt.rcParams["font.size"] = 10

# --- Grafik 1: Ham vs Düzeltilmiş açı (tam veri) ---
fig, ax = plt.subplots(2, 1, sharex=True)
ax[0].plot(t, angle,     label="Ham açı (AS5600)",       color="tab:red",  lw=0.8)
ax[0].plot(t, angle_duz, label="Düzeltilmiş açı (1-3H)", color="tab:blue", lw=0.8)
ax[0].set_ylabel("Açı (°)")
ax[0].set_title("Ham vs Fourier Düzeltilmiş Açı (tam veri)")
ax[0].legend(loc="upper right")
ax[0].grid(True, alpha=0.3)

ax[1].plot(t, hata_ham_deg, label="Ham hata",         color="tab:red",  lw=0.8)
ax[1].plot(t, hata_duz_deg, label="Düzeltilmiş hata", color="tab:blue", lw=0.8)
ax[1].set_xlabel("Zaman (s)")
ax[1].set_ylabel("Hata (°)")
ax[1].set_title("Ham vs Düzeltilmiş Hata (derece)")
ax[1].legend(loc="upper right")
ax[1].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("grafik_1_ham_vs_duzeltilmis.png", dpi=150)

# --- Grafik 2: Yakınlaştırma (0-25 s) ---
fig, ax = plt.subplots(2, 1, sharex=True)
mask = t <= 25.0
ax[0].plot(t[mask], angle[mask],     label="Ham açı",         color="tab:red",  lw=1.0)
ax[0].plot(t[mask], angle_duz[mask], label="Düzeltilmiş açı", color="tab:blue", lw=1.0)
ax[0].set_ylabel("Açı (°)")
ax[0].set_title("Yakınlaştırma: 0–25 s")
ax[0].legend()
ax[0].grid(True, alpha=0.3)

ax[1].plot(t[mask], hata_ham_deg[mask], label="Ham hata",         color="tab:red",  lw=1.0)
ax[1].plot(t[mask], hata_duz_deg[mask], label="Düzeltilmiş hata", color="tab:blue", lw=1.0)
ax[1].set_xlabel("Zaman (s)")
ax[1].set_ylabel("Hata (°)")
ax[1].set_title("Yakınlaştırma: 0–25 s (hata)")
ax[1].legend()
ax[1].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("grafik_2_yakinlastirma.png", dpi=150)

# --- Grafik 3: Harmonik genlik spektrumu ---
fig, ax = plt.subplots(figsize=(8, 5))
ks = [h[0] for h in harmonikler]
As = [h[1] for h in harmonikler]
ax.bar(ks, As, color="tab:orange", edgecolor="black")
ax.set_xlabel("Harmonik mertebesi k")
ax.set_ylabel("Genlik A_k (°)")
ax.set_title("Fourier Harmonik Genlikleri (1-3)")
ax.set_xticks(ks)
for k, A_k in zip(ks, As):
    ax.text(k, A_k + 0.02, f"{A_k:.3f}°", ha="center")
ax.grid(True, alpha=0.3, axis="y")
plt.tight_layout()
plt.savefig("grafik_3_harmonikler.png", dpi=150)

# --- Grafik 4: Histogram ---
fig, ax = plt.subplots(figsize=(10, 5))
bins = np.linspace(-1.5, 1.5, 80)
ax.hist(hata_ham_deg, bins=bins, alpha=0.6,
        label=f"Ham (RMS={rms_ham:.3f}°)", color="tab:red")
ax.hist(hata_duz_deg, bins=bins, alpha=0.6,
        label=f"Düzeltilmiş (RMS={rms_duz:.3f}°)", color="tab:blue")
ax.set_xlabel("Hata (°)")
ax.set_ylabel("Örnek sayısı")
ax.set_title("Hata Dağılımı: Ham vs Düzeltilmiş")
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("grafik_4_histogram.png", dpi=150)

# --- Grafik 5: Hata vs Açı ---
fig, ax = plt.subplots(1, 2, figsize=(14, 5))
theta_grid = np.linspace(0, 360, 1000)
theta_grid_rad = np.deg2rad(theta_grid)
hata_model = np.zeros_like(theta_grid)
for k, A_k, phi_k, a_k, b_k in harmonikler:
    hata_model += a_k * np.sin(k * theta_grid_rad) + b_k * np.cos(k * theta_grid_rad)

ax[0].plot(theta_grid, hata_model, color="tab:blue", lw=1.5)
ax[0].set_xlabel("Açı θ (°)")
ax[0].set_ylabel("Model hatası (°)")
ax[0].set_title("Harmonik Hata Modeli (1-3)")
ax[0].grid(True, alpha=0.3)

ax[1].scatter(angle, hata_ham_deg, s=2, alpha=0.3, color="tab:red",  label="Ham hata")
ax[1].scatter(angle, hata_duz_deg, s=2, alpha=0.3, color="tab:blue", label="Düzeltilmiş hata")
ax[1].set_xlabel("Ham açı (°)")
ax[1].set_ylabel("Hata (°)")
ax[1].set_title("Hata vs Açı")
ax[1].legend()
ax[1].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("grafik_5_hata_vs_aci.png", dpi=150)

print("\nGrafikler kaydedildi:")
print("  grafik_1_ham_vs_duzeltilmis.png")
print("  grafik_2_yakinlastirma.png")
print("  grafik_3_harmonikler.png")
print("  grafik_4_histogram.png")
print("  grafik_5_hata_vs_aci.png")

plt.show()
