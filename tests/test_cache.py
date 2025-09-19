# tests/test_cache.py

import pytest
import time
import threading
from app.cache import LRUCache

@pytest.fixture
def cache():
  """Fornece uma instância limpa do LRUCache para cada teste."""
  # Usamos limites pequenos para facilitar os testes
  return LRUCache(max_items=3, max_bytes=100)

def test_cache_set_and_get(cache):
  """Testa a funcionalidade básica de set e get (cache hit)."""
  cache.set("key1", b"value1", ttl_seconds=10)
  assert cache.get("key1") == b"value1"

def test_cache_miss(cache):
  """Testa o comportamento de cache miss."""
  assert cache.get("non_existent_key") is None

def test_cache_expiration(cache):
  """Testa se o item expira corretamente após o TTL."""
  cache.set("key_exp", b"value_exp", ttl_seconds=0.1)
  time.sleep(0.2)  # Espera o TTL expirar
  assert cache.get("key_exp") is None

def test_cache_invalidate(cache):
  """Testa a funcionalidade de invalidação de cache."""
  cache.set("key_inv", b"value_inv", ttl_seconds=10)
  cache.invalidate("key_inv")
  assert cache.get("key_inv") is None # Verifica se foi removido

def test_cache_stats(cache):
  """Testa se as estatísticas de hits e misses estão corretas."""
  cache.get("k1") # miss
  cache.set("k1", b"v1", 10)
  cache.get("k1") # hit
  stats = cache.stats()
  assert stats['hits'] == 1
  assert stats['misses'] == 1
  assert stats['current_items'] == 1
  assert stats['current_bytes'] == len(b"v1")

# --- Novos testes para a política de eviction LRU ---

def test_eviction_by_max_items(cache):
  """Testa a política de remoção LRU baseada no número máximo de itens."""
  cache.set("k1", b"v1", 10) # Mais antigo
  cache.set("k2", b"v2", 10)
  cache.set("k3", b"v3", 10) # Mais recente

  # Cache está cheio (3 itens). Adicionar o 4º deve remover o k1
  cache.set("k4", b"v4", 10)

  assert cache.get("k1") is None  # k1 deve ter sido removido
  assert cache.get("k2") is not None
  assert cache.get("k3") is not None
  assert cache.get("k4") is not None
  assert cache.stats()['current_items'] == 3

def test_eviction_by_max_bytes(cache):
  """Testa a política de remoção LRU baseada no tamanho máximo em bytes."""
  # Limite é 100 bytes
  cache.set("large1", b"a" * 50, 10) # 50 bytes
  cache.set("large2", b"b" * 50, 10) # 100 bytes. Cache cheio agora.

  # Adicionar outro item grande deve remover o large1 (mais antigo)
  cache.set("small", b"c" * 10, 10) # 10 bytes

  assert cache.get("large1") is None  # large1 deve ter sido removido
  assert cache.get("large2") is not None
  assert cache.get("small") is not None
  assert cache.stats()['current_bytes'] == 60  # 50 + 10

def test_lru_order_is_updated_on_get(cache):
  """Testa se um GET em um item o torna o mais recentemente usado."""
  cache.set("k1", b"v1", 10) # Mais antigo
  cache.set("k2", b"v2", 10)

  # Acessa k1 para torná-lo o mais recentemente usado
  time.sleep(0.1)  # Garante que o tempo mude
  cache.get("k1")

  cache.set("k3", b"v3", 10) # Cache cheio agora

  # Adicionar k4 deve remover k2
  cache.set("k4", b"v4", 10)

  assert cache.get("k2") is None  # k2 deve ter sido removido
  assert cache.get("k1") is not None
  assert cache.get("k3") is not None
  assert cache.get("k4") is not None