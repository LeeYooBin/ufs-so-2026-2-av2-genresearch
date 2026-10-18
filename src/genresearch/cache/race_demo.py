"""Demonstração isolada de cache stampede: inseguro, lock global e lock por chave."""
from collections import OrderedDict
from threading import Lock, RLock
import time


class UnsafeLRU:
    """Intencionalmente inseguro: não usar no serviço real."""
    def __init__(self, capacity=8, miss_delay_ms=0):
        if capacity < 1 or miss_delay_ms < 0:
            raise ValueError('capacidade positiva e atraso não negativo')
        self.capacity = capacity
        self.delay = miss_delay_ms / 1000
        self.data = OrderedDict()
        self.hits = self.misses = self.evictions = 0

    def get_or_compute(self, key, compute):
        if key in self.data:
            self.hits += 1
            self.data.move_to_end(key)
            return self.data[key], True
        # Janela de corrida intencional entre verificar e computar.
        if self.delay:
            time.sleep(self.delay)
        self.misses += 1
        value = compute()
        if key not in self.data and len(self.data) >= self.capacity:
            self.data.popitem(last=False)
            self.evictions += 1
        self.data[key] = value
        return value, False

    def stats(self):
        return dict(hits=self.hits, misses=self.misses, evictions=self.evictions,
                    size=len(self.data), capacity=self.capacity)


class KeyedLRU:
    """LRU com singleflight por chave; computações de chaves diferentes podem concorrer."""
    def __init__(self, capacity=8):
        if capacity < 1:
            raise ValueError('capacidade deve ser positiva')
        self.capacity = capacity
        self.data = OrderedDict()
        self.lock = RLock()
        self.key_locks = {}  # chave -> [Lock, número de usuários/reservas]
        self.hits = self.misses = self.evictions = 0

    def get_or_compute(self, key, compute):
        with self.lock:
            if key in self.data:
                self.hits += 1
                self.data.move_to_end(key)
                return self.data[key], True
            if key not in self.key_locks:
                self.key_locks[key] = [Lock(), 0]
            entry = self.key_locks[key]
            entry[1] += 1
        try:
            with entry[0]:
                with self.lock:
                    # Double-check: outra thread pode ter calculado enquanto esperávamos.
                    if key in self.data:
                        self.hits += 1
                        self.data.move_to_end(key)
                        return self.data[key], True
                value = compute()  # fora do lock global
                with self.lock:
                    self.misses += 1
                    if key not in self.data and len(self.data) >= self.capacity:
                        self.data.popitem(last=False)
                        self.evictions += 1
                    self.data[key] = value
                    self.data.move_to_end(key)
                return value, False
        finally:
            with self.lock:
                entry[1] -= 1
                if entry[1] == 0:
                    del self.key_locks[key]

    def stats(self):
        with self.lock:
            return dict(hits=self.hits, misses=self.misses, evictions=self.evictions,
                        size=len(self.data), capacity=self.capacity)
