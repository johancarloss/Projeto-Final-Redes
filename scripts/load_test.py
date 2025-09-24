# scripts/load_test.py

import argparse
import csv
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def make_request(session, url):
  """
  Realiza uma única requisição HTTP e mede sua latência.
  
  Returns:
    tuple: (latency_mds, status_code, sucess)
  """
  start_time = time.perf_counter()
  try:
    with session.get(url, timeout=10) as response:
      latency = time.perf_counter() - start_time
      return (latency * 1000, response.status_code, True)
  except requests.RequestException as e:
    latency = time.perf_counter() - start_time
    return (latency * 1000, None, False)
  
def run_load_test(url, num_clients, requests_per_client):
  """
  Executa o teste de carga com clientes concorrentes.
  
  Args:
    url (str): A URL a ser testada.
    num_clients (int): O número de clientes concorrentes (threads).
    requests_per_client (int): O número de requisições que cada cliente fará.
    
  Returns:
    list: Uma lista de tuplas com os resultados de cada requisição.
  """
  total_requests = num_clients * requests_per_client
  print(f"Iniciando teste de carga em {url}")
  print(f"Clientes concorrentes: {num_clients}")
  print(f"Requisições por cliente: {requests_per_client}")
  print(f"Total de requisições: {total_requests}\n")

  results = []

  # Usamos um ThreadPoolExecutor para gerenciar os clientes concorrentes
  with ThreadPoolExecutor(max_workers=num_clients) as executor:
    # Usamos uma sessão por cliente para reutilização de conexão (similar ao keep-alive)
    sessions = [requests.Session() for _ in range(num_clients)]

    futures = []
    for i in range(total_requests):
      session = sessions[i % num_clients]
      futures.append(executor.submit(make_request, session, url))

    # Coleta os resultados conforme eles ficam prontos
    for i, future in enumerate(as_completed(futures)):
      results.append(future.result())
      print(f"Progresso: {i + 1}/{total_requests}", end='\r')

  print("\nTeste de carga concluído.\n")
  return results

def save_results_to_csv(results, filepath):
  """
  Salva os resultados do teste de carga em um arquivo CSV.
  """
  print(f"Salvando resultados em '{filepath}'...")
  with open(filepath, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["latency_ms", "status_code", "success"])
    writer.writerows(results)
  print("Resultados salvos com sucesso.\n")

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Script de Teste de Carga para Servidor HTTP.")
  parser.add_argument("path", help="Caminho do recurso a ser testado (ex: /index.html)")
  parser.add_argument("-c", "--clients", type=int, default=10, help="Número de clientes concorrentes.")
  parser.add_argument("-n", "--requests-per-client", type=int, default=10, help="Número de requisições por cliente.")
  parser.add_argument("--port", type=int, default=8080, help="Porta do servidor.")

  args = parser.parse_args()

  target_url = f"http://localhost:{args.port}{args.path}"

  test_results = run_load_test(target_url, args.clients, args.requests_per_client)

  # Garante que o diretório de resultados exista
  import os
  os.makedirs("results", exist_ok=True)

  output_filepath = "results/load_test_results.csv"
  save_results_to_csv(test_results, output_filepath)