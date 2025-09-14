# app/server.py  (PATCH=etag-v2)
import argparse
import os
import socket
import threading
import time
import mimetypes
import email.utils
import hashlib
from urllib.parse import urlparse, unquote, parse_qs

from app.cache import MemoryCache
from app.metrics import http_log, csv_log, now_ts
from app import config  # <-- usa o config central

PATCH_ID = "etag-v2"  # <-- marcador de versão para você ver na inicialização
HOST = "0.0.0.0"

def httpdate(ts: float) -> str:
    return email.utils.formatdate(ts, usegmt=True)

def parse_if_none_match(value: str):
    """Normaliza o header If-None-Match em um conjunto de ETags (sem W/ e sem aspas)."""
    items = set()
    for part in value.split(","):
        p = part.strip()
        if p.startswith("W/"):
            p = p[2:].strip()
        if p.startswith('"') and p.endswith('"'):
            p = p[1:-1]
        if p:
            items.add(p)
    return items

def parse_http_date(date_str: str) -> float:
    try:
        return email.utils.parsedate_to_datetime(date_str).timestamp()
    except Exception:
        return 0.0

def guess_mime(path: str) -> str:
    typ, _ = mimetypes.guess_type(path)
    return typ or "application/octet-stream"

def sanitize_path(root: str, url_path: str) -> str | None:
    decoded = unquote(url_path.split("?", 1)[0])
    if decoded.startswith("/"):
        decoded = decoded[1:]
    full = os.path.normpath(os.path.join(root, decoded))
    if not os.path.abspath(full).startswith(os.path.abspath(root)):
        return None
    if os.path.isdir(full):
        idx = os.path.join(full, "index.html")
        return idx if os.path.exists(idx) else None
    return full

def compute_etag(stat) -> str:
    seed = f"{stat.st_size}-{int(stat.st_mtime_ns)}".encode("utf-8")
    return '"' + hashlib.sha1(seed).hexdigest() + '"'

APP_CACHE = MemoryCache(
    max_items=config.LRU_MAX_ITEMS,
    max_bytes=config.LRU_MAX_BYTES,
    default_ttl=config.DEFAULT_TTL_SECONDS
) if config.ENABLE_APP_CACHE else None

def build_headers(status_line: str, headers: dict) -> bytes:
    head = f"HTTP/1.1 {status_line}\r\n"
    for k, v in headers.items():
        head += f"{k}: {v}\r\n"
    head += "\r\n"
    return head.encode("utf-8")

