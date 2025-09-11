# create_large_file.py

import os

"""
Script para gerar um arquivo binário grande para testes de streaming.
"""

# Garante que o diretório www existe
os.makedirs("www", exist_ok=True)

FILE_PATH = "www/image_large.jpg"
# Gera um arquivo de 3 MB (3 * 1024 * 1024 bytes)
FILE_SIZE_MB = 3
FILE_SIZE_BYTES = FILE_SIZE_MB * 1024 * 1024
CHUNK_SIZE = 1024 # Escreve em chunks de 1KB

try:
  with open(FILE_PATH, 'wb') as f:
    # Gera bytes aletórios para simular o conteúdo de uma imagem
    for _ in range(FILE_SIZE_BYTES // CHUNK_SIZE):
      f.write(os.urandom(CHUNK_SIZE))
  print(f"Arquivo '{FILE_PATH} de {FILE_SIZE_MB}MB criado com sucesso.")
except IOError as e:
  print(f"Erro ao criar o arquivo: {e}")