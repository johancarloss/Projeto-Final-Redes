# app/cache.py
from collections import OrderedDict
import threading
import time

class MemoryCache:
    """
    Implementação de um cache em memória com:
    - Política de remoção LRU (Least Recently Used → remove o item menos usado recentemente)
    - TTL (time-to-live) individual para cada item
    - Thread-safe (usa RLock para sincronização)
    - Limite de número de itens e, opcionalmente, limite de memória em bytes
    """
    def __init__(self, max_items=128, max_bytes=None, default_ttl=30):
        # Máximo de itens armazenados no cache
        self.max_items = max_items
        # Máximo de bytes permitidos no cache (None = sem limite)
        self.max_bytes = max_bytes
        # Tempo de vida padrão de cada item (em segundos)
        self.default_ttl = default_ttl

        # Lock para garantir thread-safety em acessos concorrentes
        self._lock = threading.RLock()
        # OrderedDict mantém a ordem de inserção (usado para implementar LRU)
        # Cada item armazenado como: chave -> (valor, timestamp_expiracao, tamanho)
        self._store = OrderedDict()
        self._bytes_in_use = 0  # Quantidade atual de bytes ocupados
        self._hits = 0          # Quantas vezes um item foi encontrado no cache
        self._misses = 0        # Quantas vezes um item não foi encontrado no cache

    def stats(self):
        """
        Retorna estatísticas do cache:
        - número de itens armazenados
        - bytes em uso
        - hits (acessos bem-sucedidos)
        - misses (falhas de acesso)
        """
        with self._lock:
            return {
                "items": len(self._store),
                "bytes_in_use": self._bytes_in_use,
                "hits": self._hits,
                "misses": self._misses,
            }

    def _evict_if_needed(self):
        """
        Remove itens mais antigos (menos usados recentemente) se:
        - ultrapassar o limite de itens (max_items)
        - ultrapassar o limite de bytes (max_bytes)
        """
        # Remove itens até respeitar o limite de quantidade
        while self.max_items and len(self._store) > self.max_items:
            k, (v, expiry, sz) = self._store.popitem(last=False)  # remove o primeiro (mais antigo)
            self._bytes_in_use -= sz

        # Remove itens até respeitar o limite de memória
        if self.max_bytes is not None:
            while self._bytes_in_use > self.max_bytes and self._store:
                k, (v, expiry, sz) = self._store.popitem(last=False)
                self._bytes_in_use -= sz

    def _expired(self, expiry_ts):
        """
        Verifica se o item já expirou.
        - Retorna True se o timestamp de expiração foi atingido.
        """
        return expiry_ts is not None and time.time() >= expiry_ts

    def get(self, key):
        """
        Obtém um item do cache.
        - Se não existir, conta como 'miss'
        - Se existir mas estiver expirado, remove e conta como 'miss'
        - Se existir e estiver válido, atualiza como mais recentemente usado (LRU) e conta como 'hit'
        """
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None

            value, expiry_ts, sz = self._store.pop(key)

            if self._expired(expiry_ts):
                # Se expirado: remove o item
                self._bytes_in_use -= sz
                self._misses += 1
                return None

            # Caso válido: reinsere como o mais recente (fim do OrderedDict)
            self._store[key] = (value, expiry_ts, sz)
            self._hits += 1
            return value

    def set(self, key, value, ttl_seconds=None):
        """
        Adiciona um item ao cache.
        - TTL pode ser configurado por item ou usa o padrão (default_ttl).
        - Atualiza estatísticas de memória usada.
        - Pode acionar a remoção (evict) caso ultrapasse limites.
        """
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl

        # Calcula timestamp de expiração
        expiry = time.time() + ttl_seconds if ttl_seconds > 0 else None
        # Estima tamanho do valor (se tiver __len__)
        sz = len(value) if hasattr(value, "__len__") else 0

        with self._lock:
            # Se já existe, remove para atualizar
            if key in self._store:
                _, _, old_sz = self._store.pop(key)
                self._bytes_in_use -= old_sz

            # Insere o item no cache
            self._store[key] = (value, expiry, sz)
            self._bytes_in_use += sz

            # Remove itens se passar dos limites
            self._evict_if_needed()

    def invalidate(self, key):
        """
        Remove um item específico do cache, se existir.
        - Libera a memória usada por ele.
        """
        with self._lock:
            if key in self._store:
                _, _, sz = self._store.pop(key)
                self._bytes_in_use -= sz
