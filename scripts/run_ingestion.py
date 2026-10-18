import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genresearch.ingestion.pipeline import generate_corpus, ingest
from genresearch.storage.readers import iter_records

parser = argparse.ArgumentParser()
parser.add_argument('--documents', type=int, default=120)
parser.add_argument('--seed', type=int, default=42)
parser.add_argument('--chunk-size', type=int, default=40)
parser.add_argument('--overlap', type=int, default=8)
parser.add_argument('--mode', choices=['standard', 'mmap'], default='standard')
args = parser.parse_args()
corpus = ROOT / 'data/synthetic/corpus.jsonl'
index = ROOT / 'data/generated/index.jsonl'
generate_corpus(corpus, args.documents, args.seed)
summary = ingest(corpus, index, args.chunk_size, args.overlap)
records = list(iter_records(index, args.mode))
assert len(records) == summary['chunks']
summary.update({'read_mode': args.mode, 'validated_records': len(records)})
print(json.dumps(summary, ensure_ascii=False, indent=2))
