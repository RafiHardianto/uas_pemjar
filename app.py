"""
UAS Pemrograman Jaringan - Aplikasi Web
=========================================
Fitur:
- UI berbasis web (Flask + Jinja2)
- Login & Register dengan hashing password
- Verifikasi login via email (kode OTP dikirim lewat SMTP)
- Upload file lewat protokol TCP (dengan bantuan tcp_server.py)
- Streaming video lewat protokol UDP (dengan bantuan udp_server.py)

Cara pakai singkat (lihat README.md untuk detail):
  1) python tcp_server.py      # jalankan di terminal 1
  2) python udp_server.py      # jalankan di terminal 2
  3) python app.py             # jalankan di terminal 3
"""

import os
import json
import socket
import random
import smtplib
import threading
import time
from email.mime.text import MIMEText
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, Response, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------------------------------
# Konfigurasi
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
VIDEO_DIR = os.path.join(BASE_DIR, "videos")

TCP_HOST = os.getenv("TCP_HOST", "127.0.0.1")
TCP_PORT = int(os.getenv("TCP_PORT", 5001))

UDP_DATA_PORT = int(os.getenv("UDP_DATA_PORT", 5002))     # udp_server -> app.py
UDP_CONTROL_HOST = os.getenv("UDP_CONTROL_HOST", "127.0.0.1")
UDP_CONTROL_PORT = int(os.getenv("UDP_CONTROL_PORT", 5003))  # app.py -> udp_server

MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "ganti-secret-key-ini")

# --------------------------------------------------------------------------
# Penyimpanan user sederhana (JSON). Untuk tugas kuliah ini cukup,
# tapi bisa diganti SQLite/PostgreSQL kalau mau.
# --------------------------------------------------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Silakan login terlebih dahulu.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# --------------------------------------------------------------------------
# Kirim email OTP (verifikasi login) via SMTP
# --------------------------------------------------------------------------
def send_otp_email(to_email, otp_code):
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        # Mode demo: kalau kredensial email belum di-set, tampilkan di console
        print(f"[EMAIL-DEMO] Kode OTP untuk {to_email}: {otp_code}")
        return True
    try:
        msg = MIMEText(
            f"Kode verifikasi login Anda adalah: {otp_code}\n\n"
            f"Kode ini berlaku selama 5 menit. Jangan bagikan kode ini ke siapa pun."
        )
        msg["Subject"] = "Kode Verifikasi Login - UAS Pemrograman Jaringan"
        msg["From"] = MAIL_USERNAME
        msg["To"] = to_email

        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_USERNAME, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL] Gagal mengirim email: {e}")
        return False


