"""Recuperação lexical determinística sobre índice JSONL (não semântica)."""
import re
from pathlib import Path
from genresearch.storage.readers import iter_records


def tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold()))


class Retriever:
    def __init__(self, index_path: Path, mode: str = 'standard'):
        self.records = list(iter_records(index_path, mode))

    def search(self, query: str, top_k: int = 3, max_context_bytes: int = 2048) -> dict:
        if top_k < 1 or max_context_bytes < 1:
            raise ValueError('top_k e max_context_bytes devem ser positivos')
        terms = tokens(query)
        ranked = sorted(self.records, key=lambda r: (-len(terms & tokens(r['text'])), r['document_id'], r['chunk_id']))
        chunks = []
        used = 0
        for record in ranked:
            score = len(terms & tokens(record['text']))
            if score == 0:
                break
            size = len(record['text'].encode('utf-8'))
            if used + size > max_context_bytes:
                continue
            chunks.append({'document_id': record['document_id'], 'chunk_id': record['chunk_id'], 'score': score, 'text': record['text']})
            used += size
            if len(chunks) >= top_k:
                break
        return {'chunks': chunks, 'chunk_count': len(chunks), 'context_bytes': used, 'approx_tokens': used // 4}
