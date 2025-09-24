# tests/test_metrics.py

import pytest
import os
import csv
import threading
from app.metrics import MetricsLogger

TEST_CSV_FILE = "test_metrics/requests_test.csv"

@pytest.fixture
def metrics_logger():
  """Fornece uma instância limpa do logger e limpa o arquivo após o teste."""
  # Garante que o diretório existe
  os.makedirs(os.path.dirname(TEST_CSV_FILE), exist_ok=True)
  
  # Limpa o arquivo antes do teste
  if os.path.exists(TEST_CSV_FILE):
    os.remove(TEST_CSV_FILE)

  logger = MetricsLogger(TEST_CSV_FILE)
  yield logger

  # Limpa o arquivo após o teste
  if os.path.exists(TEST_CSV_FILE):
    os.remove(TEST_CSV_FILE)

def test_csv_creation_and_header(metrics_logger):
  """Verifica se o arquivo CSV é criado com o cabeçalho correto."""
  assert os.path.exists(TEST_CSV_FILE)
  with open(TEST_CSV_FILE, 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    assert header == [
      "timestamp", "client_ip", "method", "path", "status",
      "response_time_ms", "bytes_sent", "cache_status"
    ]

def test_concurrent_logging(metrics_logger):
  """
  Testa se o logger escreve no CSV de forma segura sob carga de múltiplas threads.
  """
  num_threads = 20
  logs_per_thread = 50
  total_logs = num_threads * logs_per_thread

  def worker(thread_id):
    for i in range(logs_per_thread):
      metrics_logger.log_request(
        client_ip=f"192.168.1.{thread_id}",
        method="GET",
        path=f"/path/{i}",
        status=200,
        response_time_ms=10.5,
        bytes_sent=1024,
        cache_status="HIT"
      )

  threads = []
  for i in range(num_threads):
    thread = threading.Thread(target=worker, args=(i,))
    threads.append(thread)
    thread.start()

  for thread in threads:
    thread.join()

  # Verifica a integridade do arquivo CSV
  with open(TEST_CSV_FILE, 'r') as f:
    reader = csv.reader(f)
    # Pula o cabeçalho
    next(reader)
    # Conta o número de linhas
    lines = list(reader)

    # 1. Verifica se o número de linhas é o esperado
    assert len(lines) == total_logs, "Número incorreto de linhas no CSV."

    # 2. Verifica se cada linha tem o número correto de colunas
    for i, row in enumerate(lines):
      assert len(row) == 8, f"Linha {i+1} tem número incorreto: {row}."