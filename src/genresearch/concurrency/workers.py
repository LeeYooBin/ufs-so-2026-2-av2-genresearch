"""Fila limitada, produtores e consumidores com encerramento coordenado."""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import asdict, dataclass
from typing import Callable


@dataclass(frozen=True)
class Request:
    request_id: int
    query: str


@dataclass
class Result:
    request_id: int
    worker: str
    queue_wait_ms: float
    processing_ms: float
    total_ms: float
    status: str


def run_pipeline(queries: list[str], producers: int = 2, consumers: int = 2,
                 queue_capacity: int = 8, processing_ms: float = 10,
                 handler: Callable[[str], object] | None = None) -> dict:
    if producers < 1 or consumers < 1 or queue_capacity < 1 or processing_ms < 0:
        raise ValueError('produtores, consumidores e capacidade devem ser positivos; custo >= 0')
    tasks: queue.Queue[tuple[Request, float] | None] = queue.Queue(maxsize=queue_capacity)
    records: list[Result] = []
    errors: list[str] = []
    lock = threading.Lock()
    start = time.perf_counter()
    maximum_queue = 0
    put_waits: list[float] = []
    queue_samples: list[int] = []
    busy_ms: dict[str, float] = {f"consumer-{i}": 0.0 for i in range(consumers)}
    handler = handler or (lambda query: time.sleep(processing_ms / 1000))

    def producer(pid: int) -> None:
        nonlocal maximum_queue
        for idx in range(pid, len(queries), producers):
            before = time.perf_counter()
            tasks.put((Request(idx, queries[idx]), before))
            waited = (time.perf_counter() - before) * 1000
            with lock:
                put_waits.append(waited)
                depth = tasks.qsize()
                queue_samples.append(depth)
                maximum_queue = max(maximum_queue, depth)

    def consumer(cid: int) -> None:
        while True:
            item = tasks.get()
            try:
                if item is None:
                    return
                req, enqueued_at = item
                processing_start = time.perf_counter()
                status = 'ok'
                try:
                    handler(req.query)
                except Exception as exc:
                    status = 'error'
                    with lock:
                        errors.append(f'{req.request_id}: {type(exc).__name__}: {exc}')
                completed_at = time.perf_counter()
                result = Result(req.request_id, f'consumer-{cid}',
                                (processing_start - enqueued_at) * 1000,
                                (completed_at - processing_start) * 1000,
                                (completed_at - enqueued_at) * 1000, status)
                with lock:
                    records.append(result)
                    busy_ms[f"consumer-{cid}"] += result.processing_ms
            finally:
                tasks.task_done()

    workers = [threading.Thread(target=consumer, args=(i,), name=f'consumer-{i}') for i in range(consumers)]
    senders = [threading.Thread(target=producer, args=(i,), name=f'producer-{i}') for i in range(producers)]
    for t in workers + senders:
        t.start()
    for t in senders:
        t.join()
    for _ in workers:
        tasks.put(None)
    tasks.join()
    for t in workers:
        t.join()
    elapsed = time.perf_counter() - start
    records.sort(key=lambda r: r.request_id)
    ids = [r.request_id for r in records]
    return {
        'producers': producers, 'consumers': consumers, 'queue_capacity': queue_capacity,
        'submitted': len(queries), 'completed': len(records),
        'lost': len(set(range(len(queries))) - set(ids)),
        'duplicate_ids': len(ids) - len(set(ids)), 'errors': errors,
        'max_queue_observed': maximum_queue,
        'mean_queue_observed_at_put': sum(queue_samples) / len(queue_samples) if queue_samples else 0,
        'worker_processing_fraction': {name: round(ms / (elapsed * 1000), 6) if elapsed else 0
                                       for name, ms in busy_ms.items()},
        'mean_producer_block_ms': sum(put_waits) / len(put_waits) if put_waits else 0,
        'elapsed_ms': elapsed * 1000,
        'throughput_req_s': len(records) / elapsed if elapsed else 0,
        'results': [asdict(r) for r in records],
    }
