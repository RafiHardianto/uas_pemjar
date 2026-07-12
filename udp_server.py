"""
udp_server.py
==============
Server UDP kustom (lanjutan dari tugas Socket Programming) yang membaca
file video, meng-encode tiap frame menjadi JPEG, lalu mengirimkannya
melalui socket UDP ke aplikasi web (app.py bertindak sebagai UDP client).

Cara kerja:
  1. Server ini membuka "control channel" UDP di port 5003, menunggu
     perintah dari app.py, formatnya:
         "START|<path_video>|<client_host>|<client_port>"
  2. Begitu perintah diterima, server membuka thread baru yang membaca
     video pakai OpenCV, meng-encode tiap frame jadi JPEG, lalu
     mengirim byte JPEG tsb via sock.sendto() ke client_host:client_port.
     Inilah "data channel" video streaming yang murni memakai UDP.

Catatan:
  - UDP tidak menjamin urutan/keutuhan paket (connectionless), makanya
    dipakai untuk video streaming: kalau ada frame yang hilang di
    jaringan, streaming tetap lanjut ke frame berikutnya tanpa nunggu
    retransmisi (beda sifat dengan TCP yang dipakai utk upload file,
    yang butuh keandalan/reliability).

Jalankan:
  python udp_server.py

Requirement:
  pip install opencv-python
"""

import socket
import threading
import time
import os

import cv2

CONTROL_HOST = "0.0.0.0"
CONTROL_PORT = 5003

FRAME_WIDTH = 320
FRAME_HEIGHT = 240
JPEG_QUALITY = 50
TARGET_FPS = 20
MAX_UDP_PAYLOAD = 60000  # aman di bawah batas teoritis UDP (65507 bytes)

active_streams = {}
active_lock = threading.Lock()


def stream_video(video_path, client_host, client_port):
    stream_key = (video_path, client_host, client_port)

    with active_lock:
        if active_streams.get(stream_key):
            print(f"[UDP] Stream untuk {stream_key} sudah berjalan, diabaikan.")
            return
        active_streams[stream_key] = True

    if not os.path.exists(video_path):
        print(f"[UDP] File video tidak ditemukan: {video_path}")
        with active_lock:
            active_streams[stream_key] = False
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[UDP] Gagal membuka video: {video_path}")
        with active_lock:
            active_streams[stream_key] = False
        return

    data_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[UDP] Mulai streaming '{video_path}' -> {client_host}:{client_port}")

    delay = 1.0 / TARGET_FPS
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                # video habis -> ulang dari awal (loop), atau bisa di-break
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            ok, encoded = cv2.imencode(
                ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
            )
            if not ok:
                continue

            payload = encoded.tobytes()
            if len(payload) > MAX_UDP_PAYLOAD:
                # frame terlalu besar untuk 1 datagram, lewati saja
                continue

            try:
                data_sock.sendto(payload, (client_host, client_port))
            except Exception as e:
                print(f"[UDP] Gagal mengirim frame: {e}")
                break

            time.sleep(delay)
    finally:
        cap.release()
        data_sock.close()
        with active_lock:
            active_streams[stream_key] = False
        print(f"[UDP] Streaming '{video_path}' dihentikan.")


def main():
    control_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    control_sock.bind((CONTROL_HOST, CONTROL_PORT))
    print(f"[UDP] Control server siap menerima perintah di {CONTROL_HOST}:{CONTROL_PORT}")
    print("[UDP] Menunggu perintah START dari aplikasi web ...")

    try:
        while True:
            data, addr = control_sock.recvfrom(4096)
            message = data.decode(errors="ignore").strip()
            print(f"[UDP] Perintah diterima dari {addr}: {message}")

            if message.startswith("START"):
                try:
                    _, video_path, client_host, client_port = message.split("|")
                    client_port = int(client_port)
                    t = threading.Thread(
                        target=stream_video,
                        args=(video_path, client_host, client_port),
                        daemon=True,
                    )
                    t.start()
                except Exception as e:
                    print(f"[UDP] Format perintah salah: {e}")
    except KeyboardInterrupt:
        print("\n[UDP] Server dihentikan.")
    finally:
        control_sock.close()


if __name__ == "__main__":
    main()
