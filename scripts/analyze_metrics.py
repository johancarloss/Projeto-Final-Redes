# tools/parse_metrics.py

import csv
from collections import Counter

METRICS_FILE = "metrics/requests.csv"

def analyze_metrics():
  """
  Lê o arquivo de métricas e imprime um resumo das estatísticas.
  """
  try:
    with open(METRICS_FILE, 'r') as f:
      reader = csv.DictReader(f)
      records = list(reader)
  except FileNotFoundError:
    print(f"Erro: Arqvuivo de métricas '{METRICS_FILE}' não encontrado.")
    return
  except Exception as e:
    print(f"Erro ao ler o arquivo de métricas: {e}")
    return
  
  if not records:
    print("Nenhum registro de métricas encontrado.")
    return
  
  # --- Cálculos ---
  total_requests = len(records)

  status_counts = Counter(r['status'] for r in records)

  # Latências (tempos de resposta)
  latencies = [float(r['response_time_ms']) for r in records]
  avg_latency = sum(latencies) / len(latencies)
  max_latency = max(latencies)

  # Cache
  cache_statuses = Counter(r['cache_status'] for r in records)
  cache_hits = cache_statuses.get("HIT", 0) + cache_statuses.get("CONDITIONAL_HIT", 0)
  cache_misses = cache_statuses.get("MISS", 0)
  total_cache_lookups = cache_hits + cache_misses
  hit_rate = (cache_hits / total_cache_lookups * 100) if total_cache_lookups > 0 else 0

  # Total de dados transferidos
  total_bytes = sum(int(r['bytes_sent']) for r in records)

  # --- Impressão do Resumo ---
  print("--- Análise de Métricas do Servidor ---")
  print(f"\nTotal de Requisições: {total_requests}")

  print("\nLatência (Tempo de Resposta):")
  print(f"  - Média: {avg_latency:.2f} ms")
  print(f"  - Máxima: {max_latency:.2f} ms")

  print("\nStatus das Respostas:")
  for status, count in status_counts.items():
    print(f"  - {status}: {count} requisições")

  print("\nDesempenho do Cache:")
  print(f"  - Hits (LRU + Condicional): {cache_hits}")
  print(f"  - Misses (LRU): {cache_misses}")
  print(f"  - Taxa de Acerto (Hit Rate): {hit_rate:.2f}%")
  
  print("\nTransferência de Dados:")
  print(f"  - Total de Bytes Enviados: {total_bytes / (1024*1024):.2f} MB")
  print("\n------------------------------------")


if __name__ == "__main__":
  analyze_metrics()