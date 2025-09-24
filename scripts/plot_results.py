# scripts/plot_results.py

import argparse
import csv
import matplotlib.pyplot as plt
import os

# --- Diretórios de Dados e Saída ---
RESULTS_DIR = "results"
METRICS_FILE = "metrics/requests.csv"
LOAD_TEST_FILE = "results/load_test_results.csv"

# Garante que o diretório de resultados exista
os.makedirs(RESULTS_DIR, exist_ok=True)

def plot_latency_histogram():
  """Gera um histograma de latências a partir do resultado do teste de carga"""
  try:
    latencies = []
    with open(LOAD_TEST_FILE, 'r') as f:
      reader = csv.DictReader(f)
      for row in reader:
        if row['success'].lower() == 'true':
          latencies.append(float(row['latency_ms']))
  except FileNotFoundError:
    print(f"Erro: Arquivo de teste de carga '{LOAD_TEST_FILE}' não encontrado.")
    return
  
  if not latencies:
    print("Nenhum dado de latência disponível para plotar.")
    return
  
  plt.figure(figsize=(10, 6))
  plt.hist(latencies, bins=50, edgecolor='black')
  plt.title("Distribuição das Latências de Requisição")
  plt.xlabel("Latência (ms)")
  plt.ylabel("Frequência")

  avg_latency = sum(latencies) / len(latencies)
  plt.axvline(avg_latency, color='r', linestyle='dashed', linewidth=2, label=f'Média: {avg_latency:.2f} ms')
  plt.legend()

  output_path = os.path.join(RESULTS_DIR, "latency_histogram.png")
  plt.savefig(output_path)
  print(f"Histograma de latências salvo em: {output_path}")
  plt.close()

def plot_cache_hit_ratio():
  """Gera um gráfico de pizza da taxa de acerto do cache a partir das métricas do servidor."""
  try:
    statuses = []
    with open(METRICS_FILE, 'r') as f:
      reader = csv.DictReader(f)
      for row in reader:
        statuses.append(row['cache_status'])
  except FileNotFoundError:
    print(f"Erro: Arquivo de métricas '{METRICS_FILE}' não encontrado.")
    return
  
  if not statuses:
    print("Nenhum dado de status de cache disponível para plotar.")
    return
  
  # Conta as ocorrências de cada status
  cache_hits = statuses.count("HIT") + statuses.count("CONDITIONAL_HIT")
  cache_misses = statuses.count("MISS")

  if cache_hits + cache_misses == 0:
    print("Nenhum dado de cache HIT ou MISS registrado.")
    return
  
  labels = 'Cache Hits', 'Cache Misses'
  sizes = [cache_hits, cache_misses]
  explode = (0.1, 0)  # destaca e fatia "Hits"

  plt.figure(figsize=(8, 8))
  plt.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
          shadow=True, startangle=90)
  plt.axis('equal')  # Garante que o gráfico seja um círculo
  plt.title("Taxa de Acerto do Cache (LRU + Condicional)")

  output_path = os.path.join(RESULTS_DIR, "cache_hit_ratio.png")
  plt.savefig(output_path)
  print(f"Gráfico de taxa de acerto do cache salvo em: {output_path}")
  plt.close()

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Gera gráficos a partir dos resultados de benchmark.")
  parser.add_argument("plot_type", choices=['latency', 'cache'], help="O tipo de gráfico a ser gerado.")
  
  args = parser.parse_args()
  
  if args.plot_type == 'latency':
      plot_latency_histogram()
  elif args.plot_type == 'cache':
      plot_cache_hit_ratio()