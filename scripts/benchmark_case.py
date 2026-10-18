"""Uma configuração por processo: permite observar RSS e faults sem contaminação entre casos."""
import argparse
import json
import os
import resource
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genresearch.ingestion.pipeline import generate_corpus, ingest
from genresearch.storage.readers import read_standard, read_mapped
from genresearch.concurrency.workers import run_pipeline
from genresearch.retrieval.search import Retriever
from genresearch.processing.service import GenResearchService


def proc_sample():
    status = {}
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith(('VmRSS:', 'VmSize:', 'Threads:')):
            key, value = line.split(':', 1)
            status[key] = int(value.strip().split()[0])
    mem = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith(('MemAvailable:', 'Cached:', 'SwapFree:', 'SwapTotal:')):
            key, value = line.split(':', 1)
            mem[key] = int(value.strip().split()[0])
    io = {}
    for line in Path('/proc/self/io').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in ('read_bytes', 'write_bytes', 'rchar', 'wchar', 'syscr', 'syscw'):
            io[key] = int(value)
    r = resource.getrusage(resource.RUSAGE_SELF)
    return {'rss_kib': status.get('VmRSS'), 'vsz_kib': status.get('VmSize'),
            'threads': status.get('Threads'), 'meminfo_kib': mem, 'io': io,
            'minor_faults': r.ru_minflt, 'major_faults': r.ru_majflt}


def delta(a, b, key):
    return b.get(key, 0) - a.get(key, 0)


def execute(args):
    start_state = proc_sample()
    started = time.perf_counter()
    result = {'case': args.case, 'mode': args.mode, 'documents': args.documents,
              'consumers': args.consumers, 'cache_capacity': args.cache_capacity,
              'unique_queries': args.unique_queries, 'context_bytes': args.context_bytes,
              'queue_capacity': args.queue_capacity, 'repeat': args.repeat}
    if args.case in ('C1', 'C2', 'C5'):
        path = ROOT / f'data/generated/benchmark_{args.documents}_index.jsonl'
        if not path.exists():
            raise FileNotFoundError(f'Índice não encontrado: {path}. Execute run_benchmarks.py primeiro.')
        reader = read_standard if args.case != 'C2' else read_mapped
        # mede primeira e segunda leitura dentro do mesmo processo; cache de páginas do SO pode já estar quente
        durations = []
        checksums = []
        for _ in range(2):
            t0 = time.perf_counter()
            data = reader(path)
            durations.append((time.perf_counter() - t0) * 1000)
            checksums.append((len(data), data[:32] == data[:32]))
        result.update({'read_ms_first': durations[0], 'read_ms_second': durations[1],
                       'bytes_read_logical': sum(x[0] for x in checksums),
                       'index_bytes': path.stat().st_size,
                       'reader': 'mmap_slice_copy' if args.case == 'C2' else 'read_all'})
        if args.case == 'C5':
            # Retém bytes e objetos JSON para demonstrar pressão moderada sem alocar memória descontrolada.
            records = [json.loads(line) for line in data.splitlines() if line]
            result['records_loaded'] = len(records)
            result['retained_bytes'] = len(data)
    elif args.case in ('C3', 'C4'):
        path = ROOT / f'data/generated/benchmark_{args.documents}_index.jsonl'
        retriever = Retriever(path, args.mode)
        service = GenResearchService(retriever, args.cache_capacity, args.response_ms, 3, args.context_bytes)
        terms = ['memoria swap', 'armazenamento mmap', 'threads mutex', 'rag contexto',
                 'fila consumidores', 'cache', 'pagina']
        pool = [f'{terms[i % len(terms)]} consulta{i}' for i in range(args.unique_queries)]
        queries = [pool[i % len(pool)] for i in range(args.requests)]
        pipeline = run_pipeline(queries, producers=2, consumers=args.consumers,
                                queue_capacity=args.queue_capacity, handler=service.query)
        timings = sorted(x['total_ms'] for x in pipeline['results'])
        def percentile(p):
            if not timings: return None
            idx = (len(timings)-1)*p
            lo, hi = int(idx), min(int(idx)+1, len(timings)-1)
            return timings[lo] + (timings[hi]-timings[lo])*(idx-lo)
        cache = service.cache.stats()
        result.update({'pipeline': {k:v for k,v in pipeline.items() if k != 'results'},
                       'cache': cache, 'hit_rate': cache['hits']/max(1,args.requests),
                       'latency_mean_ms': sum(timings)/len(timings) if timings else None,
                       'latency_median_ms': percentile(.5), 'latency_p95_ms': percentile(.95),
                       'retrieval_mean_ms_misses': (sum(x['retrieval_ms'] for x in service.records if not x['cache_hit']) /
                                                     max(1, sum(not x['cache_hit'] for x in service.records))),
                       'response_mean_ms_misses': (sum(x['response_ms'] for x in service.records if not x['cache_hit']) /
                                                    max(1, sum(not x['cache_hit'] for x in service.records))),
                       'context_bytes_mean': sum(x['context_bytes'] for x in service.records)/max(1,len(service.records)),
                       'queue_wait_mean_ms': sum(x['queue_wait_ms'] for x in pipeline['results'])/max(1,len(timings))})
    elif args.case == 'C6':
        missing = ROOT / 'data/generated/arquivo_inexistente_av2.jsonl'
        try:
            Retriever(missing, 'standard')
        except FileNotFoundError as exc:
            result['missing_index_handled'] = True
            result['exception'] = type(exc).__name__
        else:
            raise AssertionError('Falha não foi detectada')
        pipeline = run_pipeline(['teste']*12, producers=2, consumers=2,
                                queue_capacity=1, processing_ms=8)
        result['saturation'] = {k:v for k,v in pipeline.items() if k != 'results'}
        assert pipeline['lost'] == 0 and pipeline['duplicate_ids'] == 0
    else:
        raise ValueError(args.case)
    end_state = proc_sample()
    result.update({'elapsed_ms': (time.perf_counter()-started)*1000,
                   'timestamp_utc': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                   'process': {'rss_kib_start':start_state['rss_kib'], 'rss_kib_end':end_state['rss_kib'],
                               'vsz_kib_start':start_state['vsz_kib'], 'vsz_kib_end':end_state['vsz_kib'],
                               'threads_end':end_state['threads'],
                               'minor_faults_delta':delta(start_state,end_state,'minor_faults'),
                               'major_faults_delta':delta(start_state,end_state,'major_faults'),
                               'io_delta':{k:end_state['io'].get(k,0)-start_state['io'].get(k,0)
                                           for k in end_state['io']},
                               'meminfo_start_kib':start_state['meminfo_kib'],
                               'meminfo_end_kib':end_state['meminfo_kib']}})
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--case', required=True, choices=['C1','C2','C3','C4','C5','C6'])
    p.add_argument('--mode', default='standard', choices=['standard','mmap'])
    p.add_argument('--documents', type=int, default=120)
    p.add_argument('--consumers', type=int, default=2)
    p.add_argument('--cache-capacity', type=int, default=8)
    p.add_argument('--unique-queries', type=int, default=5)
    p.add_argument('--context-bytes', type=int, default=2048)
    p.add_argument('--queue-capacity', type=int, default=8)
    p.add_argument('--requests', type=int, default=40)
    p.add_argument('--response-ms', type=float, default=20)
    p.add_argument('--repeat', type=int, default=1)
    a=p.parse_args()
    print(json.dumps(execute(a), ensure_ascii=False))
