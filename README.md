# UAS Pemrograman Jaringan — Web App (TCP Upload + UDP Streaming)

Aplikasi web (Flask) dengan:
- Login + register (password di-hash)
- Verifikasi login via kode OTP yang dikirim ke email (SMTP)
- Upload file lewat **protokol TCP** murni (`tcp_server.py`)
- Streaming video lewat **protokol UDP** murni (`udp_server.py`), ditayangkan di browser sebagai MJPEG

Ada 3 proses yang berjalan bersamaan:

| Proses | File | Port | Fungsi |
|---|---|---|---|
| Web app | `app.py` | 5000 | UI, auth, OTP email, jadi client TCP & UDP |
| TCP server | `tcp_server.py` | 5001 | Terima file upload dari `app.py`, simpan ke `uploads/` |
| UDP server | `udp_server.py` | 5003 (control), kirim ke 5002 | Baca video, encode JPEG per-frame, kirim via UDP ke `app.py` |

## 1. Setup di VM

```bash
# clone repo
git clone <url-repo-kamu>.git
cd <nama-repo>

# python venv
python3 -m venv venv
source venv/bin/activate

# install dependency
pip install -r requirements.txt

# konfigurasi
cp .env.example .env
nano .env   # isi SECRET_KEY, SMTP, dll
```

> `opencv-python` butuh beberapa library sistem di VM Linux minimal (mis. Ubuntu):
> ```bash
> sudo apt update && sudo apt install -y libgl1 libglib2.0-0
> ```

Taruh 1–2 file video pendek (mp4) di folder `videos/` untuk didemokan saat streaming, contoh:

```bash
cp contoh.mp4 videos/
```

## 2. Menjalankan (cara cepat, untuk development/demo)

```bash
chmod +x run_all.sh stop_all.sh
./run_all.sh
```

Ini menjalankan `tcp_server.py`, `udp_server.py`, dan `app.py` sekaligus di background dengan log di folder `logs/`. Buka:

```
http://<ip-vm>:5000
```

Hentikan semua dengan `./stop_all.sh`.

Kalau mau jalankan manual (3 terminal terpisah, sesuai instruksi tugas):

```bash
# terminal 1
python3 tcp_server.py
# terminal 2
python3 udp_server.py
# terminal 3
python3 app.py
```

## 3. Menjalankan sebagai service (production, auto-restart & auto-start saat boot)

Lihat folder `systemd/` — panduan lengkap ada di [DEPLOY_CLOUDFLARE.md](DEPLOY_CLOUDFLARE.md) bagian "Menjalankan sebagai systemd service".

## 4. Setup email OTP (SMTP)

Paling gampang pakai Gmail:
1. Aktifkan 2-Step Verification di akun Google.
2. Buat App Password di https://myaccount.google.com/apppasswords
3. Isi di `.env`:
   ```
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USERNAME=emailkamu@gmail.com
   MAIL_PASSWORD=<app-password-16-digit>
   ```

Kalau `MAIL_USERNAME`/`MAIL_PASSWORD` dikosongkan, kode OTP otomatis muncul di **console log** server (mode demo) — enak buat testing tanpa setup SMTP dulu.

## 5. Deploy dengan Cloudflare

Lihat panduan lengkap: [DEPLOY_CLOUDFLARE.md](DEPLOY_CLOUDFLARE.md)

## 6. Struktur folder

```
.
├── app.py                 # aplikasi web utama (Flask)
├── tcp_server.py           # server TCP untuk upload file
├── udp_server.py           # server UDP untuk streaming video
├── requirements.txt
├── .env.example
├── run_all.sh / stop_all.sh
├── systemd/                # unit file untuk production
├── templates/               # HTML (Jinja2)
├── static/css, static/js
├── uploads/                # hasil upload (tidak ikut git)
└── videos/                 # sumber video untuk streaming (tidak ikut git)
```

## 7. Checklist demo presentasi

- [ ] Jalankan `./run_all.sh` (atau `systemctl start pj-tcp pj-udp pj-web`)
- [ ] Buka domain hasil deploy Cloudflare
- [ ] Registrasi akun baru → tunjukkan email OTP masuk
- [ ] Login → masukkan OTP → masuk dashboard
- [ ] Upload file → tunjukkan file tersimpan (protokol TCP)
- [ ] Buka halaman Streaming → pilih video → tunjukkan video jalan (protokol UDP)
- [ ] Tunjukkan `docs/` / kode `tcp_server.py` & `udp_server.py` sebagai bukti socket asli, bukan library HTTP
