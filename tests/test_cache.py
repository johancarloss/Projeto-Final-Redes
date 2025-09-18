# tests/test_cache.py

import pytest
import time
import threading
from app.cache import InMemoryCache

@pytest.fixture
def cache():
  """Fixture para criar uma nova instância de InMemoryCache para cada teste."""
  return InMemoryCache()

def test_cache_set_and_get(cache):
  """Testa a funcionalidade básica de set e get (cache hit)."""
  cache.set("key1", "value1", ttl_seconds=10)
  assert cache.get("key1") == "value1"

def test_cache_miss(cache):
  """Testa o comportamento de cache miss."""
  assert cache.get("non_existent_key") is None

def test_cache_expiration(cache):
  """Testa se o item expira corretamente após o TTL."""
  cache.set("key_exp", "value_exp", ttl_seconds=0.1)
  time.sleep(0.2)  # Espera o TTL expirar
  assert cache.get("key_exp") is None

def test_cache_invalidate(cache):
  """Testa a funcionalidade de invalidação de cache."""
  cache.set("key_inv", "value_inv", ttl_seconds=10)
  assert cache.get("key_inv") == "value_inv" # Verifica que está no cache
  cache.invalidate("key_inv")
  assert cache.get("key_inv") is None # Verifica se foi removido

def test_cache_stats(cache):
  """Testa se as estatísticas de hits e misses estão corretas."""
  # 1 miss inicial
  cache.get("key_stats")

  # 1 seg, depois 2 hits
  cache.set("key_stats", "value_stats", ttl_seconds=10)
  cache.get("key_stats")
  cache.get("key_stats")

  # 1 miss após expiração
  cache.set("key_exp_stats", "value_exp_stats", ttl_seconds=0.1)
  time.sleep(0.2)
  cache.get("key_exp_stats")

  stats = cache.stats()
  assert stats['hits'] == 2
  assert stats['misses'] == 2
  assert stats['current_size'] == 1  # Apenas "key_stats" deve estar no cache

def test_cache_thread_safety():
  """
  Teste a segunranla do cache em um ambiente multi-thread.
  Várias threads irão definir e obter valores simultaneamente.
  """
  shared_cache = InMemoryCache()
  num_threads = 20
  iterations = 100
  key = "concurrent_key"

  def worker():
    for i in range(iterations):
      # Alterna entre set e get para aumentar a concorrência
      if i % 2 == 0:
        shared_cache.set(key, f"value_{i}", ttl_seconds=1)
      else:
        shared_cache.get(key)

  threads = []
  for _ in range(num_threads):
    thread = threading.Thread(target=worker)
    threads.append(thread)
    thread.start()

  for thread in threads:
    thread.join()

  # O teste é considerado bem-sucedido se não houver exceções (como deadlock ou race conditions).
  # Também podemos verificar se as estatísticas fazem sentido.
  stats = shared_cache.stats()
  total_operations = num_threads * iterations

  # O número de hits e misses deve igual ao total de operações 'get'
  total_gets = num_threads * (iterations / 2)
  assert stats["hits"] + stats["misses"] == total_gets
  print(f"Teste de concorrência finalizado. Stats: {stats}")