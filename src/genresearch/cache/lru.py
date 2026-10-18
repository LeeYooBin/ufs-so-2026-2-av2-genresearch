"""Cache LRU compartilhado; check-compute-store protegido por Lock."""
from collections import OrderedDict
import threading
import time


class SharedLRU:
    def __init__(self, capacity: int):
        if capacity < 1:
            raise ValueError('capacity deve ser positiva')
        self.capacity = capacity
        self.data = OrderedDict()
        self.lock = threading.Lock()
        self.hits = self.misses = self.evictions = self.saved_ms = 0

    def get_or_compute(self, key, compute):
        # Lock cobre também compute: evita duas computações para a mesma chave,
        # mas serializa misses distintos. Trade-off a estudar na Etapa 5.
        with self.lock:
            if key in self.data:
                self.hits += 1
                value, compute_ms = self.data[key]
                self.data.move_to_end(key)
                self.saved_ms += compute_ms
                return value, True
            self.misses += 1
            started = time.perf_counter()
            value = compute()
            cost_ms = (time.perf_counter() - started) * 1000
            if len(self.data) >= self.capacity:
                self.data.popitem(last=False)
                self.evictions += 1
            self.data[key] = (value, cost_ms)
            return value, False

    def stats(self):
        with self.lock:
            return {'hits': self.hits, 'misses': self.misses, 'evictions': self.evictions,
                    'size': len(self.data), 'capacity': self.capacity, 'estimated_saved_ms': round(self.saved_ms, 3)}
