"""
tcp_server.py
=============
Server TCP kustom (lanjutan dari tugas Socket Programming) yang menerima
file dari aplikasi web (app.py bertindak sebagai TCP client) dan
menyimpannya ke folder uploads/.

Protokol sederhana yang dipakai:
  1. Client connect ke server.
  2. Client mengirim header teks: "<nama_file>|<ukuran_file_bytes>\n"
  3. Client mengirim isi file sebanyak <ukuran_file_bytes> byte.
  4. Server membalas b"OK" jika sukses, b"ERR" jika gagal.

Jalankan:
  python tcp_server.py
"""

import socket
import os

HOST = "0.0.0.0"
PORT = 5001
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")


def recv_all(conn, size):
    data = b""
    while len(data) < size:
        chunk = conn.recv(min(65536, size - len(data)))
        if not chunk:
            break
        data += chunk
    return data


def recv_header(conn):
    header = b""
    while not header.endswith(b"\n"):
        chunk = conn.recv(1)
        if not chunk:
            break
        header += chunk
    return header.decode(errors="ignore").strip()


def handle_client(conn, addr):
    print(f"[TCP] Koneksi masuk dari {addr}")
    try:
        header = recv_header(conn)
        filename, filesize = header.split("|")
        filesize = int(filesize)
        filename = os.path.basename(filename)  # cegah path traversal

        data = recv_all(conn, filesize)
        if len(data) != filesize:
            raise ValueError("Ukuran data tidak sesuai header.")

        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(data)

        print(f"[TCP] Berhasil menyimpan '{filename}' ({filesize} bytes) dari {addr}")
        conn.sendall(b"OK")
    except Exception as e:
        print(f"[TCP] Error saat menerima file dari {addr}: {e}")
        try:
            conn.sendall(b"ERR")
        except Exception:
            pass
    finally:
        conn.close()


def main():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[TCP] Upload server berjalan di {HOST}:{PORT}, folder tujuan: {UPLOAD_DIR}")

    try:
        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)  # sederhana: sekuensial (bisa diganti threading)
    except KeyboardInterrupt:
        print("\n[TCP] Server dihentikan.")
    finally:
        server.close()


if __name__ == "__main__":
    main()
