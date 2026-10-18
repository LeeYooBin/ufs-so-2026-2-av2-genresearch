import mmap
from pathlib import Path

def read_standard(path: Path) -> bytes:
    with path.open('rb') as file:
        return file.read()

def read_mapped(path: Path) -> bytes:
    with path.open('rb') as file:
        if path.stat().st_size == 0:
            return b''
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
            return mapped[:]

def iter_records(path: Path, mode: str = 'standard'):
    if mode not in ('standard', 'mmap'):
        raise ValueError('mode deve ser standard ou mmap')
    # Mesma saída lógica; a comparação de desempenho será feita na etapa experimental.
    import json
    raw = read_standard(path) if mode == 'standard' else read_mapped(path)
    for line in raw.splitlines():
        if line:
            yield json.loads(line)
