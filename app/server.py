# app/server.py

import socket
import threading
import os
import sys
import logging
import argparse
from datetime import datetime, timezone
from time import time

# Importando o cache
from cache import Cache
cache = Cache()

# Importa as configurações
import config

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
  '.ico': 'image/x-icon'
}

def get_mime_type(filepath):
  """
  Retorna o tipo MIME com base na extensão do arquivo.
  """
  _, ext = os.path.splitext(filepath)
  return MIME_TYPES.get(ext.lower(), 'application/octet-stream')

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
    Analisa a requisição, determina a ação e envia a resposta.
    Esta função agora orquestra envio, sea completo ou por streaming.
    """
    try:
      first_line = request_str.split('\r\n')[0]
      method, path, _ = first_line.split()
    except ValueError:
      self.send_error_response(400)
      self.log_request(request_str, 400, start_time)
      return
    
    if method != 'GET':
      self.send_error_response(405)
      self.log_request(request_str, 405, start_time)
      return
    
    if path == '/':
      path = '/index.html'

    base_dir = os.path.abspath(config.WWW_ROOT)
    filepath = os.path.join(base_dir, path.lstrip('/'))

    if not os.path.abspath(filepath).startswith(base_dir):
      self.send_error_response(403)
      self.log_request(request_str, 403, start_time)
      return
    
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
      self.send_error_response(404)
      self.log_request(request_str, 404, start_time)
      return
    
    # Se o arquivo existe e é válido, envia a resposta de sucesso.
    self.send_file_response(filepath)
    self.log_request(request_str, 200, start_time)

  def send_file_response(self, filepath):
    """
    Envia uma resposta 200 OK com o conteúdo do arquivo.
    Usa streaming se o arquivo for maior que o limiar definido em config.
    """
    try:
      filepath_normalized = os.path.abspath(filepath)
      file_size = os.path.getsize(filepath)
      mime_type = get_mime_type(filepath)

      # Para tipos textuais, adiciona charset UTF-8
      if mime_type.startswith("text/") or mime_type == "application/javascript":
        mime_type += "; charset=utf-8"

      # Constrói e envia os cabeçalhos primeiro
      headers = self.build_headers(200, {
        "Content-Type": mime_type,
        "Content-Length": file_size,
        "Connection": "keep-alive"
      })
      self.client_socket.sendall(headers.encode('utf-8'))

      # --- Integração com Cache ---
      cached = cache.get(filepath_normalized)
      if cached:
        logging.info(f"Cache hit: {filepath_normalized}")
        self.client_socket.sendall(cached)
        return
      else:
        logging.info(f"Cache miss: {filepath_normalized}")


      # Decode se usa streaming ou envia tudo de uma vez
      streaming_threshold_bytes = config.STREAMING_THRESHOLD_MB * 1024 * 1024

      if file_size > streaming_threshold_bytes:
        # --- Lógica de Streaming ---
        logging.info(f"Servindo arquivo {filepath_normalized} via streaming ({file_size} bytes).")
        with open(filepath_normalized, 'rb') as f:
          while True:
            chunk = f.read(config.CHUNK_SIZE_BYTES)
            if not chunk:
              break
            self.client_socket.sendall(chunk)
      else:
        # --- Envio completo para arquivos pequenos ---
        with open(filepath_normalized, 'rb') as f:
          self.client_socket.sendall(f.read())
    
    except Exception as e:
      logging.error(f"Erro ao enviar arquivo {filepath_normalized}: {e}")
      # Se ocorrer um erro durante o envio, a conexão já pode estar comprometida,
      # mas tentamos enviar um erro de servidor mesmo assim.
      if not self.client_socket._closed:
        self.send_error_response(500)

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

  def build_headers(self, status_code, extra_headers):
    """
    Constrói a linha de status e os cabeçalhos HTTP.
    """
    status_messages = {
      200: "OK", 400: "Bad Request", 403: "Forbidden", 404: "Not Found",
      405: "Method Not Allowed", 500: "Internal Server Error"
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
  
  def log_request(self, request_str, status_code, start_time):
    """
    Registra os detalhes da requisição no log.
    """
    response_time_ms = (time() - start_time) * 1000
    client_ip = self.client_address[0]

    try:
      first_line = request_str.split('\r\n')[0]
      method, path, _ = first_line.split()
    except ValueError:
      # Não foi possível parsear, loga o que for possível
      method, path = "INVALID", "INVALID"

    logging.info(
      f'client_ip="{client_ip}" method="{method}" path="{path}" '
      f'status={status_code} response_time_ms={response_time_ms:.2f}'
    )

def main(host, port):
  """Função principal que inicia o servidor."""
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