# app/metrics.py
import os
import threading
import time

SERVER_LOG_PATH = "logs/server.log"
METRICS_CSV_PATH = "metrics/requests.csv"

_server_log_lock = threading.Lock()
_metrics_lock = threading.Lock()

os.makedirs(os.path.dirname(SERVER_LOG_PATH), exist_ok=True)
os.makedirs(os.path.dirname(METRICS_CSV_PATH), exist_ok=True)

def http_log(line: str):
    with _server_log_lock:
        with open(SERVER_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")

def csv_log(row: dict):
    header = "timestamp,client_ip,method,path,status,response_time_ms,bytes_sent,cache_hit,conditional_hit\n"
    need_header = not os.path.exists(METRICS_CSV_PATH)
    with _metrics_lock:
        with open(METRICS_CSV_PATH, "a", encoding="utf-8") as f:
            if need_header:
                f.write(header)
            f.write("{timestamp},{client_ip},{method},{path},{status},{response_time_ms},{bytes_sent},{cache_hit},{conditional_hit}\n".format(**row))

def now_ts() -> int:
    return int(time.time())
