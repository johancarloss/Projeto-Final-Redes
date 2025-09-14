# scripts/load_test.py
import argparse
import time
import csv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


# Função para realizar uma requisição HTTP e medir latência

def fetch(url: str, headers=None, timeout=10.0):
    """
    Faz GET para uma URL e retorna:
    - dt_ms: tempo de resposta em milissegundos
    - status: código HTTP (0 em caso de erro)
    """
    t0 = time.perf_counter()  # tempo inicial
    try:
        # Realiza requisição GET
        r = requests.get(url, headers=headers or {}, timeout=timeout)
        status = r.status_code
        # Lê o primeiro byte do conteúdo apenas (evita carregar arquivos grandes desnecessariamente)
        _ = r.content[:1]
    except Exception:
        status = 0  # erro de conexão ou timeout
    dt_ms = (time.perf_counter() - t0) * 1000.0  # tempo em milissegundos
    return dt_ms, status


# Função principal

def main():
    """
    Realiza um teste de carga para uma URL usando múltiplos clientes concorrentes.
    - Permite configurar número de clientes, requisições por cliente e bypass de cache
    - Salva resultados em CSV
    """
    
    # Parsing de argumentos da linha de comando
    
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080/index.html")
    ap.add_argument("--clients", type=int, default=10)
    ap.add_argument("--requests-per-client", type=int, default=50)
    ap.add_argument("--bypass", action="store_true", help="Força bypass de cache (X-Bypass-Cache: 1)")
    ap.add_argument("--out", default="metrics/bench_results.csv")
    args = ap.parse_args()

    # Define headers caso queira forçar bypass de cache
    headers = {"X-Bypass-Cache": "1"} if args.bypass else {}
    total = args.clients * args.requests_per_client  # total de requisições a serem feitas

    rows = []  # lista de resultados
    t_start = time.perf_counter()  # tempo de início

    
    # Executor de threads para requisições concorrentes
    
    with ThreadPoolExecutor(max_workers=args.clients) as ex:
        # Cria futures para cada requisição
        futs = [ex.submit(fetch, args.url, headers) for _ in range(total)]
        # Processa resultados conforme forem completando
        for f in as_completed(futs):
            dt_ms, status = f.result()
            rows.append({"latency_ms": dt_ms, "status": status})

    # Calcula tempo total e throughput aproximado
    elapsed = time.perf_counter() - t_start
    rps = total / elapsed if elapsed > 0 else 0.0

    
    # Salva resultados em CSV
    
    os.makedirs("metrics", exist_ok=True)  # cria pasta se não existir
    # Sobrescreve a cada execução
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["latency_ms", "status"])
        w.writeheader()
        w.writerows(rows)

    
    # Print resumo do teste
    
    print(f"Concluído: {total} req | clientes={args.clients} | bypass={args.bypass}")
    print(f"Tempo total: {elapsed:.2f}s | Throughput ~ {rps:.2f} req/s")
    print(f"Resultados em: {args.out}")


# Execução direta do script

if __name__ == "__main__":
    main()
