#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
angle_logger.py
udp.toplamXacisi pinini 0.02 sn'de bir okur.
halui.machine.is-on pini SADECE OKUNUR.
  - Power ON  -> angle_log.csv dosyasi sifirlanarak baştan acilir ve kayit baslar.
  - Power OFF -> angle_log.csv dosyasi kapatilir.
"""

import hal
import time
import os

# ============ AYARLAR ============
COMP_NAME      = "angle_logger"
SAMPLE_PERIOD  = 0.02                       # 50 Hz (20 ms)
# Log dosyası tam olarak bu klasörün içinde angle_log.csv adıyla sabitlendi:
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
LOG_DIR        = os.path.join(SCRIPT_DIR, "angle_logs")
LOG_FILE       = os.path.join(LOG_DIR, "angle_log.csv")
JUMP_THRESHOLD = 3.0                        # Sicrama esigi (derece)
# =================================

os.makedirs(LOG_DIR, exist_ok=True)

h = hal.component(COMP_NAME)

# Pinler - SADECE OKUMA (IN) ve durum cikislari (OUT)
h.newpin("angle-in",     hal.HAL_FLOAT, hal.HAL_IN)   # udp.toplamXacisi
h.newpin("power-in",     hal.HAL_BIT,   hal.HAL_IN)   # halui.machine.is-on
h.newpin("logging",      hal.HAL_BIT,   hal.HAL_OUT)  # Kayit durumu
h.newpin("sample-count", hal.HAL_S32,   hal.HAL_OUT)
h.newpin("jump-count",   hal.HAL_S32,   hal.HAL_OUT)
h.newpin("elapsed",      hal.HAL_FLOAT, hal.HAL_OUT)
h.ready()

print(f"[{COMP_NAME}] Hazir. Log dosyasi: {LOG_FILE}", flush=True)

# Durum Degiskenleri
logging_active = False
last_power     = False
log_file       = None
sample_count   = 0
jump_count     = 0
t_start        = 0.0
prev_angle     = None


def open_log():
    """Power ON oldugunda angle_log.csv dosyasini baştan yazmak üzere acar."""
    global log_file, logging_active, sample_count, jump_count, t_start, prev_angle
    
    # "w" modu dosyayi her Power ON durumunda tamamen sifirlar ve yeni baslik yazar.
    log_file = open(LOG_FILE, "w", buffering=1)
    log_file.write("t_sec,angle,delta,jump\n")
    
    logging_active = True
    sample_count = 0
    jump_count = 0
    prev_angle = None
    t_start = time.time()
    
    h["logging"]      = True
    h["sample-count"] = 0
    h["jump-count"]   = 0
    h["elapsed"]      = 0.0
    print(f"[{COMP_NAME}] >>> POWER ON: {LOG_FILE} olusturuldu/sifirlandi.", flush=True)


def close_log():
    """Power OFF oldugunda dosyayi kapatir."""
    global log_file, logging_active
    logging_active = False
    h["logging"] = False
    
    if log_file:
        log_file.close()
        log_file = None
        
    print(f"[{COMP_NAME}] <<< POWER OFF: Dosya kapatildi. Toplam: {sample_count} ornek.", flush=True)


try:
    while True:
        power = bool(h["power-in"])

        # YUKSELEN KENAR: Power ON -> angle_log.csv dosyasini ac
        if power and not last_power:
            if not logging_active:
                open_log()

        # DUSEN KENAR: Power OFF -> Dosyayi kapat
        if not power and last_power:
            if logging_active:
                close_log()

        last_power = power

        # Kayit Yap
        if logging_active and log_file:
            angle = float(h["angle-in"])
            t = time.time() - t_start

            if prev_angle is None:
                delta = 0.0
                is_jump = 0
            else:
                delta = angle - prev_angle
                is_jump = 1 if abs(delta) > JUMP_THRESHOLD else 0
                if is_jump:
                    jump_count += 1
                    h["jump-count"] = jump_count

            log_file.write(f"{t:.4f},{angle:.6f},{delta:.6f},{is_jump}\n")
            
            sample_count += 1
            h["sample-count"] = sample_count
            h["elapsed"]      = t
            prev_angle = angle

        time.sleep(SAMPLE_PERIOD)

except KeyboardInterrupt:
    if log_file:
        log_file.close()
    raise SystemExit
