# AV2 — Roteiro incremental de apresentação

> Documento de apoio à apresentação oral (10–12 minutos). Atualizar ao final de cada etapa; não substitui o relatório técnico de 8–12 páginas.

## Etapa 1 — Setup e ambiente

**O que falar (20–30 segundos):**
O GenResearch-Servidor é uma aplicação experimental individual em Python executada em Linux (WSL2). Seu objetivo é observar como memória, armazenamento, filas, sincronização e cache influenciam desempenho e correção de um pipeline simplificado de recuperação e geração. Escolhemos dados sintéticos e processamento simulado para controlar as variáveis, conforme permitido pelo enunciado.

**O que mostrar:**
- Árvore do repositório, destacando `src/`, `experiments/`, `results/` e `docs/`.
- Saída real de `python3 --version`, `uname -a`, `free -h`, `swapon --show` e `df -h`.
- Commit inicial no GitHub e instruções de reprodução no README.

**Evidências a coletar:**
- `results/raw/environment.txt` (sem segredos nem identificadores desnecessários).
- Versão de Python, distribuição/kernel, RAM/swap, sistema de arquivos e commit Git.

**Ainda não afirmar:** resultados de benchmarks, desempenho de mmap, eficácia de cache ou ausência de condições de corrida. Isso só será conhecido após executar os experimentos.

## Etapa 2 — Ingestão e armazenamento

**O que falar (40–50 segundos):**
O pipeline recebe documentos sintéticos em JSONL, fragmenta textos em trechos com sobreposição configurável, produz vetores simulados determinísticos e grava um índice persistente em JSONL. A simulação permite experimentos controlados sem o custo de um modelo real; não constitui recuperação semântica de qualidade. Dois leitores oferecem leitura convencional (`read`) e mapeamento de arquivo (`mmap`), com a mesma saída lógica. Não afirmar superioridade de desempenho sem benchmarks.

**O que mostrar:**
- `src/genresearch/ingestion/pipeline.py`: geração, fragmentação e vetorização.
- `src/genresearch/storage/readers.py`: `read_standard` versus `read_mapped`.
- `python scripts/run_ingestion.py --documents 120` e o resumo com contagens e bytes reais.
- `python -m unittest discover -s tests -v` e equivalência dos leitores.

**Evidências:**
- Resumo da ingestão (documentos, trechos, tamanho do corpus/índice).
- Testes automatizados e commit da etapa.

**Limitação:** `mmap[:]` copia os dados para `bytes`; a comparação futura deverá explicitar essa escolha e, se necessário, comparar acesso incremental sem cópia. C1/C2 ainda não foram medidos.


## Etapa 3 — Fila e trabalhadores
_A preencher após implementação e testes._

## Etapa 4 — Recuperação, processamento e cache
_A preencher após implementação e testes._

## Etapa 5 — Sincronização e falha controlada
_A preencher após implementação e testes._

## Etapa 6 — Experimentos C1–C6 e métricas
_A preencher com números reais, tabelas e gráficos._

## Etapa 7 — Conclusões e limites
_A preencher após análise._

## Checklist da apresentação
- [ ] Problema e cenário
- [ ] Ambiente e arquitetura
- [ ] Dados e configurações
- [ ] Processos, filas e recursos
- [ ] Experimentos e gráficos
- [ ] Sincronização e falha controlada
- [ ] Memória, armazenamento e E/S
- [ ] Relação com IA generativa e limitações
- [ ] Ensaiar para 10–12 minutos, reservar 3–5 para perguntas
