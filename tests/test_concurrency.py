import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from genresearch.concurrency.workers import run_pipeline


class ConcurrencyTests(unittest.TestCase):
    def test_no_loss_or_duplicates(self):
        data = run_pipeline([str(i) for i in range(51)], 3, 4, 2, 0)
        self.assertEqual(data['submitted'], 51)
        self.assertEqual(data['completed'], 51)
        self.assertEqual(data['lost'], 0)
        self.assertEqual(data['duplicate_ids'], 0)
        self.assertEqual(data['errors'], [])

    def test_empty_workload(self):
        data = run_pipeline([], 2, 2, 1, 0)
        self.assertEqual(data['completed'], 0)

    def test_handler_error_does_not_hang(self):
        def handler(value):
            if value == 'bad':
                raise ValueError('controlled')
        data = run_pipeline(['ok', 'bad', 'ok'], 2, 2, 1, handler=handler)
        self.assertEqual(data['completed'], 3)
        self.assertEqual(len(data['errors']), 1)
        self.assertEqual(data['lost'], 0)

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            run_pipeline(['a'], consumers=0)


if __name__ == '__main__':
    unittest.main()
