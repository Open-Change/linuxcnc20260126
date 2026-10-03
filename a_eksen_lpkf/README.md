
### `a_eksen_lpkf/`
LinuxCNC'nin ana konfigürasyon klasörü. İçinde:
- `a_eksen_lpkf.ini` — eksen, motor, hız ayarları
- `*.hal` — HAL bağlantıları (step/dir, encoder, limit, home)
- `macros/` — G-code makrolar (cakı değiştirme, probe, ölçüm vs.)
- `EncoderSpeed/`, `FerrorGuard/` — özel HAL component'leri
- `ferrorHata/` — ileride kullanılmak üzere FerrorGuard yardımcı dosyaları

> **Not:** Klasör adı `a_eksen_lpkf` olsa da şu an **XYZ eksenleri** için
> kullanılıyor. A ekseni ileride eklenecek.

### `linuxcncUDP/`
LinuxCNC ile dış dünya arasında UDP üzerinden veri alışverişi için
component'ler:
- `udp.comp` — aktif HAL component
- `acilstop.comp` — acil durdurma
- `udpcompenet.h` — başlık dosyası

> **Durum:** Arayüz tarafı hazır. **STM32 tarafı henüz yazılmadı** —
> STM32 ile UDP iletişimi sonraki proje adımında eklenecek.

## Gereksinimler

- **LinuxCNC** (2.8 veya üzeri önerilir)
- Linux (Ubuntu / Debian tabanlı)
- Yerel ağda UDP haberleşmesi için: STM32 kartı (henüz entegre edilmedi)

## Nasıl çalıştırılır

```bash
# LinuxCNC'yi başlat
linuxcnc ~/Masaüstü/linuxcnc20260126/a_eksen_lpkf/a_eksen_lpkf.ini