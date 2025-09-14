# tests/test_server.py
import threading
import time
import os
import requests

from app.server import serve   # importa o servidor a ser testado
from app import config         # importa configurações globais

# Porta de teste (evita conflito com a porta padrão do servidor em produção)
TEST_PORT = 9090
# URL base usada nos testes
BASE = f"http://127.0.0.1:{TEST_PORT}"


# Função para iniciar o servidor em thread separada

def start_server_once():
    """
    Inicia o servidor HTTP em background (thread daemon).
    Aguarda meio segundo para garantir que ele esteja pronto.
    """
    t = threading.Thread(target=serve, args=(TEST_PORT,), daemon=True)
    t.start()
    # espera o servidor subir antes de enviar requests
    time.sleep(0.5)


# Função auxiliar que garante que index.html exista

def ensure_index():
    """
    Garante que o arquivo index.html exista no diretório WWW_ROOT.
    Caso não exista, cria com conteúdo simples.
    """
    os.makedirs(config.WWW_ROOT, exist_ok=True)
    idx = os.path.join(config.WWW_ROOT, "index.html")
    if not os.path.exists(idx):
        with open(idx, "w", encoding="utf-8") as f:
            f.write("<h1>ok</h1>")


# Teste principal: GET normal e validação de 304 (ETag)

def test_get_and_304():
    """
    1. Cria index.html se não existir.
    2. Sobe o servidor de teste em thread.
    3. Faz requisição GET para index.html -> espera HTTP 200.
    4. Extrai ETag retornado pelo servidor.
    5. Refaz GET com cabeçalho If-None-Match=ETag -> espera HTTP 304.
    """
    ensure_index()
    start_server_once()

    # Primeira requisição: deve retornar 200 e incluir cabeçalho ETag
    r1 = requests.get(f"{BASE}/index.html", timeout=5)
    assert r1.status_code == 200
    assert "ETag" in r1.headers
    etag = r1.headers["ETag"]

    # Segunda requisição: envia o mesmo ETag no cabeçalho
    # O servidor deve responder 304 Not Modified (sem corpo)
    r2 = requests.get(f"{BASE}/index.html", headers={"If-None-Match": etag}, timeout=5)
    assert r2.status_code == 304
