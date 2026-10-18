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


## Etapa 3 — Fila limitada e trabalhadores concorrentes

**O que falar (40–50 segundos):** implementamos o padrão produtores-consumidores com `queue.Queue(maxsize=N)`, dois produtores e dois consumidores por padrão. A fila usa sincronização interna e bloqueia produtores quando está cheia. Cada requisição tem ID único; medimos espera na fila, processamento, latência total, vazão e duplicações/perdas. `task_done()` e sentinelas garantem encerramento coordenado após os produtores terminarem.

**O que mostrar:** `src/genresearch/concurrency/workers.py`, saída de `python scripts/run_concurrency.py --requests 40 --producers 2 --consumers 2 --queue-capacity 4` e `results/raw/concurrency.json`. Comparar depois 1, 2 e 4 consumidores, sem afirmar aceleração antes das medições.

**Limitações:** o custo inicial é simulado com `sleep`, representando espera/I/O, não carga intensiva de CPU; não há ainda recuperação real nem cache. O pico de fila é amostrado, não uma série temporal completa. Falha controlada de sincronização será demonstrada na etapa do cache.


## Etapa 4 — Recuperação, processamento e cache

**O que falar (50–60 segundos):** a fila da etapa 3 agora chama um serviço de recuperação real sobre o índice JSONL gerado na etapa 2. A busca é lexical (sobreposição de termos), não semântica; respeita `top_k` e limite de bytes de contexto. A resposta é simulada por uma espera configurável, sem inferência de LLM. Um cache LRU compartilhado armazena respostas e métricas; são registrados hits, misses, evicções e tempo estimado economizado.

**O que mostrar:** `retrieval/search.py`, `cache/lru.py`, `processing/service.py`; executar `scripts/run_service.py` com consultas repetidas e depois com cache pequeno para observar evicções. Mostrar `results/raw/service.json` e métricas de cache e contexto.

**Sincronização e limite:** o cache protege check-compute-store com `threading.Lock`, evitando cálculos duplicados, mas serializando misses diferentes; a etapa 5 comparará com uma implementação insegura. `estimated_saved_ms` é soma de custos históricos evitados, não ganho líquido medido. Latência em hits pode incluir espera pelo lock. Consultas lexicais simuladas não demonstram qualidade de embeddings.


## Etapa 5 — Sincronização e falha controlada

**O que falar (60–75 segundos):** o cache faz `check → compute → store`, uma sequência não atômica. Em uma versão propositalmente insegura, várias threads observam simultaneamente um miss para a mesma chave e calculam a resposta repetidamente (*cache stampede*). O lock global da etapa 4 evita duplicação, mas também serializa chaves distintas. A terceira versão aplica um lock por chave com dupla verificação (*double-check*): a mesma chave só é calculada uma vez, e chaves diferentes podem avançar em paralelo.

**O que mostrar:** `src/genresearch/cache/race_demo.py`, especialmente o atraso controlado após o miss e o `double-check`; executar `python scripts/run_race_demo.py --workers 8 --compute-ms 40 --repetitions 3`; mostrar `results/raw/race_demo.json` com `compute_calls_per_run`, hits e tempo médio dos cenários `same` e `distinct`.

**Evidências:** três repetições por configuração; testes demonstrando cálculos duplicados no modo inseguro e um único cálculo nos modos protegidos; gráfico do tempo médio por modo. Não afirmar que `sleep` representa paralelismo de CPU ou inferência real. Os números e conclusões quantitativas só entram após rodar no WSL.

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

