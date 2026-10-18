import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from genresearch.ingestion.pipeline import generate_corpus, ingest
from genresearch.retrieval.search import Retriever
from genresearch.cache.lru import SharedLRU
from genresearch.processing.service import GenResearchService
from genresearch.concurrency.workers import run_pipeline


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        corpus = Path(self.temp.name) / 'corpus.jsonl'
        index = Path(self.temp.name) / 'index.jsonl'
        generate_corpus(corpus, 12)
        ingest(corpus, index)
        self.retriever = Retriever(index)

    def test_retrieval_limits(self):
        result = self.retriever.search('memoria swap', top_k=2, max_context_bytes=500)
        self.assertLessEqual(result['chunk_count'], 2)
        self.assertLessEqual(result['context_bytes'], 500)

    def test_cache_hits_and_evictions(self):
        cache = SharedLRU(1)
        calls = []
        def compute():
            calls.append(1)
            return 42
        self.assertFalse(cache.get_or_compute('a', compute)[1])
        self.assertTrue(cache.get_or_compute('a', compute)[1])
        cache.get_or_compute('b', compute)
        self.assertEqual(len(calls), 2)
        self.assertEqual(cache.stats()['evictions'], 1)

    def test_integrated_pipeline(self):
        service = GenResearchService(self.retriever, cache_capacity=3, simulated_response_ms=1)
        queries = ['memoria swap'] * 12
        result = run_pipeline(queries, producers=2, consumers=4, queue_capacity=4, handler=service.query)
        self.assertEqual(result['completed'], 12)
        self.assertEqual(result['lost'], 0)
        self.assertEqual(result['duplicate_ids'], 0)
        self.assertEqual(service.cache.stats()['misses'], 1)
        self.assertEqual(service.cache.stats()['hits'], 11)

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            SharedLRU(0)
        with self.assertRaises(ValueError):
            self.retriever.search('memoria', top_k=0)
