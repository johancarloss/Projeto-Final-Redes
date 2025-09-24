# tests/test_integration.py

import pytest
import requests
import threading
import time
import os

# Importa a função main do servidor para rodá-lo em um thread separado
from app.server import main as start_server
from app import config

# --- Configuração do Teste ---
SERVER_URL = f"http://127.0.0.1:{config.PORT}"
TEST_FILE_CONTENT = "<html><body>Test Content</body></html>"

# A fixture agora aceita 'tmp_path' e 'monkeypatch' como argumentos
@pytest.fixture
def running_server(tmp_path, monkeypatch):
  """
  Fixture que inicia o servidor em uma thread separada pra os testes de integração.
  """
  # 1. Cria o diretório web temporário para testes
  test_www_dir = tmp_path / "www"
  test_www_dir.mkdir()

  # 2. Cria o arquivo de teste DENTRO do diretório temporário
  test_file = test_www_dir / "index.html"
  test_file.write_text(TEST_FILE_CONTENT)

  # 3. USA MONKEYPATCH PARA SUBSTITUIR A CONFIGURAÇÃO EM TEMPO DE EXECUÇÃO
  # Isso faz com que o servidor, ao ser iniciado, use nossa pasta
  # de teste em vez da pasta padrão (WWW_ROOT).
  monkeypatch.setattr(config, "WWW_ROOT", str(test_www_dir))

  # A variável global TEST_FILE_PATH também precisar ser atualizada
  global TEST_FILE_PATH
  TEST_FILE_PATH = str(test_file)

  # Inicia o servidor em uma thread separada
  server_thread = threading.Thread(target=start_server, args=(config.HOST, config.PORT), daemon=True)
  server_thread.start()
  time.sleep(0.5)  # Dá um tempo pro servidor iniciar

  # 'yield' passa o controle para os testes
  yield SERVER_URL

def test_conditional_get_with_etag(running_server):
  """
  Testea se o servidor retorna 304 Not Modified para uma ETag correspondente.
  """
  url = f"{running_server}/index.html"

  # 1. Primeira requisição para obter a ETag
  response1 = requests.get(url)
  assert response1.status_code == 200
  assert "ETag" in response1.headers
  etag = response1.headers["ETag"]

  # 2. SEgunda requisição com cabeçalho If-None-Match
  headers = {"If-None-Match": etag}
  response2 = requests.get(url, headers=headers)

  # Verifica se a resposta foi 304 e o corpo está vazio
  assert response2.status_code == 304
  assert response2.text == ""

def test_conditional_get_with_last_modified(running_server):
  """
  Testa se o servidor retorna 304 Not Modified para uma data de modificação correspondente.
  """
  url = f"{running_server}/index.html"

  # 1. Primeira requisição para obter Last-Modified
  response1 = requests.get(url)
  assert response1.status_code == 200
  assert "Last-Modified" in response1.headers
  last_modified = response1.headers["Last-Modified"]

  # 2. Segunda requisição com cabeçalho If-Modified-Since
  headers = {"If-Modified-Since": last_modified}
  response2 = requests.get(url, headers=headers)

  assert response2.status_code == 304
  assert response2.text == ""

def test_modified_file_returns_200(running_server):
  """
  Testa se o servidor retorna 200 OK quando com o novo conteúdo quando o arquivo é modificado.
  """
  url = f"{running_server}/index.html"

  # 1. Primeira requisição para obter a ETag original
  response1 = requests.get(url)
  assert response1.status_code == 200
  original_etag = response1.headers["ETag"]

  # 2. Modifica o arquivo no disco
  time.sleep(1)  # Garante que o timestamp de modificação será diferente
  new_content = "<html><body>Updated Content</body></html>"
  with open(TEST_FILE_PATH, "w") as f:
    f.write(new_content)

  # 3. Segunda requisição com o ETag ANTIGA
  headers = {"If-None-Match": original_etag}
  response2 = requests.get(url, headers=headers)

  # A rseposta deve ser 200 com o novo conteúdo, pois a ETag não coresponde mais
  assert response2.status_code == 200
  assert response2.text == new_content

  # A nova ETag deve ser diferente da original
  new_etag = response2.headers["ETag"]
  assert new_etag != original_etag

  # Restaura o arquivo original para não afetar outros testes
  with open(TEST_FILE_PATH, "w") as f:
    f.write(TEST_FILE_CONTENT)