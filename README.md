# GenResearch-Servidor — Sistemas Operacionais AV2 (2026.2)

Projeto individual de observação de memória, armazenamento, sincronização e desempenho em um pipeline simplificado de recuperação e geração.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
bash scripts/collect_environment.sh
```

## Organização

- `src/genresearch`: aplicação (implementação incremental)
- `data/synthetic`: corpus sintético
- `experiments/configs`: configurações dos experimentos
- `results/raw`, `results/metrics`, `results/plots`: evidências e resultados
- `docs/roteiro_apresentacao.md`: roteiro incremental da apresentação

## Etapa 2 — Ingestão e armazenamento

```bash
python scripts/run_ingestion.py --documents 120 --mode standard
python scripts/run_ingestion.py --documents 120 --mode mmap
python -m unittest discover -s tests -v
```

A ingestão gera um corpus JSONL sintético e um índice JSONL com fragmentos e vetores simulados determinísticos. Os leitores `standard` e `mmap` são equivalentes em conteúdo. **Não há resultados de benchmark C1/C2 nesta etapa.** `mmap[:]` copia o arquivo inteiro, portanto não representa ainda um acesso incremental zero-copy.

## Status

Etapas 1 e 2: estrutura, ambiente, ingestão e armazenamento. Próximas: fila, trabalhadores e experimentos.

