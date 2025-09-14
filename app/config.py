# app/config.py

# Servidor
HOST = "0.0.0.0"
PORT = 8080
WWW_ROOT = "www"
KEEP_ALIVE = False
CHUNK_SIZE = 64 * 1024
MAX_CONNECTION_BACKLOG = 128

# HTTP Cache-Control
CACHE_CONTROL_MAX_AGE = 60  # segundos

# Logs
SERVER_LOG_PATH = "logs/server.log"
METRICS_CSV_PATH = "metrics/requests.csv"

# Cache em memória
ENABLE_APP_CACHE = True          # <-- ESTA LINHA PRECISA EXISTIR
DEFAULT_TTL_SECONDS = 30
LRU_MAX_ITEMS = 128
LRU_MAX_BYTES = None
