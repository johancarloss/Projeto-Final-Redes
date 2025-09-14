# app/metrics.py
import os
import threading
import time

# Caminhos dos arquivos de log
SERVER_LOG_PATH = "logs/server.log"           # Log de requisições HTTP
METRICS_CSV_PATH = "metrics/requests.csv"    # Métricas detalhadas em CSV

# Locks para garantir thread-safety em escrita concorrente
_server_log_lock = threading.Lock()
_metrics_lock = threading.Lock()

# Cria os diretórios caso não existam
os.makedirs(os.path.dirname(SERVER_LOG_PATH), exist_ok=True)
os.makedirs(os.path.dirname(METRICS_CSV_PATH), exist_ok=True)

def http_log(line: str):
    """
    Adiciona uma linha de log no arquivo de logs do servidor.
    - Garante thread-safety usando _server_log_lock
    - Cada linha é gravada com \n ao final
    """
    with _server_log_lock:
        with open(SERVER_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")

def csv_log(row: dict):
    """
    Adiciona uma linha de métricas no CSV.
    - row deve ser um dicionário com as seguintes chaves:
      timestamp, client_ip, method, path, status, response_time_ms, bytes_sent, cache_hit, conditional_hit
    - Se o arquivo CSV não existir, escreve o cabeçalho
    - Garante thread-safety usando _metrics_lock
    """
    # Cabeçalho do CSV
    header = "timestamp,client_ip,method,path,status,response_time_ms,bytes_sent,cache_hit,conditional_hit\n"
    need_header = not os.path.exists(METRICS_CSV_PATH)  # Verifica se é necessário escrever o cabeçalho

    with _metrics_lock:
        with open(METRICS_CSV_PATH, "a", encoding="utf-8") as f:
            if need_header:
                f.write(header)  # escreve cabeçalho se arquivo novo
            # Escreve a linha de métricas formatada
            f.write("{timestamp},{client_ip},{method},{path},{status},{response_time_ms},{bytes_sent},{cache_hit},{conditional_hit}\n".format(**row))

def now_ts() -> int:
    """
    Retorna timestamp atual em segundos (epoch time).
    Útil para marcação de tempo em logs e métricas.
    """
    return int(time.time())
