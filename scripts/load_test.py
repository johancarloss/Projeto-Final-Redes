# scripts/load_test.py
import argparse
import time
import csv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

def fetch(url: str, headers=None, timeout=10.0):
    t0 = time.perf_counter()
    try:
        r = requests.get(url, headers=headers or {}, timeout=timeout)
        status = r.status_code
        _ = r.content[:1]
    except Exception:
        status = 0
    dt_ms = (time.perf_counter() - t0) * 1000.0
    return dt_ms, status

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080/index.html")
    ap.add_argument("--clients", type=int, default=10)
    ap.add_argument("--requests-per-client", type=int, default=50)
    ap.add_argument("--bypass", action="store_true", help="Força bypass de cache (X-Bypass-Cache: 1)")
    ap.add_argument("--out", default="metrics/bench_results.csv")
    args = ap.parse_args()

    headers = {"X-Bypass-Cache": "1"} if args.bypass else {}
    total = args.clients * args.requests_per_client

    rows = []
    t_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.clients) as ex:
        futs = [ex.submit(fetch, args.url, headers) for _ in range(total)]
        for f in as_completed(futs):
            dt_ms, status = f.result()
            rows.append({"latency_ms": dt_ms, "status": status})
    elapsed = time.perf_counter() - t_start
    rps = total / elapsed if elapsed > 0 else 0.0

    os.makedirs("metrics", exist_ok=True)
    # sobrescreve a cada execução para facilitar comparar runs
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["latency_ms", "status"])
        w.writeheader()
        w.writerows(rows)

    print(f"Concluído: {total} req | clientes={args.clients} | bypass={args.bypass}")
    print(f"Tempo total: {elapsed:.2f}s | Throughput ~ {rps:.2f} req/s")
    print(f"Resultados em: {args.out}")

if __name__ == "__main__":
    main()
