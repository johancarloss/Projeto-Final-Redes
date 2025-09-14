# scripts/plot_results.py
import csv
import os
from collections import defaultdict
import matplotlib.pyplot as plt

BENCH_CSV = "metrics/bench_results.csv"
REQS_CSV = "metrics/requests.csv"

def plot_latency_hist():
    if not os.path.exists(BENCH_CSV):
        print(f"[aviso] {BENCH_CSV} não encontrado. Rode scripts/load_test.py antes.")
        return
    lats = []
    with open(BENCH_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                lats.append(float(row["latency_ms"]))
            except:
                pass
    if not lats:
        print("[aviso] sem dados de latência.")
        return
    plt.figure()
    plt.hist(lats, bins=30)
    plt.xlabel("Latência (ms)")
    plt.ylabel("Contagem")
    plt.title("Histograma de latência (bench_results)")
    plt.tight_layout()
    out = "metrics/latency.png"
    plt.savefig(out)
    plt.close()
    print(f"[ok] salvo {out}")

def plot_throughput_from_requests(window_s=1):
    if not os.path.exists(REQS_CSV):
        print(f"[aviso] {REQS_CSV} não encontrado. Gere tráfego para criar o CSV.")
        return
    buckets = defaultdict(int)
    with open(REQS_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                ts = int(row["timestamp"])
                buckets[ts // window_s * window_s] += 1
            except:
                pass
    if not buckets:
        print("[aviso] sem dados em requests.csv.")
        return
    xs = sorted(buckets.keys())
    ys = [buckets[t] / window_s for t in xs]  # req/s por janela
    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xlabel("Timestamp (s)")
    plt.ylabel("Req/s")
    plt.title(f"Throughput aproximado (janela {window_s}s)")
    plt.tight_layout()
    out = "metrics/throughput.png"
    plt.savefig(out)
    plt.close()
    print(f"[ok] salvo {out}")

if __name__ == "__main__":
    os.makedirs("metrics", exist_ok=True)
    plot_latency_hist()
    plot_throughput_from_requests(window_s=1)
