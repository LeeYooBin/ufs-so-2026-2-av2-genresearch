import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from genresearch.concurrency.workers import run_pipeline

class ObservabilityTests(unittest.TestCase):
    def test_queue_and_worker_metrics(self):
        r = run_pipeline(['a'] * 12, producers=2, consumers=4, queue_capacity=2, processing_ms=2)
        self.assertEqual(r['lost'], 0)
        self.assertEqual(r['completed'], 12)
        self.assertGreaterEqual(r['mean_queue_observed_at_put'], 0)
        self.assertLessEqual(r['mean_queue_observed_at_put'], 2)
        self.assertEqual(len(r['worker_processing_fraction']), 4)
        self.assertTrue(all(0 <= v <= 1.1 for v in r['worker_processing_fraction'].values()))
