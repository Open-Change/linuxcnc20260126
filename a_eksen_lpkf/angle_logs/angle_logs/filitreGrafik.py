#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Encoder log analiz ve observer simulasyonu (pandas'siz).
Kullanim:
    python3 filitreGrafik.py angle_log.csv
"""

import sys
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


# =============================================================================
# 1) CSV OKUMA (COK SAGLAM)
# =============================================================================
def load_log(path):
    """
    Cok saglam CSV okuyucu.
    - Baslik satiri olsun ya da olmasin
    - Sayisal olmayan satirlari atla
    - Coklu baslik (birlestirilmis log) varsa hepsini atla
    - Eksik/ bos degerleri 0 kabul et
    - Kolon isimleri esnek (t/time, pos/position/angle, d/dv)
    """
    alias = {'t': 't_sec', 'time': 't_sec', 'timestamp': 't_sec',
             'pos': 'angle', 'position': 'angle', 'theta': 'angle',
             'd': 'delta', 'dv': 'delta', 'diff': 'delta'}

    def to_float(s):
        if s is None:
            return None
        s = s.strip()
        if s == '' or s.lower() in ('nan', 'none', 'null'):
            return None
        try:
            return float(s)
        except (ValueError, TypeError):
            return None

    t_list = []
    angle_list = []
    delta_list = []
    jump_list = []

    with open(path, 'r', newline='') as f:
        reader = csv.reader(f)
        header = None
        seen_header = False

        for row in reader:
            if not row:
                continue
            row = [c.strip() for c in row]
            if all(c == '' for c in row):
                continue

            # Baslik mi?
            first = to_float(row[0])
            if first is None:
                if not seen_header:
                    header = [c.lower() for c in row]
                    seen_header = True
                # Ikinci ve sonraki basliklari atla
                continue

            # Kolon haritasi
            if header is not None:
                col = {}
                for i, name in enumerate(header):
                    real = alias.get(name, name)
                    col[real] = i
            else:
                col = {'t_sec': 0, 'angle': 1, 'delta': 2, 'jump': 3}

            def get_val(real_name, default=0.0):
                idx = col.get(real_name)
                if idx is None or idx >= len(row):
                    return default
                v = to_float(row[idx])
                return default if v is None else v

            t_list.append(get_val('t_sec', 0.0))
            angle_list.append(get_val('angle', 0.0))
            delta_list.append(get_val('delta', 0.0))
            jump_list.append(int(get_val('jump', 0.0)))

    if not t_list:
        raise ValueError(f"Dosyada gecerli veri satiri bulunamadi: {path}")

    t     = np.array(t_list)
    angle = np.array(angle_list)
    delta = np.array(delta_list)
    jump  = np.array(jump_list, dtype=int)

    idx = np.argsort(t)
    return {
        't_sec': t[idx],
        'angle': angle[idx],
        'delta': delta[idx],
        'jump':  jump[idx],
    }


# =============================================================================
# 2) OBSERVER + FILTRE HATTI
# =============================================================================
def run_observer(t, x_meas,
                 alpha=0.20,
                 beta=0.015,
                 vel_alpha=0.30,
                 jump_thresh=0.20,
                 quant_step=0.002787,
                 deadband_mult=2.0):
    """
    LinuxCNC bileseninin (encoder_speed) Python karsiligi.
    Outlier reddi -> alpha-beta observer -> deadband -> EMA.
    """
    n = len(t)

    pos_out = np.zeros(n)
    vel_raw = np.zeros(n)
    vel_obs = np.zeros(n)
    vel_out = np.zeros(n)
    innov   = np.zeros(n)
    jump    = np.zeros(n, dtype=int)

    obs_x     = x_meas[0]
    obs_v     = 0.0
    vel_filt  = 0.0
    prev_meas = x_meas[0]
    prev_t    = t[0]
    have_meas = False

    for k in range(n):
        if k == 0:
            pos_out[k] = obs_x
            continue

        dt = t[k] - t[k-1]
        if dt <= 0:
            pos_out[k] = obs_x
            continue

        t_now = t[k]

        # --- PREDICT ---
        obs_x += obs_v * dt

        # --- Outlier reddi ---
        dt_meas = t_now - prev_t
        if dt_meas <= 0:
            dt_meas = dt

        expected = prev_meas + obs_v * dt_meas
        diff = x_meas[k] - expected

        if abs(diff) > jump_thresh:
            jump[k] = 1
        else:
            # --- CORRECT ---
            r = x_meas[k] - obs_x
            innov[k] = r
            obs_x += alpha * r
            obs_v += (beta / dt_meas) * r

            if have_meas:
                vel_raw[k] = (x_meas[k] - prev_meas) / dt_meas

            prev_meas = x_meas[k]
            prev_t    = t_now
            have_meas = True

        # --- Deadband ---
        v_dead = (quant_step * deadband_mult) / dt
        v_use = obs_v
        if abs(v_use) < v_dead:
            v_use = 0.0
        vel_obs[k] = v_use

        # --- EMA ---
        if vel_alpha >= 1.0:
            vel_filt = v_use
        else:
            vel_filt = vel_alpha * v_use + (1.0 - vel_alpha) * vel_filt
        vel_out[k] = vel_filt

        pos_out[k] = obs_x

    return {
        'pos_clean':  pos_out,
        'vel_raw':    vel_raw,
        'vel_obs':    vel_obs,
        'vel_out':    vel_out,
        'innovation': innov,
        'jump':       jump,
    }


# =============================================================================
# 3) GRAFIK
# =============================================================================
def plot_analysis(t, x_raw, obs, jump_raw=None, save_path=None):
    fig = plt.figure(figsize=(14, 11))
    gs = GridSpec(4, 2, figure=fig, hspace=0.42, wspace=0.25)

    # ---- (1) Ham pozisyon ----
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(t, x_raw, color='steelblue', lw=0.8, label='Ham angle (UDP)')
    if jump_raw is not None and np.any(jump_raw):
        jmask = jump_raw.astype(bool)
        ax1.scatter(t[jmask], x_raw[jmask], color='red', s=20,
                    zorder=5, label='jump=1 (log)')
    if np.any(obs['jump']):
        omask = obs['jump'].astype(bool)
        ax1.scatter(t[omask], x_raw[omask], color='orange', s=30,
                    marker='x', zorder=6, label='jump=1 (observer)')
    ax1.set_ylabel('Pozisyon')
    ax1.set_title('1) Ham UDP Verisi — 20 ms ZOH ve sicramalar')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left', fontsize=8)

    # ---- (2) Zoom 0-0.6 s ----
    ax2 = fig.add_subplot(gs[1, 0])
    z = (t >= 0.0) & (t <= 0.6)
    if np.any(z):
        ax2.step(t[z], x_raw[z], where='post', color='steelblue', lw=1.0)
    ax2.set_title('2) Zoom 0-0.6 s — 20 ms ZOH (merdiven)')
    ax2.set_xlabel('t [s]')
    ax2.set_ylabel('Pozisyon')
    ax2.grid(True, alpha=0.3)

    # ---- (3) Zoom 1.2-2.0 s ----
    ax3 = fig.add_subplot(gs[1, 1])
    z = (t >= 1.2) & (t <= 2.0)
    if np.any(z):
        ax3.step(t[z], x_raw[z], where='post',
                 color='steelblue', lw=1.0, label='Ham')
        ax3.plot(t[z], obs['pos_clean'][z],
                 color='darkorange', lw=1.2, label='Observer cikis')
    ax3.set_title('3) Zoom 1.2-2.0 s — Hareket + observer')
    ax3.set_xlabel('t [s]')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=8)

    # ---- (4) Ham turev vs Observer hizi ----
    ax4 = fig.add_subplot(gs[2, :])
    ax4.plot(t, obs['vel_raw'], color='red', lw=0.7, alpha=0.6,
             label='Ham turev (dpos/dt) — gurultulu')
    ax4.plot(t, obs['vel_obs'], color='green', lw=1.0, alpha=0.8,
             label='Observer hizi (deadband sonrasi)')
    ax4.plot(t, obs['vel_out'], color='black', lw=1.2,
             label='EMA filtrelenmis cikis')
    ax4.set_title('4) Hiz Tahmini — Ham turev vs Observer')
    ax4.set_xlabel('t [s]')
    ax4.set_ylabel('Hiz [birim/s]')
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc='upper left', fontsize=8)
    ax4.set_ylim(-8, 8)

    # ---- (5) Innovation ----
    ax5 = fig.add_subplot(gs[3, 0])
    ax5.plot(t, obs['innovation'], color='purple', lw=0.6)
    ax5.axhline(0, color='gray', lw=0.5)
    ax5.set_title('5) Innovation (r = x_meas - x_hat)')
    ax5.set_xlabel('t [s]')
    ax5.set_ylabel('Yenilik')
    ax5.grid(True, alpha=0.3)

    # ---- (6) dpos histogrami (durusa yakin) ----
    ax6 = fig.add_subplot(gs[3, 1])
    z = (t >= 9.0) & (t <= 10.5)
    if np.sum(z) > 2:
        d = np.diff(x_raw[z])
        d = d[np.abs(d) > 1e-9]
        if len(d) > 0:
            ax6.hist(d, bins=40, color='teal', alpha=0.75)
            ax6.set_title('6) dpos histogrami (durusa yakin) — kuantizasyon')
            ax6.set_xlabel('dpos [birim]')
            ax6.set_ylabel('Sayi')
            ax6.grid(True, alpha=0.3)

    fig.suptitle('Encoder Log Analizi — UDP 20 ms Gecikme + Observer',
                 fontsize=13, y=0.995)

    if save_path:
        plt.savefig(save_path, dpi=120, bbox_inches='tight')
        print(f"[+] Grafik kaydedildi: {save_path}")

    plt.show()


# =============================================================================
# 4) SAYISAL OZET
# =============================================================================
def print_summary(t, x_raw, obs):
    print("=" * 70)
    print("OZET ISTATISTIKLER")
    print("=" * 70)

    dt = np.diff(t)

    print(f"Toplam sure         : {t[-1]:.3f} s")
    print(f"Ornek sayisi        : {len(t)}")
    print(f"Ort. ornekleme      : {dt.mean()*1000:.3f} ms")
    print(f"Medyan ornekleme    : {np.median(dt)*1000:.3f} ms")
    print(f"Max ornekleme       : {dt.max()*1000:.3f} ms  (ZOH suresi)")

    d = np.diff(x_raw)
    d_nonzero = d[np.abs(d) > 1e-9]
    if len(d_nonzero) > 0:
        pos_step = d_nonzero[d_nonzero > 0]
        if len(pos_step) > 0:
            lsb = np.percentile(pos_step, 5)
            print(f"Tahmini 1 LSB       : {lsb:.6f} birim")

    vr = obs['vel_raw']
    vr_nz = vr[np.abs(vr) > 1e-9]
    if len(vr_nz) > 0:
        print(f"Ham hiz std         : {vr_nz.std():.3f} birim/s")
        print(f"Ham hiz max |v|     : {np.abs(vr_nz).max():.3f} birim/s")

    vo = obs['vel_out']
    print(f"Observer hiz std    : {vo.std():.3f} birim/s")
    print(f"Observer hiz max|v| : {np.abs(vo).max():.3f} birim/s")

    print(f"Tespit edilen jump  : {int(obs['jump'].sum())}")

    if len(vr_nz) > 0 and vr_nz.std() > 0:
        ratio = vo.std() / vr_nz.std()
        print(f"Gurultu azaltma     : {ratio*100:.1f}%  "
              f"(1.0'a yakin = hic filtre yok)")

    print("=" * 70)


# =============================================================================
# 5) FILTRELENMIS CSV KAYDET
# =============================================================================
def save_filtered_csv(path, t, x_raw, obs):
    out_path = path.replace(".csv", "_filtered.csv")
    header = ("t_sec,angle,pos_clean,vel_raw,vel_obs,vel_out,"
              "innovation,jump")
    data = np.column_stack([
        t,
        x_raw,
        obs['pos_clean'],
        obs['vel_raw'],
        obs['vel_obs'],
        obs['vel_out'],
        obs['innovation'],
        obs['jump'].astype(float),
    ])
    np.savetxt(out_path, data, delimiter=',', header=header,
               comments='', fmt='%.6f')
    print(f"[+] Filtrelenmis veri: {out_path}")


# =============================================================================
# 6) ANA
# =============================================================================
def main():
    if len(sys.argv) < 2:
        path = "angle_log.csv"
    else:
        path = sys.argv[1]

    print(f"[+] Yukleniyor: {path}")
    data = load_log(path)
    t = data['t_sec']
    x_raw = data['angle']
    jump_log = data.get('jump', None)
    print(f"    {len(t)} satir okundu")

    print("[+] Observer calistiriliyor...")
    obs = run_observer(
        t, x_raw,
        alpha=0.20,
        beta=0.015,
        vel_alpha=0.30,
        jump_thresh=0.20,
        quant_step=0.002787,
        deadband_mult=2.0,
    )

    print_summary(t, x_raw, obs)
    save_filtered_csv(path, t, x_raw, obs)
    plot_analysis(t, x_raw, obs, jump_raw=jump_log,
                  save_path=path.replace(".csv", "_analysis.png"))


if __name__ == "__main__":
    main()
