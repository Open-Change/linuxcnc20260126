#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
import signal
import sys
import threading

# ========= EŞİKLER =========
THRESH_REDUCE = 0.4
THRESH_HOLD   = 0.6
THRESH_PAUSE  = 0.912

DEBOUNCE = 0.25
LOOP_DT  = 0.05

# ========= GLOBAL STATE =========
running = True
paused_by_me = False
hold_by_me   = False
last_action  = 0.0

# ========= SIGNAL HANDLERS =========
def sig_exit(sig, frame):
    global running
    running = False
    print("[ferror_guard] SIGTERM/SIGINT/SIGHUP alındı, kapatılıyor...", flush=True)
    sys.exit(0)

signal.signal(signal.SIGINT,  sig_exit)
signal.signal(signal.SIGTERM, sig_exit)
signal.signal(signal.SIGHUP,  sig_exit)

# ========= HAL HELPERS =========
def halcmd(cmd):
    try:
        return subprocess.check_output(
            f"halcmd -s {cmd}",
            shell=True,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except:
        return ""

def getf(pin):
    try:
        return float(halcmd(f"getp {pin}"))
    except:
        return 0.0

def getb(pin):
    return halcmd(f"getp {pin}").lower() in ("1", "true")

def pulse(pin, t=0.03):
    halcmd(f"setp {pin} 1")
    time.sleep(t)
    halcmd(f"setp {pin} 0")

# ========= LINUXCNC WATCHDOG THREAD =========
def linuxcnc_watchdog():
    global running
    TIMEOUT = 5.0
    CHECK_INTERVAL = 1.0
    elapsed = 0.0

    while running and elapsed < TIMEOUT:
        time.sleep(CHECK_INTERVAL)
        elapsed += CHECK_INTERVAL

        # LinuxCNC (ini dosyası ile başlatılmış) çalışıyor mu?
        try:
            result = subprocess.run(
                ["ps", "aux"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )
            found = any(
                "linuxcnc" in line.lower() and ".ini" in line and "grep" not in line
                for line in result.stdout.splitlines()
            )
        except:
            found = False

        if found:
            # LinuxCNC hâlâ yaşıyor → sayaç sıfırla
            elapsed = 0.0

    # Süre doldu, LinuxCNC yok
    if running:
        print("[WATCHDOG] LinuxCNC süreci 5 saniyedir bulunamadı. Güvenli çıkış yapılıyor...", flush=True)
        running = False
        # Ana döngüyü hemen uyandırmak için kısa bekleme
        time.sleep(0.005)
        sys.exit(0)

# ========= PROGRAM BAŞLANGICI =========
print("[ferror_guard] Python f-error koruyucusu başlatıldı.", flush=True)

# Watchdog thread’ini başlat (daemon → program biterse kendiliğinden ölür)
watchdog = threading.Thread(target=linuxcnc_watchdog, daemon=True)
watchdog.start()

try:
    while running:
        # HAL pin değerlerini oku
        fx = abs(getf("joint.0.f-error"))
        fy = abs(getf("joint.1.f-error"))
        ferror = max(fx, fy)

        motion = int(getf("motion.motion-type"))
        is_rapid = (motion == 1)
        is_feed  = (motion == 2)

        now = time.time()

        # ===== PROGRAM PAUSE (acil durum) =====
        if ferror >= THRESH_PAUSE:
            if not getb("halui.program.is-paused"):
                pulse("motion.feed-hold")
                pulse("halui.program.pause")
                paused_by_me = True
                print(f"[PAUSE] ferror={ferror:.3f}", flush=True)
            time.sleep(LOOP_DT)
            continue

        # ===== FEED HOLD =====
        if ferror >= THRESH_HOLD and not hold_by_me:
            pulse("motion.feed-hold")
            hold_by_me = True
            last_action = now
            print(f"[HOLD] ferror={ferror:.3f}", flush=True)
            time.sleep(LOOP_DT)
            continue

        # ===== RESUME =====
        if paused_by_me and ferror < THRESH_REDUCE:
            if getb("halui.program.is-paused"):
                pulse("halui.program.resume")
                print("[RESUME] Program devam ediyor.", flush=True)
            paused_by_me = False
            hold_by_me   = False
            last_action  = now

        # ===== DEBOUNCE SÜRESİ =====
        if (now - last_action) < DEBOUNCE:
            time.sleep(LOOP_DT)
            continue

        # ===== FEED/RAPID ORANI AZALTMA =====
        if ferror >= THRESH_REDUCE and not getb("halui.program.is-paused"):
            if is_feed:
                pulse("halui.feed-override.decrease")
                print(f"[REDUCE] G1 → ferror={ferror:.3f}", flush=True)
            elif is_rapid:
                pulse("halui.rapid-override.decrease")
                print(f"[REDUCE] G0 → ferror={ferror:.3f}", flush=True)
            last_action = now

        time.sleep(LOOP_DT)

except Exception as e:
    print(f"[ferror_guard] Beklenmeyen hata: {e}", flush=True)

print("[ferror_guard] Güvenli çıkış tamamlandı.", flush=True)
sys.exit(0)
