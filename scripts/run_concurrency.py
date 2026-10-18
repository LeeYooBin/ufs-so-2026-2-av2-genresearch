import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genresearch.concurrency.workers import run_pipeline

parser = argparse.ArgumentParser()
parser.add_argument('--requests', type=int, default=40)
parser.add_argument('--producers', type=int, default=2)
parser.add_argument('--consumers', type=int, default=2)
parser.add_argument('--queue-capacity', type=int, default=8)
parser.add_argument('--processing-ms', type=float, default=20)
parser.add_argument('--output', default='results/raw/concurrency.json')
args = parser.parse_args()

if args.requests < 0:
    parser.error('--requests deve ser >= 0')

queries = [f'consulta experimental {i % 7}' for i in range(args.requests)]
result = run_pipeline(queries, args.producers, args.consumers, args.queue_capacity, args.processing_ms)
output = ROOT / args.output
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k != 'results'}, ensure_ascii=False, indent=2))
print(f'Detalhes: {output}')
