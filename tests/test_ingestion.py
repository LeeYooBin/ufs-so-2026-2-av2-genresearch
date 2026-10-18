import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from genresearch.ingestion.pipeline import chunk_text, generate_corpus, ingest, simulated_vector
from genresearch.storage.readers import read_standard, read_mapped, iter_records

class PipelineTests(unittest.TestCase):
    def test_chunks(self):
        self.assertEqual(chunk_text('a b c d e', 3, 1), ['a b c', 'c d e', 'e'])
        with self.assertRaises(ValueError): chunk_text('a b', 2, 2)
    def test_vectors_deterministic(self):
        self.assertEqual(simulated_vector('texto'), simulated_vector('texto'))
        self.assertNotEqual(simulated_vector('texto'), simulated_vector('outro'))
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); corpus = base/'corpus.jsonl'; index = base/'index.jsonl'
            generate_corpus(corpus, 8)
            result = ingest(corpus, index)
            self.assertEqual(result['documents'], 8)
            self.assertGreater(result['chunks'], 8)
            self.assertEqual(read_standard(index), read_mapped(index))
            self.assertEqual(list(iter_records(index, 'standard')), list(iter_records(index, 'mmap')))
    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'empty';p.write_bytes(b'')
            self.assertEqual(read_mapped(p), b'')

if __name__ == '__main__': unittest.main()
