import sys
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from time import sleep

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from genresearch.cache.race_demo import UnsafeLRU, KeyedLRU
from genresearch.cache.lru import SharedLRU


class RaceTests(unittest.TestCase):
    def test_unsafe_duplicates_deterministically(self):
        cache = UnsafeLRU(8, miss_delay_ms=30)
        barrier = Barrier(6)
        counter = [0]
        lock = Lock()
        def task(_):
            barrier.wait(timeout=5)
            def compute():
                with lock:
                    counter[0] += 1
                sleep(.02)
                return 'ok'
            return cache.get_or_compute('same', compute)
        with ThreadPoolExecutor(max_workers=6) as pool:
            result = list(pool.map(task, range(6)))
        self.assertEqual(counter[0], 6)
        self.assertEqual(sum(hit for _, hit in result), 0)

    def test_safe_modes_singleflight(self):
        for cache in (SharedLRU(8), KeyedLRU(8)):
            barrier = Barrier(6)
            counter = [0]
            lock = Lock()
            def task(_):
                barrier.wait(timeout=5)
                def compute():
                    with lock:
                        counter[0] += 1
                    sleep(.02)
                    return 'ok'
                return cache.get_or_compute('same', compute)
            with ThreadPoolExecutor(max_workers=6) as pool:
                result = list(pool.map(task, range(6)))
            self.assertEqual(counter[0], 1)
            self.assertEqual(sum(hit for _, hit in result), 5)

    def test_keyed_eviction_and_exception_recovery(self):
        cache = KeyedLRU(1)
        with self.assertRaises(RuntimeError):
            cache.get_or_compute('a', lambda: (_ for _ in ()).throw(RuntimeError('falha')))
        self.assertEqual(cache.get_or_compute('a', lambda: 1), (1, False))
        self.assertEqual(cache.get_or_compute('a', lambda: 2), (1, True))
        cache.get_or_compute('b', lambda: 3)
        self.assertEqual(cache.stats()['evictions'], 1)
        self.assertEqual(len(cache.key_locks), 0)

if __name__ == '__main__':
    unittest.main()
