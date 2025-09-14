# scripts/plot_results.py
import csv
import os
from collections import defaultdict
import matplotlib.pyplot as plt

# Arquivos de entrada e saída
BENCH_CSV = "metrics/bench_results.csv"  # resultados do load_test.py
REQS_CSV = "metrics/requests.csv"        # métricas de requisições reais do servidor


# Gera histograma de latência a partir do bench_results.csv

def plot_latency_hist():
    """
    Lê o arquivo bench_results.csv e gera um histograma
    da latência das requisições (em ms).
    Salva a figura em metrics/latency.png.
    """
    if not os.path.exists(BENCH_CSV):
        print(f"[aviso] {BENCH_CSV} não encontrado. Rode scripts/load_test.py antes.")
        return

    lats = []
    # Lê latências do CSV
    with open(BENCH_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                lats.append(float(row["latency_ms"]))
            except:
                pass  # ignora linhas inválidas

    if not lats:
        print("[aviso] sem dados de latência.")
        return

    # Criação do histograma
    plt.figure()
    plt.hist(lats, bins=30)  # 30 intervalos
    plt.xlabel("Latência (ms)")
    plt.ylabel("Contagem")
    plt.title("Histograma de latência (bench_results)")
    plt.tight_layout()

    # Salva gráfico
    out = "metrics/latency.png"
    plt.savefig(out)
    plt.close()
    print(f"[ok] salvo {out}")


# Gera gráfico de throughput (req/s) ao longo do tempo

def plot_throughput_from_requests(window_s=1):
    """
    Lê requests.csv e calcula throughput (req/s) usando buckets
    de tempo configuráveis (por padrão, janela de 1s).
    Salva a figura em metrics/throughput.png.
    """
    if not os.path.exists(REQS_CSV):
        print(f"[aviso] {REQS_CSV} não encontrado. Gere tráfego para criar o CSV.")
        return

    buckets = defaultdict(int)  # timestamp -> contagem de reqs

    # Lê timestamps das requisições e conta por janela
    with open(REQS_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                ts = int(row["timestamp"])
                # Agrupa timestamps em janelas (ex: de 1 em 1 segundo)
                buckets[ts // window_s * window_s] += 1
            except:
                pass  # ignora linhas inválidas

    if not buckets:
        print("[aviso] sem dados em requests.csv.")
        return

    # Ordena os buckets por tempo
    xs = sorted(buckets.keys())
    ys = [buckets[t] / window_s for t in xs]  # taxa req/s

    # Criação do gráfico de throughput
    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xlabel("Timestamp (s)")
    plt.ylabel("Req/s")
    plt.title(f"Throughput aproximado (janela {window_s}s)")
    plt.tight_layout()

    # Salva gráfico
    out = "metrics/throughput.png"
    plt.savefig(out)
    plt.close()
    print(f"[ok] salvo {out}")


# Execução principal

if __name__ == "__main__":
    # Garante que a pasta metrics existe
    os.makedirs("metrics", exist_ok=True)

    # Gera ambos os gráficos
    plot_latency_hist()
    plot_throughput_from_requests(window_s=1)