def handle_conn(conn: socket.socket, addr):
    start = time.perf_counter()
    status = "500"
    sent = 0
    cache_hit = "-"
    cond_hit = "-"
    method = "-"
    path = "-"

    try:
        conn.settimeout(5.0)
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if len(data) > 65536:
                break
        if not data:
            return

        header_raw, _, _ = data.partition(b"\r\n\r\n")
        header_txt = header_raw.decode("iso-8859-1", errors="replace")
        lines = header_txt.split("\r\n")
        req = lines[0].split(" ")
        if len(req) < 3:
            resp = build_headers("400 Bad Request", {"Date": httpdate(time.time()), "Connection": "close"})
            conn.sendall(resp)
            status = "400"
            return

        method, target, version = req[0].upper(), req[1], req[2]
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        parsed = urlparse(target)
        path = parsed.path
        qs = parse_qs(parsed.query)
        bypass = qs.get("nocache", ["0"])[0] == "1" or headers.get("x-bypass-cache") == "1"

        if method not in ("GET", "HEAD"):
            body = b"Method Not Allowed"
            resp = build_headers("405 Method Not Allowed", {
                "Date": httpdate(time.time()),
                "Allow": "GET, HEAD",
                "Content-Length": str(len(body)),
                "Connection": "close"
            })
            if method != "HEAD":
                resp += body
            conn.sendall(resp)
            status = "405"
            sent = len(body) if method != "HEAD" else 0
            return

        os.makedirs(config.WWW_ROOT, exist_ok=True)
        file_path = sanitize_path(config.WWW_ROOT, path)
        if not file_path or not os.path.exists(file_path):
            body = b"Not Found"
            resp = build_headers("404 Not Found", {
                "Date": httpdate(time.time()),
                "Content-Length": str(len(body)),
                "Connection": "close"
            })
            if method != "HEAD":
                resp += body
            conn.sendall(resp)
            status = "404"
            sent = len(body) if method != "HEAD" else 0
            return

        st = os.stat(file_path)
        last_mod = httpdate(st.st_mtime)
        etag = compute_etag(st)

        # --------- Conditional GET (ETag / Last-Modified) ----------
        inm = headers.get("if-none-match")
        ims = headers.get("if-modified-since")

        # DEBUG: logar o que chegou para investigação
        if inm:
            http_log(f"DEBUG If-None-Match recv={inm} | server-etag={etag}")

        if inm:
            client_etags = parse_if_none_match(inm)
            server_tag = etag.strip('"')
            if server_tag in client_etags:
                resp = build_headers("304 Not Modified", {
                    "Date": httpdate(time.time()),
                    "ETag": etag,
                    "Last-Modified": last_mod,
                    "Cache-Control": f"public, max-age={config.CACHE_CONTROL_MAX_AGE}",
                    "Connection": "close",
                    "Content-Length": "0",  # força corpo zero
                })
                conn.sendall(resp)
                status = "304"
                cond_hit = "1"
                sent = 0
                return

        if ims:
            try:
                ims_ts = parse_http_date(ims)
                if st.st_mtime <= ims_ts:
                    resp = build_headers("304 Not Modified", {
                        "Date": httpdate(time.time()),
                        "ETag": etag,
                        "Last-Modified": last_mod,
                        "Cache-Control": f"public, max-age={config.CACHE_CONTROL_MAX_AGE}",
                        "Connection": "close",
                        "Content-Length": "0",  # força corpo zero
                    })
                    conn.sendall(resp)
                    status = "304"
                    cond_hit = "1"
                    sent = 0
                    return
            except Exception:
                pass
        # -----------------------------------------------------------

        ctype = guess_mime(file_path)

        # Cache app (apenas GET)
        content = None
        if APP_CACHE and not bypass and method == "GET":
            got = APP_CACHE.get(file_path)
            if got is not None:
                if os.stat(file_path).st_mtime_ns == st.st_mtime_ns:
                    content = got
                    cache_hit = "hit"
                else:
                    cache_hit = "stale"
        if content is None and method == "GET":
            with open(file_path, "rb") as f:
                content = f.read()
            if APP_CACHE and not bypass:
                APP_CACHE.set(file_path, content)
            if cache_hit == "-":
                cache_hit = "miss"
        if bypass:
            cache_hit = "bypass"

        base_headers = {
            "Date": httpdate(time.time()),
            "Content-Type": ctype,
            "ETag": etag,
            "Last-Modified": last_mod,
            "Cache-Control": f"public, max-age={config.CACHE_CONTROL_MAX_AGE}",
            "Connection": "close",
            "Content-Length": str(st.st_size)
        }

        if method == "HEAD":
            resp = build_headers("200 OK", base_headers)
            conn.sendall(resp)
            status = "200"
            sent = 0
        else:
            resp = build_headers("200 OK", base_headers)
            conn.sendall(resp)
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(config.CHUNK_SIZE)
                    if not chunk:
                        break
                    conn.sendall(chunk)
                    sent += len(chunk)
            status = "200"

    except Exception as e:
        body = f"Internal Server Error: {e}\n".encode("utf-8", errors="ignore")
        try:
            resp = build_headers("500 Internal Server Error", {
                "Date": httpdate(time.time()),
                "Content-Length": str(len(body)),
                "Connection": "close"
            })
            resp += body
            conn.sendall(resp)
            status = "500"
            sent = len(body)
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        http_log(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {addr[0]} {method} {path} {status} {elapsed_ms}ms bytes={sent} cache={cache_hit} cond={cond_hit}")
        csv_log({
            "timestamp": now_ts(),
            "client_ip": addr[0],
            "method": method,
            "path": path,
            "status": status,
            "response_time_ms": elapsed_ms,
            "bytes_sent": sent,
            "cache_hit": cache_hit,
            "conditional_hit": cond_hit
        })

def serve(port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, port))
        s.listen(config.MAX_CONNECTION_BACKLOG)
        print(f"PATCH={PATCH_ID} | Servindo {os.path.abspath(config.WWW_ROOT)} em {HOST}:{port} | cache={'on' if APP_CACHE else 'off'}")
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_conn, args=(conn, addr), daemon=True)
            t.start()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=config.PORT)
    args = ap.parse_args()
    os.makedirs("logs", exist_ok=True)
    os.makedirs("metrics", exist_ok=True)
    os.makedirs(config.WWW_ROOT, exist_ok=True)
    serve(args.port)
