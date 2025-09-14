# tests/test_server.py
import threading
import time
import os
import requests

from app.server import serve
from app import config

TEST_PORT = 9090
BASE = f"http://127.0.0.1:{TEST_PORT}"

def start_server_once():
    t = threading.Thread(target=serve, args=(TEST_PORT,), daemon=True)
    t.start()
    # aguarda abrir
    time.sleep(0.5)

def ensure_index():
    os.makedirs(config.WWW_ROOT, exist_ok=True)
    idx = os.path.join(config.WWW_ROOT, "index.html")
    if not os.path.exists(idx):
        with open(idx, "w", encoding="utf-8") as f:
            f.write("<h1>ok</h1>")

def test_get_and_304():
    ensure_index()
    start_server_once()

    r1 = requests.get(f"{BASE}/index.html", timeout=5)
    assert r1.status_code == 200
    assert "ETag" in r1.headers
    etag = r1.headers["ETag"]

    r2 = requests.get(f"{BASE}/index.html", headers={"If-None-Match": etag}, timeout=5)
    assert r2.status_code == 304
