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

## Status

Etapa 1: estrutura e ambiente. Nenhum resultado experimental coletado ainda.
