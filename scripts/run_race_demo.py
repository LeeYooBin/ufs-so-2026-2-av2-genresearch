"""Experimento reprodutível de sincronização. Execução: python scripts/run_race_demo.py"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import sys
from threading import Barrier, Lock
from time import perf_counter, sleep

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genresearch.cache.lru import SharedLRU
from genresearch.cache.race_demo import UnsafeLRU, KeyedLRU


def trial(mode, workload, workers, compute_ms, capacity, miss_delay_ms):
    cache = {'unsafe': lambda: UnsafeLRU(capacity, miss_delay_ms),
             'global': lambda: SharedLRU(capacity),
             'keyed': lambda: KeyedLRU(capacity)}[mode]()
    barrier = Barrier(workers)
    counter_lock = Lock()
    computations = [0]
    keys = ['consulta-repetida'] * workers if workload == 'same' else [f'consulta-{i}' for i in range(workers)]

    def run(key):
        barrier.wait(timeout=10)
        def compute():
            with counter_lock:
                computations[0] += 1
            sleep(compute_ms / 1000)  # espera simulada: não representa CPU intensiva
            return 'resposta:' + key
        value, hit = cache.get_or_compute(key, compute)
        if value != 'resposta:' + key:
            raise AssertionError('resposta incorreta')
        return hit

    started = perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        hits = list(executor.map(run, keys))
    elapsed_ms = (perf_counter() - started) * 1000
    return {'mode': mode, 'workload': workload, 'workers': workers,
            'elapsed_ms': round(elapsed_ms, 3), 'compute_calls': computations[0],
            'hits_observed': sum(hits), 'cache': cache.stats(), 'correct_answers': workers}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--compute-ms', type=float, default=40)
    p.add_argument('--miss-delay-ms', type=float, default=10)
    p.add_argument('--repetitions', type=int, default=3)
    p.add_argument('--output', default='results/raw/race_demo.json')
    a = p.parse_args()
    if a.workers < 2 or a.compute_ms < 0 or a.miss_delay_ms < 0 or a.repetitions < 1:
        p.error('workers >= 2, tempos >= 0 e repetitions >= 1')
    runs = [trial(mode, workload, a.workers, a.compute_ms, a.workers, a.miss_delay_ms)
            for workload in ('same', 'distinct')
            for mode in ('unsafe', 'global', 'keyed')
            for _ in range(a.repetitions)]
    summary = []
    for workload in ('same', 'distinct'):
        for mode in ('unsafe', 'global', 'keyed'):
            group = [r for r in runs if r['mode'] == mode and r['workload'] == workload]
            summary.append({'workload': workload, 'mode': mode,
                            'mean_elapsed_ms': round(statistics.mean(r['elapsed_ms'] for r in group), 3),
                            'median_elapsed_ms': round(statistics.median(r['elapsed_ms'] for r in group), 3),
                            'compute_calls_per_run': [r['compute_calls'] for r in group],
                            'hits_per_run': [r['hits_observed'] for r in group]})
    output = ROOT / a.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'configuration': vars(a), 'summary': summary, 'runs': runs}, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('Detalhes:', output)

if __name__ == '__main__':
    main()
