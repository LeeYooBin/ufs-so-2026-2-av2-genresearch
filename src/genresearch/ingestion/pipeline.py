import hashlib
import json
import random
from pathlib import Path

TOPICS = {
    "memoria": "RAM paginação swap cache páginas alocação processo",
    "armazenamento": "arquivo disco índice leitura escrita blocos mmap",
    "concorrencia": "threads mutex semáforo fila produtores consumidores",
    "rag": "documentos fragmentos vetores contexto recuperação resposta",
}

def generate_corpus(path: Path, count: int = 120, seed: int = 42) -> None:
    if count < 1:
        raise ValueError("count deve ser positivo")
    rng = random.Random(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for i in range(count):
            topic = list(TOPICS)[i % len(TOPICS)]
            terms = TOPICS[topic].split()
            content = ' '.join(rng.choice(terms) for _ in range(110))
            f.write(json.dumps({'id': f'doc-{i:05d}', 'topic': topic, 'text': content}, ensure_ascii=False) + '\n')

def chunk_text(text: str, size: int = 40, overlap: int = 8) -> list[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError('size deve ser positivo e 0 <= overlap < size')
    words = text.split()
    step = size - overlap
    return [' '.join(words[i:i+size]) for i in range(0, len(words), step) if words[i:i+size]]

def simulated_vector(text: str, dimensions: int = 16) -> list[float]:
    if dimensions < 1:
        raise ValueError('dimensions deve ser positivo')
    result = []
    for i in range(dimensions):
        digest = hashlib.sha256(f'{i}:{text}'.encode('utf-8')).digest()
        result.append(round(int.from_bytes(digest[:4], 'big') / 4294967295, 8))
    return result

def ingest(corpus: Path, index: Path, size: int = 40, overlap: int = 8) -> dict:
    index.parent.mkdir(parents=True, exist_ok=True)
    documents = chunks = 0
    with corpus.open('r', encoding='utf-8') as source, index.open('w', encoding='utf-8') as target:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            doc = json.loads(line)
            if not all(k in doc for k in ('id', 'topic', 'text')):
                raise ValueError(f'Documento inválido na linha {line_number}')
            documents += 1
            for chunk_number, chunk in enumerate(chunk_text(doc['text'], size, overlap)):
                record = {'document_id': doc['id'], 'topic': doc['topic'], 'chunk_id': chunk_number,
                          'text': chunk, 'vector': simulated_vector(chunk)}
                target.write(json.dumps(record, ensure_ascii=False) + '\n')
                chunks += 1
    return {'documents': documents, 'chunks': chunks, 'corpus_bytes': corpus.stat().st_size,
            'index_bytes': index.stat().st_size}
