# tests/test_server.py

import pytest
# Importa a função a ser testada do módulo do servidor
from app.server import get_mime_type

"""
Testes unitários para as funções utilitárias do servidor.
"""

def test_get_mime_type():
  """
  Testa a função get_mime_type para garantir que elea retorna os Content-Types
  corretos para uma variedade de extensões de arquivo, incluindo com letras
  maiúsculas e extensões desconhecidas.
  """
  # Casos de test: (nome_do_arquivo, tipo_mime_esperado)
  test_cases = {
    "index.html": "text/html",
    "style.css": "text/css",
    "script.js": "application/javascript",
    "photo.jpg": "image/jpeg",
    "image.JPEG": "image/jpeg",  # Testa insensibilidade a maiúsculas/minúsculas
    "document.txt": "text/plain",
    "archive.zip": "application/octet-stream", # Exemplo de tipo não mapeado
    "no_extension": "application/octet-stream" # Arquivo sem extensão
  }

  for filename, expected_mime in test_cases.items():
    assert get_mime_type(filename) == expected_mime, \
      f"Falha para '{filename}': esperado '{expected_mime}', obteve '{get_mime_type(filename)}'"

def test_placeholder():
  """
  Placeholder para garantir que o pytest está configurado corretamente.
  """
  assert True