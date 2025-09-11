# app/config.py

"""
Arquivo de configuração central para o servidor HTTP.
"""

# Configurações de Rede
HOST = "0.0.0.0"                # Escuta em todas as interfaces de rede
PORT = 8080                     # Porta padrão

# Configurações de Desempenho
MAX_CONNECTIONS = 100           # Número máximo de conexões enfileiradas no socket
KEEP_ALIVE_TIMEOUT = 5          # Segundos que uma conexão keep-alive aguarda por nova requisição

# Configurações de Arquivos
WWW_ROOT = "www"                # Diretório raiz para servir arquivos estáticos
LOG_FILE = "logs/server.log"    # Arquivo para registrar os logs de acesso