# app/cache.py

import time
import threading
from sys import getsizeof

"""
Módulo que implementa um cache em LRU (Least Recently Used) em memória,
thread-safe, com TTL e limites de tamanho (itens e bytes).
"""

class _CacheNode:
  """Nó interno para a lista duplamente encadeada que gerencia a ordem LRU."""
  def __init__(self, key, value, expiration_time):
    self.key = key
    # self.value agora será um dicionário: {'content': ..., 'etag': ...}
    self.value = value
    self.expiration_time = expiration_time
    # Calculamos o tamanho com base no conteúdo real em bytes
    content_bytes = self.value.get('content', b'')
    self.size_bytes = len(content_bytes) if isinstance(content_bytes, bytes) else getsizeof(content_bytes)
    self.prev = None
    self.next = None

class LRUCache:
  """
  Uma classe que implementa um cache LRU thread-safe.
  
  Combina um dicionário para acesso O(1) e uma lista duplamente encadeada para manter a ordem de uso e realizar remoções em O(1).
  Suporta expiração por TTL, expiração preguiçosa e políticas de remoção
  baseadas no número de itens e no tamanho total em bytes.
  """

  def __init__(self, max_items, max_bytes):
    self._cache = {}
    self._lock = threading.Lock()

    # Limites para política de remoção
    self._max_items = max_items
    self._max_bytes = max_bytes

    # Nós sentinela (dummy) para simplificar a lógica da lista
    self._head = _CacheNode(None, None, None)  # Nó mais recentemente usado
    self._tail = _CacheNode(None, None, None)  # Nó menos recentemente usado
    self._head.next = self._tail
    self._tail.prev = self._head

    # Estatísticas
    self._hits = 0
    self._misses = 0
    self._current_bytes = 0

  # --- Métodos Privados para Gerenciar a Lista Encadeada ---

  def _remove_node(self, node):
    """Remove um nó da lista duplamente encadeada."""
    prev_node = node.prev
    next_node = node.next
    prev_node.next = next_node
    next_node.prev = prev_node

  def _add_to_front(self, node):
    """Adiciona um nó logo após o head (mais recentemente usado)."""
    node.next = self._head.next
    node.prev = self._head
    self._head.next.prev = node
    self._head.next = node

  # --- Métodos Públicos do Cache ---

  def get(self, key):
    """Recupera um item do cache, atualizando sua posição como mais recente."""
    with self._lock:
      node = self._cache.get(key)
      
      if node is None:
        self._misses += 1
        return None  # Cache miss
      
      # Expiração preguiçosa
      if time.time() > node.expiration_time:
        self._remove_node(node)
        del self._cache[node.key]
        self._current_bytes -= node.size_bytes
        self._misses += 1
        return None # Cache miss por expiração
      
      # Move o nó para a frente (mais recentemente usado)
      self._remove_node(node)
      self._add_to_front(node)

      self._hits += 1
      return node.value # Cache hit
    
  def set(self, key, value, ttl_seconds):
    """Adiciona ou atualiza um item no cache, aplicando a política LRU e os limites."""
    with self._lock:
      # Se o item já existe, removemos a versão antiga
      if key in self._cache:
        old_node = self._cache[key]
        self._current_bytes -= old_node.size_bytes
        self._remove_node(old_node)

      # Cria um novo nó
      expiration_time = time.time() + ttl_seconds
      new_node = _CacheNode(key, value, expiration_time)

      # Adiciona ao cache e à frente da lista
      self._cache[key] = new_node
      self._add_to_front(new_node)
      self._current_bytes += new_node.size_bytes

      # Aplica a política de remoção LRU
      self._enforce_limits()

  def _enforce_limits(self):
    """Remove itens antigos até que os limites sejam respeitados."""
    while (len(self._cache) > self._max_items) or (self._current_bytes > self._max_bytes):
      # Remove o nó menos recentemente usado (tail.prev)
      lru_node = self._tail.prev
      if lru_node == self._head:
        break  # Cache está vazio, nada a remover

      # Remove da lista, do dicionário e atualiza o tamanho
      self._remove_node(lru_node)
      del self._cache[lru_node.key]
      self._current_bytes -= lru_node.size_bytes

  def invalidate(self, key):
    """Remove um item específico do cache."""
    with self._lock:
      if key in self._cache:
        node_to_remove = self._cache[key]
        self._remove_node(node_to_remove)
        del self._cache[key]
        self._current_bytes -= node_to_remove.size_bytes

  def stats(self):
    """Retorna estatísticas do cache."""
    with self._lock:
      return {
        "hits": self._hits,
        "misses": self._misses,
        "current_items": len(self._cache),
        "current_bytes": self._current_bytes,
        "max_items": self._max_items,
        "max_bytes": self._max_bytes
      }

# --- Instância Global do Cache ---
from .config import MAX_CACHE_ITEMS, MAX_CACHE_BYTES

# A instância agora é criada com os limites definidos em config.py
cache_instance = LRUCache(MAX_CACHE_ITEMS, MAX_CACHE_BYTES)