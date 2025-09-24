# app/server.py

import socket
import threading
import os
import sys
import logging
import argparse
import hashlib
from email.utils import formatdate
from datetime import datetime, timezone
from time import time

# Importa as configurações
from . import config

# Importa instâncias do cache e do logger de métricas
from .cache import cache_instance
from .metrics import metrics_logger

# --- Configuração do Logging ---
# Garante que o diretório de logs existe
os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)

logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(message)s',
  handlers=[
    logging.FileHandler(config.LOG_FILE),
    logging.StreamHandler(sys.stdout) # Também exibe logs no console
  ]
)

# --- Mapeamento de Tipos MIME ---
MIME_TYPES = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  ".txt": "text/plain",
}

def get_mime_type(filepath):
  """
  Retorna o tipo MIME com base na extensão do arquivo.
  """
  _, ext = os.path.splitext(filepath)
  return MIME_TYPES.get(ext.lower(), 'application/octet-stream')

# -- Novas Funções Utilitárias ---

def generate_etag(filepath):
  """
  Gera um ETag fraca baseada no tamanho e data de modificação do arquivo.
  """
  stat = os.stat(filepath)
  # Formato "tamanho-timestap_modificacao"
  etag_str = f"{stat.st_size}-{stat.st_mtime}"
  # Usamos SHA1 para criar um hash curto e opaco, como é comum
  return hashlib.sha1(etag_str.encode('utf-8')).hexdigest()

def parse_http_date(date_str):
  """
  Converte uma data em formato HTTP para timestamp. Simples, para este projeto.
  """
  from email.utils import parsedate_to_datetime
  try:
    return parsedate_to_datetime(date_str).timestamp()
  except (TypeError, ValueError):
    return None
  
def parse_headers(request_str):
  """
  Analisa os cabeçalhos HTTP da requisição e retorna um dicionário.
  """
  headers = {}
  lines = request_str.split('\r\n')[1:]  # Ignora a primeira linha (GET / HTTP/1.1)
  for line in lines:
    if not line:
      break # Fim dos cabeçalhos
    key, value = line.split(':', 1)
    headers[key.strip().lower()] = value.strip()
  return headers

