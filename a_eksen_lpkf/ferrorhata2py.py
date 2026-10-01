#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ferrorhata2py.py — Son hali (LinuxCNC 2.9.4 + HAL pinleri)
- Tireli bileşen adı: ferror-guard
- h.ready() sonrası print
- Signal handler ile temiz çıkış
- Tevfik — 30 Aralık 2025
"""

import time
import signal
import sys
import threading
import hal

# ========== SABİT EŞİKLER ==========
THRESH_HOLD   = 0.6
THRESH_PAUSE  = 0.912
THRESH_REDUCE_MIN = 0.2
THRESH_REDUCE_MAX = 0.4
DEBOUNCE = 0.25
LOOP_DT  = 0.05
OVERRIDE_STEP = 5.0

# ========== GLOBAL STATE ==========
running = True
paused_by_me = False
hold_by_me   = False
last_action  = 0.0

# ========== SIGNAL HANDLER ==========
def sig_exit(sig, frame):
    global running
    running = False
    print("[ferror_guard] Kapatılıyor...", flush=True)
    try:
        h.exit()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT,  sig_exit)
signal.signal(signal.SIGTERM, sig_exit)
signal.signal(signal.SIGHUP,  sig_exit)

# ========== LINUXCNC BAĞLANTISI ==========
try:
    from linuxcnc import stat, command
    stat = stat()
    command = command()
    print("[OK] linuxcnc.stat/command hazır.", flush=True)
except Exception as e:
    print(f"[HATA] LinuxCNC bağlantısı: {e}", flush=True)
    sys.exit(1)

# ========== HAL BİLEŞENİ ==========
try:
    h = hal.component("ferror-guard")  # TIRELI AD!
    h.newpin("pause-pulse", hal.HAL_BIT, hal.HAL_OUT)
    h.newpin("resume-pulse", hal.HAL_BIT, hal.HAL_OUT)
    h.newpin("feedhold-pulse", hal.HAL_BIT, hal.HAL_OUT)
    h.ready()  # 🔑 BU SATIR SONRAKİLERDEN ÖNCE, AYNI GİRİNTİDE!
    time.sleep(0.51)  # HAL sisteminin pinleri kaydetmesi için 100 ms bekle
    print("[HAL] ferror-guard bileşeni hazır.", flush=True)
except Exception as e:
    print(f"[HATA] HAL bileşeni: {e}", flush=True)
    sys.exit(1)

# ========== YARDIMCI: PULSE ==========
def pulse(pin_name):
    try:
        h[pin_name] = 1
        time.sleep(0.02)  # 20 ms yeterli
        h[pin_name] = 0
    except Exception as e:
        print(f"[HATA-pulse] {pin_name}: {e}", flush=True)

# ========== WATCHDOG ==========
def linuxcnc_watchdog():
    global running
    while running:
        time.sleep(1.0)
        try:
            stat.poll()
            if stat.ini_filename:
                continue
        except:
            pass
    if running:
        print("[WATCHDOG] LinuxCNC kayboldu.", flush=True)
        running = False

# ========== DİNAMİK THRESH_REDUCE ==========
def get_dynamic_thresh_reduce(ferror):
    if ferror <= 0.0:
        return THRESH_REDUCE_MIN
    elif ferror >= 0.6:
        return THRESH_REDUCE_MAX
    else:
        return THRESH_REDUCE_MIN + (ferror / 3.0)

# ========== ANA DÖNGÜ ==========
print("[ferror_guard] Başlatıldı — HAL pinleri aktif.", flush=True)

watchdog = threading.Thread(target=linuxcnc_watchdog, daemon=True)
watchdog.start()

try:
    while running:
        try:
            stat.poll()
        except:
            time.sleep(LOOP_DT)
            continue

        # ✅ ferror_current okuma (dict formatı)
        fx = fy = 0.0
        try:
            if len(stat.joint) > 0:
                fx = abs(float(stat.joint[0].get('ferror_current', 0.0)))
        except:
            pass
        try:
            if len(stat.joint) > 1:
                fy = abs(float(stat.joint[1].get('ferror_current', 0.0)))
        except:
            pass
        ferror = max(fx, fy)

        THRESH_REDUCE = get_dynamic_thresh_reduce(ferror)
        motion_type = stat.motion_type
        is_feed = (motion_type == 1)

        now = time.time()

        # 🚨 PAUSE
        if ferror >= THRESH_PAUSE:
            if not stat.paused:
                pulse("pause-pulse")
                paused_by_me = True
                print(f"[🚨 PAUSE] ferror={ferror:.4f}", flush=True)
            time.sleep(LOOP_DT)
            continue

        # ⏸️ HOLD
        if ferror >= THRESH_HOLD and not hold_by_me:
            pulse("feedhold-pulse")
            hold_by_me = True
            last_action = now
            print(f"[⏸️ HOLD] ferror={ferror:.4f}", flush=True)
            time.sleep(LOOP_DT)
            continue

        # ▶️ RESUME
        if paused_by_me and ferror < THRESH_REDUCE:
            if stat.paused:
                pulse("resume-pulse")
                print("[▶️ RESUME] Program devam ediyor.", flush=True)
            paused_by_me = False
            hold_by_me = False
            last_action = now

        # ⏳ DEBOUNCE
        if (now - last_action) < DEBOUNCE:
            time.sleep(LOOP_DT)
            continue

        # 📉 AZALT / 📈 ARTIR
        if not stat.paused and is_feed:
            if ferror >= THRESH_REDUCE:
                # Feed override azalt
                try:
                    cur = stat.feedrate * 100.0
                    new = max(10.0, cur - OVERRIDE_STEP)
                    command.feedrate(new / 100.0)
                    print(f"   → Feed: %{cur:.0f} → %{new:.0f}", flush=True)
                    print(f"[📉 REDUCE] G1 — ferror={ferror:.4f}", flush=True)
                    last_action = now
                except Exception as e:
                    print(f"[HATA-feed] {e}", flush=True)

            elif ferror <= (THRESH_REDUCE * 0.6):
                # Feed override artır
                try:
                    cur = stat.feedrate * 100.0
                    new = min(120.0, cur + OVERRIDE_STEP)
                    if new > cur:
                        command.feedrate(new / 100.0)
                        print(f"   → Feed: %{cur:.0f} → %{new:.0f} (↑)", flush=True)
                        print(f"[📈 RECOVER] G1 — ferror={ferror:.4f}", flush=True)
                        last_action = now
                except Exception as e:
                    print(f"[HATA-feed+] {e}", flush=True)

        time.sleep(LOOP_DT)

except KeyboardInterrupt:
    pass
except Exception as e:
    print(f"[KRİTİK] {e}", flush=True)

# Temiz çıkış
try:
    h.exit()
except:
    pass
print("[ferror_guard] Güvenli çıkış tamamlandı.", flush=True)
sys.exit(0)
