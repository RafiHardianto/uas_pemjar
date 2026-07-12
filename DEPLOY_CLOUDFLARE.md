# Panduan Deploy ke Cloudflare

Tujuan tugas: aplikasi web bisa diakses lewat domain yang di-manage DNS-nya oleh Cloudflare
(pakai akun kelas yang disediakan). Ada dua cara umum. **Cara A (Cloudflare Tunnel)
direkomendasikan** karena VM di kelas biasanya tidak punya IP publik sendiri / tidak boleh
buka port ke internet, dan setup-nya jauh lebih simpel + otomatis dapat HTTPS.

> Catatan penting: yang perlu diekspos ke internet **hanya `app.py` (port 5000/web)**.
> `tcp_server.py` (5001) dan `udp_server.py` (5003) cukup jalan di `127.0.0.1` / jaringan
> lokal VM — mereka dipanggil oleh `app.py`, bukan diakses langsung dari browser. Jangan
> buka port 5001/5002/5003 ke publik, tidak perlu dan tidak aman.

---

## Cara A — Cloudflare Tunnel (`cloudflared`) — direkomendasikan

Cloudflare Tunnel membuat koneksi keluar (outbound) dari VM ke jaringan Cloudflare, jadi
tidak perlu IP publik atau buka port firewall sama sekali di VM.

### 1. Install `cloudflared` di VM

```bash
# Ubuntu/Debian
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
cloudflared --version
```

### 2. Login pakai akun Cloudflare kelas

```bash
cloudflared tunnel login
```

Ini akan membuka URL — buka di browser, login dengan akun Cloudflare yang diberikan
dosen/kelas, lalu pilih domain (zone) yang mau dipakai. Setelah selesai, credential
tersimpan otomatis di `~/.cloudflared/`.

### 3. Buat tunnel

```bash
cloudflared tunnel create uas-pemjar
```

Catat `Tunnel ID` yang muncul (juga tersimpan sebagai file `<TUNNEL_ID>.json` di
`~/.cloudflared/`).

### 4. Arahkan subdomain ke tunnel (DNS otomatis dibuat oleh Cloudflare)

```bash
cloudflared tunnel route dns uas-pemjar uas-nama-kamu.domain-kelas.com
```

Ganti `uas-nama-kamu.domain-kelas.com` sesuai domain yang tersedia di akun kelas.
Perintah ini otomatis membuat record CNAME di Cloudflare DNS — tidak perlu isi manual
di dashboard.

### 5. Buat file konfigurasi tunnel

Buat `~/.cloudflared/config.yml`:

```yaml
tunnel: uas-pemjar
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: uas-nama-kamu.domain-kelas.com
    service: http://localhost:5000
  - service: http_status:404
```

### 6. Jalankan tunnel

Untuk tes cepat:

```bash
cloudflared tunnel run uas-pemjar
```

Untuk production (auto-start saat boot, auto-restart):

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared
```

### 7. Jalankan aplikasi web (lihat README.md bagian "Menjalankan")

```bash
./run_all.sh
# atau lewat systemd, lihat bagian di bawah
```

Sekarang buka `https://uas-nama-kamu.domain-kelas.com` — HTTPS sudah otomatis disediakan
Cloudflare, tidak perlu setup sertifikat sendiri.

---

## Cara B — DNS biasa (kalau VM punya IP publik & boleh buka port)

Kalau instruktur memberi VM dengan IP publik dan port 80/443 boleh dibuka:

### 1. Tambah DNS record di dashboard Cloudflare

- Tipe: `A`
- Nama: `uas-nama-kamu` (atau sesuai arahan)
- Konten: IP publik VM
- Proxy status: **Proxied** (awan oranye ON) — supaya lewat Cloudflare & dapat HTTPS gratis

### 2. Pasang reverse proxy (Nginx) di depan Flask

```bash
sudo apt install -y nginx
```

`/etc/nginx/sites-available/uas-pemjar`:

```nginx
server {
    listen 80;
    server_name uas-nama-kamu.domain-kelas.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # penting untuk MJPEG (streaming video) — jangan buffer respons
        proxy_buffering off;
        chunked_transfer_encoding on;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/uas-pemjar /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 3. SSL

Karena DNS di-proxy Cloudflare (awan oranye), set SSL/TLS mode di dashboard Cloudflare
ke **Flexible** (browser↔Cloudflare HTTPS, Cloudflare↔VM HTTP biasa lewat Nginx di atas)
— paling simpel untuk tugas kuliah. Kalau mau end-to-end HTTPS, pakai mode **Full** dan
pasang sertifikat origin Cloudflare (`Origin Server Certificate` dari dashboard) di Nginx.

---

## Menjalankan sebagai systemd service (opsional, biar rapi & auto-restart)

```bash
# taruh project di /opt (atau sesuaikan path di file .service)
sudo mkdir -p /opt/uas-pemjar
sudo cp -r . /opt/uas-pemjar
cd /opt/uas-pemjar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env

# salin unit file, sesuaikan User= dan WorkingDirectory= jika perlu
sudo cp systemd/pj-tcp.service /etc/systemd/system/pj-tcp@$(whoami).service
sudo cp systemd/pj-udp.service /etc/systemd/system/pj-udp@$(whoami).service
sudo cp systemd/pj-web.service /etc/systemd/system/pj-web@$(whoami).service

sudo systemctl daemon-reload
sudo systemctl enable --now pj-tcp@$(whoami) pj-udp@$(whoami) pj-web@$(whoami)

# cek status & log
sudo systemctl status pj-web@$(whoami)
sudo journalctl -u pj-web@$(whoami) -f
```

---

## Troubleshooting singkat

| Gejala | Kemungkinan penyebab |
|---|---|
| Upload gagal "TCP server belum jalan" | `tcp_server.py` belum running / port 5001 dipakai proses lain |
| Video tidak muncul di halaman Stream | `udp_server.py` belum running, atau path video di `videos/` salah, atau firewall lokal blok UDP antar-proses |
| Email OTP tidak masuk | Cek `.env` SMTP, cek folder Spam, atau lihat console log (mode demo tanpa SMTP) |
| Streaming lag / patah-patah | Wajar untuk UDP tanpa jaminan urutan — turunkan `TARGET_FPS` / `JPEG_QUALITY` di `udp_server.py` |
| 502/504 lewat Cloudflare | Pastikan `app.py` benar-benar jalan di port yang dikonfigurasi di `config.yml` / Nginx |