class ClientThread(threading.Thread):
  """
  Thread para lidar com uma única conexão de cliente, suportando keep-alive.
  """
  def __init__(self, cliente_socket, client_address):
    super().__init__()
    self.client_socket = cliente_socket
    self.client_address = client_address
    self.daemon = True    # Permite que o programa principal saia mesmo se as threads estiverem ativas

  def run(self):
    """
    Processa requisições do cliente em um loop para suportar keep-alive.
    """
    # Define um timeout para a conexão. Se nenhuma requisição chegar, a conexão é fechada.
    self.client_socket.settimeout(config.KEEP_ALIVE_TIMEOUT)

    try:
      while True:
        start_time = time()

        # Recebe a requisição HTTP (limitada a 4096 bytes)
        request_data = self.client_socket.recv(4096)
        if not request_data:
          # Cliente fechou a conexão
          break

        # Tenta decodificar a requisição para processamento
        request_str = request_data.decode('utf-8', errors='ignore')
        self.process_request(request_str, start_time)

    except socket.timeout:
      logging.info(f"Conexão com {self.client_address[0]} expirou (timeout).")
    except Exception as e:
      logging.error(f"Erro na thread do cliente {self.client_address[0]}: {e}")
    finally:
      self.client_socket.close()

  def process_request(self, request_str, start_time):
    """
    Analisa a requisição HTTP, gerencia o cache e envia a resposta.
    Centraliza o log de métricas no final da execução.
    """
    status_code = 500 # Status padrão para erro inesperado
    bytes_sent = 0
    cache_status = "N/A"

    try:
      first_line = request_str.split('\r\n')[0]
      method, path, _ = first_line.split()
    except ValueError:
      method, path = "INVALID", "INVALID"
    
    try:
      # --- Lógica de Roteamento e Validação ---
      if method != 'GET':
        status_code = 405
        bytes_sent = self.send_error_response(status_code)
        return
      
      # Normaliza o path
      if path == '/':
        path = '/index.html'

      # Constrói o caminho absoluto do arquivo
      base_dir = os.path.abspath(config.WWW_ROOT)
      filepath = os.path.join(base_dir, path.lstrip('/'))

      # Segurança: Garante que o arquivo está dentro do diretório permitido
      if not os.path.abspath(filepath).startswith(base_dir):
        status_code = 403
        bytes_sent = self.send_error_response(status_code)
        return
      
      # Verifica se o arquivo existe
      if not os.path.exists(filepath) or not os.path.isfile(filepath):
        status_code = 404
        bytes_sent = self.send_error_response(status_code)
        return
      
      # Extraio os cabeçalhos da requisição
      request_headers = parse_headers(request_str)

      # --- Lógica de Cache Condicional ---
      current_etag = generate_etag(filepath)
      last_modified_time = os.path.getmtime(filepath)

      # Chega o If-None-Match (ETag) - tem prioridade
      if_none_match = request_headers.get('if-none-match')
      if if_none_match and if_none_match == current_etag:
        status_code = 304
        cache_status = "CONDITIONAL_HIT"
        bytes_sent = self.send_not_modified_response(current_etag, last_modified_time)
        return
      
      # Checa o If-Modified-Since (Data de Modificação)
      if_modified_since_str = request_headers.get('if-modified-since')
      if if_modified_since_str and not if_none_match:
        if_modified_since_time = parse_http_date(if_modified_since_str)
        # Se o arquivo não foi modificado desde a data enviada pelo cleinte
        if if_modified_since_time and int(last_modified_time) <= if_modified_since_time:
          status_code = 304
          cache_status = "CONDITIONAL_HIT"
          bytes_sent = self.send_not_modified_response(current_etag, last_modified_time)
          return
        
      # --- Servir o Arquivo (com captura de métricas) ---
      status_code = 200

      # Lógica de streaming movida para cá para capturar métricas corretamente
      file_size = os.path.getsize(filepath)
      streaming_threshold_bytes = config.STREAMING_THRESHOLD_MB * 1024 * 1024
      if file_size > streaming_threshold_bytes:
        self.stream_file(filepath, file_size, current_etag, last_modified_time)
        bytes_sent = file_size
        cache_status = "STREAMING"
      else:
        bytes_sent, cache_status = self.send_file_response(filepath, current_etag, last_modified_time)
        
    except Exception as e:
      # Em caso de um erro não tratado, loga o erro e envia 500
      logging.error(f"Erro inesperado ao processar '{method} {path}': {e}")
      try:
        status_code = 500
        bytes_sent = self.send_error_response(status_code)
      except:
        # Se até o envio do erro falhar, não há muito o que fazer
        pass
    finally:
      # --- PONTO ÚNICO DE LOG DE MÉTRICAS ---
      response_time_ms = (time() - start_time) * 1000
      metrics_logger.log_request(
        client_ip=self.client_address[0],
        method=method,
        path=path,
        status=status_code,
        response_time_ms=response_time_ms,
        bytes_sent=bytes_sent,
        cache_status=cache_status
      )

  def send_not_modified_response(self, etag, last_modified_time):
    """
    Envia uma resposta 304 Not Modified com os cabeçalhos apropriados.
    """
    extra_headers = {
      "ETag": etag,
      "Last-Modified": formatdate(timeval=last_modified_time, localtime=False, usegmt=True),
      # Cache-Control pode ser adicionado para maior controle
    }
    response_headers = self.build_headers(304, extra_headers)
    self.client_socket.sendall(response_headers.encode('utf-8'))

    return 0  # Nenhum byte de corpo é enviado
    
  # send_file_response agora aceita etag e last_modified para incluir nos cabeçalhos
  def send_file_response(self, filepath, etag, last_modified_time):
    """
    Envia uma resposta 200 OK com o conteúdo do arquivo.
    Usa streaming se o arquivo for maior que o limiar definido em config.
    Primeiro, tenta obter o conteúdo do cache. Se falhar (miss),
    lê do disco e armazena no cache para futuras requisições.
    """

    cache_status = "DISABLED"
    file_content = None
    cached_data = None

    # --- Etapa 1: Consultar o Cache ---
    if config.ENABLE_CACHE:
      cached_data = cache_instance.get(filepath)
      if cached_data:
        # Cache HIT! Agora, vamos REVALIDAR.
        cached_etag = cached_data.get('etag')
        current_etag = etag # Usamos a ETag já calculada no process_request

        if cached_etag == current_etag:
          # ETag bate! O cache é válido.
          cache_status = "HIT"
          logging.info(f"Cache HIT para o arquivo: {filepath} (Válido)")
          file_content = cached_data.get('content')
        else:
          # ETag diferente! O cache está OBSOLETO (stale)
          cache_status = "STALE"
          logging.info(f"Cache STALE para o arquivo: {filepath}. Invalidando.")
          cache_instance.invalidate(filepath)
      else:
        cache_status = "MISS"
        logging.info(f"Cache MISS para o arquivo: {filepath}")

    # --- Etapa 2: Ler do Disco (se cache miss ou stale) ---
    if file_content is None:
      try:
        # Limita o cache para arquivos menores que o limitar de streaming
        file_size = os.path.getsize(filepath)
        streaming_threshold_bytes = config.STREAMING_THRESHOLD_MB * 1024 * 1024

        if file_size > streaming_threshold_bytes:
          self.stream_file(filepath, file_size, etag, last_modified_time)
          return
        
        with open(filepath, 'rb') as f:
          file_content = f.read()

        # --- Etapa 3: Armazenar no Cache (após ler do disco) ---
        if config.ENABLE_CACHE:
          # Guardamos um dicionário com conteúdo e a ETag atual
          data_to_cache = {
            'content': file_content,
            'etag': etag
          }
          cache_instance.set(filepath, data_to_cache, config.DEFAULT_TTL_SECONDS)
      except Exception as e:
        logging.error(f"Erro ao ler o arquivo {filepath}: {e}")
        self.send_error_response(500)
        return
      
    # --- Etapa 4: Enviar a Resposta Completa ---
    # Esta parte é executada tanto para cache hit quanto para miss (com conteúdo lido do disco)
    try:
      mime_type = get_mime_type(filepath)
      headers = self.build_headers(200, {
        "Content-Type": mime_type,
        "Content-Length": len(file_content),
        "Connection": "keep-alive",
        "X-Cache-Status": cache_status,
        "ETag": etag,
        "Last-Modified": formatdate(timeval=last_modified_time, localtime=False, usegmt=True)
      })
      self.client_socket.sendall(headers.encode('utf-8') + file_content)

      return len(file_content), cache_status
    
    except Exception as e:
      logging.error(f"Erro ao enviar resposta para {filepath}: {e}")
      return 0, cache_status # Nenhum byte enviado em caso de erro
  
  def stream_file(self, filepath, file_size, etag, last_modified_time):
    """Função dedicada para servir arquivos grandes por streaming (não usa cache)."""
    logging.info(f"Servindo arquivo '{filepath}' por streaming (tamanho: {file_size} bytes)")
    mime_type = get_mime_type(filepath)
    headers = self.build_headers(200, {
      "Content-Type": mime_type,
      "Content-Length": file_size,
      "Connection": "keep-alive",
      "X-Cache-Status": "STREAMING", # Indica que foi servido por streaming
      "ETag": etag,
      "Last-Modified": formatdate(timeval=last_modified_time, localtime=False, usegmt=True)
    })
    self.client_socket.sendall(headers.encode('utf-8'))

    with open(filepath, 'rb') as f:
      while True:
        chunk = f.read(config.CHUNK_SIZE_BYTES)
        if not chunk:
          break
        self.client_socket.sendall(chunk)

  def send_error_response(self, status_code):
    """
    Envia uma resposta de errro HTTP simples.
    """
    error_messages = {
      400: "Bad Request", 403: "Forbidden", 404: "Not Found",
      405: "Method Not Allowed", 500: "Internal Server Error"
    }
    status_text = error_messages.get(status_code, "Unknown Error")
    body = f"<h1>{status_code} {status_text}</h1>".encode('utf-8')

    headers = self.build_headers(status_code, {
      "Content-Type": "text/html; charset=utf-8",
      "Content-Length": len(body),
      "Connection": "close"     # Fecha a conexão após um erro
    })

    full_response = headers.encode('utf-8') + body
    self.client_socket.sendall(full_response)

    return len(body)

  def build_headers(self, status_code, extra_headers):
    """
    Constrói a linha de status e os cabeçalhos HTTP.
    """
    status_messages = {
      200: "OK", 304: "Not Modified", 400: "Bad Request", 403: "Forbidden", 
      404: "Not Found", 405: "Method Not Allowed", 500: "Internal Server Error"
    }
    status_text = status_messages.get(status_code, "Unknown Status")

    response_line = f"HTTP/1.1 {status_code} {status_text}\r\n"

    headers = {
      "Date": datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT'),
      "Server": "PythonSimpleServer/1.0",
    }
    headers.update(extra_headers)

    headers_str = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    return f"{response_line}{headers_str}\r\n"

