
# Configuração central do servidor


# Servidor
HOST = "0.0.0.0"
PORT = 8080
WWW_ROOT = "www"
KEEP_ALIVE = False                   # servidor simples: fecha conexão após resposta
CHUNK_SIZE = 64 * 1024               # tamanho de cada chunk enviado (64 KB)
MAX_CONNECTION_BACKLOG = 128         # fila de conexões pendentes

# HTTP Cache-Control
CACHE_CONTROL_MAX_AGE = 60           # segundos que o cliente pode reusar resposta

# Logs e métricas
SERVER_LOG_PATH = "logs/server.log"
METRICS_CSV_PATH = "metrics/requests.csv"

# Cache de aplicação (LRU + TTL)
ENABLE_APP_CACHE = True              # desative para comparar desempenho
DEFAULT_TTL_SECONDS = 30             # tempo padrão de vida no cache
LRU_MAX_ITEMS = 128                  # quantidade máxima de itens no cache
LRU_MAX_BYTES = None                 # None = sem limite por tamanho total
