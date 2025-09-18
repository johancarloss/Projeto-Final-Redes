# app/cache.py

import time
import threading

"""
Módulo que implementa um cache em memória thread-safe com TTL
"""

class InMemoryCache:
  """
  Uma classe que implementa um cache em memória simples, thread-safe,
  com expiração de itens baseada em TTL (Time-To-Live) e estratégia 
  de expiração preguiçosa (expire-on-acess)
  """

  def __init__(self):
    """Iniciailza o cache."""
    self._cache = {}
    self._lock = threading.Lock()
    self._hits = 0
    self._misses = 0

  def get(self, key):
    """
    Recupera um item do cache.

    Verifica se o item existe e se não expirou. Se o item expirou,
    ele é removido da cache (expiração preguiçosa).

    Args:
      key (str): A chave do item a ser recuperado.
    
    Returns:
      O valor associado à chave, ou None se a chave não existir ou o item tiver expirado.
    """

    with self._lock:
      item = self._cache.get(key)

      if item is None:
        self._misses += 1
        return None # Cache miss
      
      value, expiration_time = item

      # Verifica se o item expirou
      if time.time() > expiration_time:
        # Expiração preguiçosa: remove o item ao acessá-lo
        del self._cache[key]
        self._misses += 1
        return None # Cache miss (item expirado)
      
      self._hits += 1
      return value # Cache hit
    
  def set(self, key, value, ttl_seconds):
    """
    Adiciona ou atualiza um item no cache com um TTL;
    
    Args:
      key (str): A chave do item a ser armazenado.
      value: O valor a ser armazenado.
      ttl_seconds (int): Tempo de vida do item em segundos.
    """
    expiration_time = time.time() + ttl_seconds
    with self._lock:
      self._cache[key] = (value, expiration_time)

  def invalidate(self, key):
    """
    Remove um item específico da cache, se ele existir.

    Args:
      key (str): A chave do item a ser invalidado.
    """
    with self._lock:
      if key in self._cache:
        del self._cache[key]

  def stats(self):
    """
    Retorna estatísticas do uso da cache.

    Returns:
      dict: Um dicionário com o número de hits, misses e o 
      tamanho atual da cache.
    """
    with self._lock:
      return {
        "hits": self._hits,
        "misses": self._misses,
        "current_size": len(self._cache)
      }
    
# Instância global do cache para ser usada pelo servidor
cache_instance = InMemoryCache()