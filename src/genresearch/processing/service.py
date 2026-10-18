"""Serviço de consulta RAG simplificado, sem LLM real."""
import hashlib
import threading
import time
from genresearch.cache.lru import SharedLRU
from genresearch.retrieval.search import Retriever


class GenResearchService:
    def __init__(self, retriever: Retriever, cache_capacity: int = 8, simulated_response_ms: float = 20,
                 top_k: int = 3, max_context_bytes: int = 2048):
        if simulated_response_ms < 0:
            raise ValueError('simulated_response_ms deve ser >= 0')
        self.retriever = retriever
        self.cache = SharedLRU(cache_capacity)
        self.simulated_response_ms = simulated_response_ms
        self.top_k = top_k
        self.max_context_bytes = max_context_bytes
        self.records = []
        self.records_lock = threading.Lock()

    def query(self, query: str) -> dict:
        started = time.perf_counter()
        def compute():
            retrieval_start = time.perf_counter()
            retrieved = self.retriever.search(query, self.top_k, self.max_context_bytes)
            retrieval_ms = (time.perf_counter() - retrieval_start) * 1000
            response_start = time.perf_counter()
            time.sleep(self.simulated_response_ms / 1000)
            response_ms = (time.perf_counter() - response_start) * 1000
            digest = hashlib.sha256((query + str(retrieved['chunks'])).encode()).hexdigest()[:12]
            return {'response': f'resposta-simulada-{digest}', 'retrieval_ms': retrieval_ms,
                    'response_ms': response_ms, 'chunk_count': retrieved['chunk_count'],
                    'context_bytes': retrieved['context_bytes'], 'approx_tokens': retrieved['approx_tokens']}
        key = (query, self.top_k, self.max_context_bytes)
        value, hit = self.cache.get_or_compute(key, compute)
        record = {'query': query, 'cache_hit': hit, 'total_ms': (time.perf_counter() - started) * 1000,
                  'worker': threading.current_thread().name, **value}
        with self.records_lock:
            self.records.append(record)
        return record