# --------------------------------------------------------------------------
# Rute: Register / Login / Verify / Logout
# --------------------------------------------------------------------------
@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        users = load_users()
        if username in users:
            flash("Username sudah terdaftar.", "error")
            return redirect(url_for("register"))

        users[username] = {
            "email": email,
            "password_hash": generate_password_hash(password),
        }
        save_users(users)
        flash("Registrasi berhasil, silakan login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        users = load_users()
        user = users.get(username)

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Username atau password salah.", "error")
            return redirect(url_for("login"))

        otp = f"{random.randint(0, 999999):06d}"
        session["pending_user"] = username
        session["otp_code"] = otp
        session["otp_time"] = time.time()

        send_otp_email(user["email"], otp)
        flash(f"Kode verifikasi telah dikirim ke {user['email']}.", "success")
        return redirect(url_for("verify"))

    return render_template("login.html")


@app.route("/verify", methods=["GET", "POST"])
def verify():
    if "pending_user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        code = request.form["otp"].strip()

        if time.time() - session.get("otp_time", 0) > 300:
            flash("Kode verifikasi kadaluarsa, silakan login ulang.", "error")
            session.pop("pending_user", None)
            return redirect(url_for("login"))

        if code == session.get("otp_code"):
            session["logged_in"] = True
            session["username"] = session.pop("pending_user")
            session.pop("otp_code", None)
            flash("Verifikasi berhasil! Selamat datang.", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Kode verifikasi salah.", "error")

    return render_template("verify.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah logout.", "success")
    return redirect(url_for("login"))


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
def _check_tcp_online():
    """Cek cepat apakah tcp_server.py sedang listen di TCP_HOST:TCP_PORT."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.6)
            s.connect((TCP_HOST, TCP_PORT))
        return True
    except Exception:
        return False


@app.route("/api/status")
@login_required
def api_status():
    with frame_lock:
        last_count = frame_count
        last_ts = _last_frame_ts
    udp_receiving = last_ts is not None and (time.time() - last_ts) < 5
    return jsonify({
        "tcp_online": _check_tcp_online(),
        "udp_receiving": udp_receiving,
        "frame_count": last_count,
    })


@app.route("/files/<path:filename>")
@login_required
def download_file(filename):
    filename = secure_filename(filename)
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        abort(404)
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)


@app.route("/dashboard")
@login_required
def dashboard():
    files = sorted(os.listdir(UPLOAD_DIR))
    videos = sorted(
        f for f in os.listdir(VIDEO_DIR) if f.lower().endswith((".mp4", ".avi", ".mov"))
    )
    return render_template("dashboard.html", files=files, videos=videos, active="dashboard")


# --------------------------------------------------------------------------
# Upload file — dikirim ke tcp_server.py lewat socket TCP asli
# --------------------------------------------------------------------------
@app.route("/upload")
@login_required
def upload_page():
    files = sorted(os.listdir(UPLOAD_DIR))
    return render_template("upload.html", files=files, active="upload")


@app.route("/api/upload", methods=["POST"])
@login_required
def api_upload():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"status": "error", "message": "Tidak ada file dipilih."}), 400

    filename = secure_filename(file.filename)
    data = file.read()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(15)
            s.connect((TCP_HOST, TCP_PORT))
            header = f"{filename}|{len(data)}\n".encode()
            s.sendall(header)
            s.sendall(data)
            response = s.recv(1024)
    except ConnectionRefusedError:
        return jsonify({
            "status": "error",
            "message": "TCP server belum jalan. Jalankan 'python tcp_server.py' dahulu."
        }), 503
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    if response == b"OK":
        return jsonify({"status": "success", "filename": filename, "size": len(data)})
    return jsonify({"status": "error", "message": "Server TCP menolak file."}), 500


# --------------------------------------------------------------------------
# Streaming video via UDP
#  udp_server.py membaca file video lalu mengirim tiap frame (JPEG) via UDP
#  ke app.py. app.py menyimpan frame terbaru lalu menayangkannya sebagai
#  MJPEG di browser (karena browser tidak bisa langsung baca socket UDP).
# --------------------------------------------------------------------------
latest_frame = None
frame_lock = threading.Lock()
frame_count = 0
_last_frame_ts = None


def udp_frame_listener():
    """Client UDP yang menerima frame video dari udp_server.py"""
    global latest_frame, frame_count, _last_frame_ts
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_DATA_PORT))
    print(f"[UDP-client] Menunggu frame video di port {UDP_DATA_PORT} ...")
    while True:
        try:
            data, addr = sock.recvfrom(65536)
            with frame_lock:
                latest_frame = data
                frame_count += 1
                _last_frame_ts = time.time()
        except Exception as e:
            print(f"[UDP-client] Error: {e}")


threading.Thread(target=udp_frame_listener, daemon=True).start()


@app.route("/stream")
@login_required
def stream_page():
    videos = sorted(
        f for f in os.listdir(VIDEO_DIR) if f.lower().endswith((".mp4", ".avi", ".mov"))
    )
    return render_template("stream.html", videos=videos, active="stream")


@app.route("/api/start_stream", methods=["POST"])
@login_required
def api_start_stream():
    video_name = request.json.get("video") if request.is_json else request.form.get("video")
    if not video_name:
        return jsonify({"status": "error", "message": "Nama video tidak diberikan."}), 400

    video_path = os.path.join(VIDEO_DIR, secure_filename(video_name))
    if not os.path.exists(video_path):
        return jsonify({"status": "error", "message": "File video tidak ditemukan."}), 404

    message = f"START|{video_path}|127.0.0.1|{UDP_DATA_PORT}"
    try:
        ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ctrl_sock.sendto(message.encode(), (UDP_CONTROL_HOST, UDP_CONTROL_PORT))
        ctrl_sock.close()
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "success", "message": f"Streaming '{video_name}' dimulai via UDP."})


def mjpeg_generator():
    global latest_frame
    last_sent_count = -1
    while True:
        with frame_lock:
            frame = latest_frame
            count = frame_count
        if frame is not None and count != last_sent_count:
            last_sent_count = count
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        time.sleep(0.03)


@app.route("/video_feed")
@login_required
def video_feed():
    return Response(mjpeg_generator(),
                     mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    web_port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=web_port, debug=debug_mode, use_reloader=False)
