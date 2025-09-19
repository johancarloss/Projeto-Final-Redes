# app/config.py

"""
Arquivo de configuração central para o servidor HTTP.
"""

# Configurações de Rede, Desempenho, Arquivos...
HOST = "0.0.0.0"                # Escuta em todas as interfaces de rede
PORT = 8080                     # Porta padrão
MAX_CONNECTIONS = 100           # Número máximo de conexões enfileiradas no socket
KEEP_ALIVE_TIMEOUT = 5          # Segundos que uma conexão keep-alive aguarda por nova requisição
WWW_ROOT = "www"                # Diretório raiz para servir arquivos estáticos
LOG_FILE = "logs/server.log"    # Arquivo para registrar os logs de acesso
STREAMING_THRESHOLD_MB = 2      # Arquivos maiores que este valor (em MB) serão transmitidos em chunks
CHUNK_SIZE_BYTES = 8192         # Tamanho de cada chunk de streaming (8 KB)

# Configurações de Cache
ENABLE_CACHE = True            # Habilita ou desabilita o cache em memória
DEFAULT_TTL_SECONDS = 30         # Tempo padrão de vida do cache (em segundos)

# Novos limites para Política de Eviction (LRU)
# O cache irá remover itens antigos se qualquer um dos limites for excedido.
MAX_CACHE_ITEMS = 100          # Número máximo de itens na cache
MAX_CACHE_SIZE_MB = 5 * 1024 * 1024         # Tamanho máximo da cache (5MB)