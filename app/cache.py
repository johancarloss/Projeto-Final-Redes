# app/cache.py
# (Módulo de cache em memória - será implementado futuramente)

import time

class Cache:
  def __init__(self):
    self.store = {} # chave = caminho do arquivo, valor = (conteudo, timestamp)

  def get(self, key):
    """Retorna o conteudo do cache se existir, senão none"""
    if key in self.store:
      return self.store[key][0]
    
    return None
  
  def set(self, key, value):
    """Adiciona ou atualiza um valor no cache"""
    self.store[key] = (value, time.time())

  def has(self, key):
    """Verifica se existe no cache"""
    return key in self.store

    