def main(host, port):
  """
  Função principal que inicia o servidor.
  """
  # Cria um socket TCP/IP
  server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  # Permite reutilizar o endereço para evitar erro "Address already in use"
  server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

  try:
    server_socket.bind((host, port))
    server_socket.listen(config.MAX_CONNECTIONS)
    logging.info(f"Servidor escutando em http://{host}:{port}")
    logging.info("Pressione Ctrl+C para encerrar.")

    while True:
      # Aceita uma nova conexão
      client_socket, client_address = server_socket.accept()
      logging.info(f"Conexão aceita de {client_address[0]}:{client_address[1]}")

      # Cria e inicia uma nova thread para o cliente
      # AVISO: Criar uma thread por conexão é um anti-padrão em produção
      # devido ao alto consumo de recursos. Usado aqui apenas para fins didáticos.
      new_thread = ClientThread(client_socket, client_address)
      new_thread.start()

  except OSError as e:
    logging.error(f"Erro ao iniciar o servidor: {e}. A porta {port} já está em uso?")
  except KeyboardInterrupt:
    logging.info("Servidor encerrado pelo usuário.")
  finally:
    server_socket.close()

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Servidor HTTP Minimal em Python")
  parser.add_argument('--port', type=int, default=config.PORT,
                      help=f"Porta para o servidor escutar (padrão: {[config.PORT]})")
  args = parser.parse_args()

  main(config.HOST, args.port)