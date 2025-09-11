# app/server.py

import socket
import threading
import os
import sys
import logging
import argparse
from datetime import datetime, timezone
from time import time

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

        try:
          # Tenta decodificar a requisição para processamento
          request_str = request_data.decode('utf-8')
          # Processa a requisição e obtém a resposta
          response, status_code = self.handle_request(request_str)
        except UnicodeDecodeError:
          # Trata o caso de requests que não são texto (ex: binários)
          response, status_code = self.build_response(
            status_code=400,
            body=b"<h1>400 Bad Request</h1>"
          )
        except Exception as e:
          logging.error(f"Erro ao processar requisição: {e}")
          response, status_code = self.build_response(
            status_code=500,
            body=b"<h1>500 Internal Server Error</h1>"
          )

        self.client_socket.sendall(response)

        # Log da requisição processada
        self.log_request(request_str, status_code, start_time)

    except socket.timeout:
      logging.info(f"Conexão com {self.cliente_address[0]} expirou (timeout).")
    except Exception as e:
      logging.error(f"Erro na thread do cliente {self.client_address[0]}: {e}")
    finally:
      self.client_socket.close()

  def handle_request(self, request_str):
    """
    Analisa a requisição HTTP e retorna a resposta apropriada.
    """
    # Pega a primeira linha da requisição (ex: "GET /index.html HTTP/1.1")
    first_line = request_str.split('\r\n')[0]
    try:
      method, path, _ = first_line.split()
    except ValueError:
      return self.build_response(status_code=400, body=b"<h1>400 Bad Request</h1>"), 400
    
    if method != 'GET':
      return self.build_response(status_code=405, body=b"<h1>405 Method Not Allowed</h1>"), 405
    
    # Trata o caso da raiz "/"
    if path == '/':
      path = '/index.html'

    # Monta o caminho do arquivo no sistema e previne Path Traversal Attack
    base_dir = os.path.abspath(config.WWW_ROOT)
    filepath = os.path.join(base_dir, path.lstrip('/'))

    if not os.path.abspath(filepath).startswith(base_dir):
      return self.build_response(status_code=403, body=b"<h1>403 Forbidden</h1>"), 403
    
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
      return self.build_response(status_code=404, body=b"<h1>404 Not Found</h1>"), 404
    
    # Lê o conteúdo do arquivo
    with open(filepath, 'rb') as f:
      file_content = f.read()

    return self.build_response(
      status_code=200,
      body=file_content,
      filepath=filepath
    ), 200
  
  def build_response(self, status_code, body, filepath=None):
    """
    Constrói uma resposta HTTP completa com cabeçalhos.
    """
    status_messages = {
      200: "OK", 400: "Bad Request", 403: "Forbidden",
      404: "Not Found", 405: "Method Not Allowed", 500: "Internal Server Error"
    }
    status_text = status_messages.get(status_code, "Unknown Status")

    response_line = f"HTTP/1.1 {status_code} {status_text}\r\n"

    # Cabeçalhos padrão
    headers = {
      "Date": datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT'),
      "Server": "PythonSimpleServer/1.0",
      "Connection": "keep-alive",
      "Content-Length": len(body)
    }

    if filepath:
      headers["Content-Type"] = get_mime_type(filepath)
    else:
      headers["Content-Type"] = "text/html"

    # Converte cabeçalhos para string
    headers_str = "".join(f"{k}: {v}\r\n" for k, v in headers.items())

    # Junta tudo e codifica para bytes
    return f"{response_line}{headers_str}\r\n".encode('utf-8') + body
  
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