# app/metrics.py

import csv
import os
import threading
from datetime import datetime, UTC

from . import config

class MetricsLogger:
  """
  Uma classe thread-safe para registrar métricas de requisições HTTP em um arquivo CSV.
  """

  def __init__(self, filepath):
    """
    Inicializa o logger de métricas.
    
    Args:
      filepath (str): Caminho do arquivo CSV onde as métricas serão armazenadas.
    """
    self.filepath = filepath
    self._lock = threading.Lock()
    self._header = [
      "timestamp", "client_ip", "method", "path", "status",
      "response_time_ms", "bytes_sent", "cache_status"
    ]

    # Garante que o diretório do arquivo existam com o cabeçalho correto
    self._initialize_file()

  def _initialize_file(self):
    """Cria o diretório e o arquivo CSV com o cabeçalho, se necessário."""
    with self._lock:
      # Garante que o diretório existe
      os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

      # Escreve o cabeçalho se o arquivo não existir
      if not os.path.exists(self.filepath):
        with open(self.filepath, 'w', newline='') as f:
          writer = csv.writer(f)
          writer.writerow(self._header)

  def log_request(self, client_ip, method, path, status, response_time_ms, bytes_sent, cache_status):
    """
    Registra uma métrica de requisição HTTP no arquivo CSV.

    Todos os argumentos devem ser fornecidos para garantir a integridade dos dados.
    
    Args:
      client_ip (str): Endereço IP do cliente.
      method (str): Método HTTP (GET, POST, etc.).
      path (str): Caminho da requisição.
      status (int): Código de status HTTP da resposta.
      response_time_ms (float): Tempo de resposta em milissegundos.
      bytes_sent (int): Número de bytes enviados na resposta.
      cache_status (str): Status do cache ("HIT", "MISS", "BYPASS").
    """
    timestamp = datetime.now(UTC).isoformat()

    row = [
      timestamp, client_ip, method, path, status,
      f"{response_time_ms:.2f}", bytes_sent, cache_status
    ]

    with self._lock:
      try:
        with open(self.filepath, 'a', newline='') as f:
          writer = csv.writer(f)
          writer.writerow(row)
      except IOError as e:
        # Em um sistema real, isso aqui deveria ser logado apropriadamente
        print(f"ERRO: Falha ao escrever no arquivo de métricas: {e}")

# --- Instância global do logger de métricas ---
metrics_logger = MetricsLogger(filepath=config.METRICS_CSV_FILE)