#!/usr/bin/env python3
"""Complemento observacional separado dos benchmarks definitivos da AV2."""
import argparse
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genresearch.ingestion.pipeline import generate_corpus, ingest
from genresearch.retrieval.search import Retriever
from genresearch.processing.service import GenResearchService
from genresearch.concurrency.workers import run_pipeline


def proc_io():
    result = {}
    try:
        for line in Path('/proc/self/io').read_text().splitlines():
            key, value = line.split(':', 1)
            result[key] = int(value.strip())
    except OSError:
        pass
    return result


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({'timestamp_utc': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
                           'level': record.levelname, 'thread': record.threadName,
                           'event': record.event, **record.fields}, ensure_ascii=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--documents', type=int, default=120)
    p.add_argument('--requests', type=int, default=40)
    p.add_argument('--unique-queries', type=int, default=5)
    p.add_argument('--consumers', type=int, default=4)
    p.add_argument('--producers', type=int, default=2)
    p.add_argument('--queue-capacity', type=int, default=2)
    p.add_argument('--cache-capacity', type=int, default=8)
    p.add_argument('--response-ms', type=float, default=20)
    a = p.parse_args()
    if a.documents < 1 or a.requests < 1 or a.unique_queries < 1:
        p.error('documents, requests, unique-queries devem ser positivos')
    logs = ROOT / 'logs'; logs.mkdir(parents=True, exist_ok=True)
    raw = ROOT / 'results/raw'; raw.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('genresearch.av2.observability')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(logs / 'etapa6_5_events.jsonl', mode='w', encoding='utf-8')
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    def event(name, **fields):
        # logging.FileHandler serializa writes entre threads com lock interno.
        logger.info('', extra={'event': name, 'fields': fields})
    before = proc_io()
    with tempfile.TemporaryDirectory(prefix='av2-observability-') as temp:
        corpus = Path(temp) / 'corpus.jsonl'
        index = Path(temp) / 'index.jsonl'
        start = time.perf_counter()
        generate_corpus(corpus, a.documents)
        generation_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        summary = ingest(corpus, index)
        ingest_ms = (time.perf_counter() - start) * 1000
        event('ingestion_completed', **summary, corpus_generation_ms=round(generation_ms, 3), ingestion_ms=round(ingest_ms, 3))
        retriever = Retriever(index)
        service = GenResearchService(retriever, a.cache_capacity, a.response_ms)
        terms = ['memoria swap', 'armazenamento mmap', 'threads mutex', 'rag contexto', 'fila consumidores', 'cache', 'pagina']
        pool = [f'{terms[i % len(terms)]} consulta{i}' for i in range(a.unique_queries)]
        queries = [pool[i % len(pool)] for i in range(a.requests)]
        def handle(query):
            event('query_received', query=query)
            try:
                rec = service.query(query)
            except Exception as exc:
                event('failure', error_type=type(exc).__name__, message=str(exc))
                raise
            event('cache_hit' if rec['cache_hit'] else 'cache_miss', query=query)
            if not rec['cache_hit']:
                event('retrieval_completed', query=query, chunks=rec['chunk_count'],
                      context_bytes=rec['context_bytes'], retrieval_ms=rec['retrieval_ms'])
                event('response_generated', query=query, response_summary=rec['response'],
                      response_ms=rec['response_ms'])
            event('query_completed', query=query, total_ms=rec['total_ms'])
        pipeline = run_pipeline(queries, a.producers, a.consumers, a.queue_capacity, handler=handle)
        event('pipeline_completed', submitted=pipeline['submitted'], completed=pipeline['completed'],
              lost=pipeline['lost'], duplicates=pipeline['duplicate_ids'], errors=pipeline['errors'])
        # Falha isolada: não altera o índice nem os resultados oficiais.
        try:
            Retriever(Path(temp) / 'missing_index.jsonl')
        except FileNotFoundError as exc:
            event('failure', error_type='FileNotFoundError', message='missing_index (controlled)')
        else:
            raise AssertionError('missing index unexpectedly succeeded')
        event('shutdown', status='normal')
    after = proc_io()
    delta = {key: after.get(key, 0) - before.get(key, 0) for key in before.keys() & after.keys()}
    output = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'note': 'Coleta complementar; NAO integra as 39 execucoes definitivas.',
              'parameters': vars(a), 'ingestion': {**summary, 'corpus_generation_ms': generation_ms,
                                                 'ingestion_ms': ingest_ms},
              'io_delta': delta,
              'io_ops_per_second': {'read_syscalls_per_s': delta.get('syscr', 0) / (pipeline['elapsed_ms']/1000),
                                    'write_syscalls_per_s': delta.get('syscw', 0) / (pipeline['elapsed_ms']/1000)},
              'io_rate_note': 'Taxas aproximadas: denominador e tempo do pipeline, enquanto contadores incluem ingestao; nao usar como benchmark de E/S.',
              'pipeline': {k: v for k, v in pipeline.items() if k != 'results'},
              'cache': service.cache.stats(), 'event_log': str(logs / 'etapa6_5_events.jsonl')}
    dest = raw / 'etapa6_5_observability.json'
    dest.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    handler.close(); logger.removeHandler(handler)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print('Eventos:', logs / 'etapa6_5_events.jsonl')
    print('Metricas:', dest)

if __name__ == '__main__':
    main()
