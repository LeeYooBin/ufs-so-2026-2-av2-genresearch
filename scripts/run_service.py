import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genresearch.concurrency.workers import run_pipeline
from genresearch.retrieval.search import Retriever
from genresearch.processing.service import GenResearchService

p = argparse.ArgumentParser()
p.add_argument('--index', default='data/generated/index.jsonl')
p.add_argument('--read-mode', choices=['standard', 'mmap'], default='standard')
p.add_argument('--requests', type=int, default=40)
p.add_argument('--unique-queries', type=int, default=5)
p.add_argument('--producers', type=int, default=2)
p.add_argument('--consumers', type=int, default=2)
p.add_argument('--queue-capacity', type=int, default=8)
p.add_argument('--cache-capacity', type=int, default=8)
p.add_argument('--response-ms', type=float, default=20)
p.add_argument('--top-k', type=int, default=3)
p.add_argument('--context-bytes', type=int, default=2048)
p.add_argument('--output', default='results/raw/service.json')
a = p.parse_args()
if a.requests < 0 or a.unique_queries < 1:
    p.error('requests >= 0 e unique-queries >= 1')
retriever = Retriever(ROOT / a.index, a.read_mode)
service = GenResearchService(retriever, a.cache_capacity, a.response_ms, a.top_k, a.context_bytes)
terms = ['memoria swap', 'armazenamento mmap', 'threads mutex', 'rag contexto', 'fila consumidores', 'cache', 'pagina']
queries = [terms[i % len(terms)] + f' consulta{i % a.unique_queries}' for i in range(a.requests)]
result = run_pipeline(queries, a.producers, a.consumers, a.queue_capacity, handler=service.query)
result['cache'] = service.cache.stats()
result['query_metrics'] = service.records
result['index_records'] = len(retriever.records)
output = ROOT / a.output
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k not in ('results', 'query_metrics')}, ensure_ascii=False, indent=2))
print(f'Detalhes: {output}')
