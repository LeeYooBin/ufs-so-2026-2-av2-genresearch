#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="docs/evidencias/etapa6_os"
mkdir -p "$OUT"
{
  echo "Timestamp UTC: $(date -u +%FT%TZ)"
  echo "PWD: $PWD"
  echo '=== uname -a ==='; uname -a
  echo '=== /etc/os-release ==='; cat /etc/os-release
  echo '=== Python ==='; python --version
  echo '=== Git commit ==='; git rev-parse HEAD 2>/dev/null || true
  echo '=== df -T . ==='; df -T .
  echo '=== free -h ==='; free -h
  echo '=== nproc ==='; nproc
  echo '=== swap ==='; cat /proc/swaps
} > "$OUT/ambiente.txt"
INDEX='data/generated/benchmark_120_index.jsonl'
if [[ ! -s "$INDEX" ]]; then
  echo "Indice ausente: $INDEX. Execute antes o benchmark ou a ingestao." >&2
  exit 1
fi
python scripts/run_service.py \
  --index "$INDEX" --requests 80 --unique-queries 80 \
  --producers 2 --consumers 4 --queue-capacity 2 \
  --cache-capacity 1 --response-ms 70 \
  --output results/raw/os_evidence_service.json \
  > "$OUT/servico_stdout.txt" 2> "$OUT/servico_stderr.txt" &
PID=$!
cleanup() { if kill -0 "$PID" 2>/dev/null; then kill "$PID" 2>/dev/null || true; wait "$PID" 2>/dev/null || true; fi; }
trap cleanup EXIT
printf 'PID observado: %s\n' "$PID" > "$OUT/amostras.txt"
if command -v vmstat >/dev/null 2>&1; then
  vmstat 1 5 > "$OUT/vmstat.txt" &
  VM_PID=$!
else
  echo 'vmstat indisponivel' > "$OUT/vmstat.txt"
  VM_PID=''
fi
for i in $(seq 1 8); do
  if ! kill -0 "$PID" 2>/dev/null; then break; fi
  {
    echo "=== Amostra $i: $(date -u +%FT%TZ) ==="
    ps -p "$PID" -o pid,ppid,stat,nlwp,%cpu,%mem,rss,vsz,etime,comm || true
    ps -T -p "$PID" -o pid,tid,stat,%cpu,etime,comm || true
    grep -E '^(Name|State|Threads|VmRSS|VmSize|VmPeak|VmHWM|voluntary_ctxt_switches|nonvoluntary_ctxt_switches):' "/proc/$PID/status" 2>/dev/null || true
    echo
  } >> "$OUT/amostras.txt"
  sleep 0.5
done
wait "$PID"
STATUS=$?
trap - EXIT
if [[ -n "$VM_PID" ]]; then wait "$VM_PID" 2>/dev/null || true; fi
printf 'Exit code: %s\n' "$STATUS" >> "$OUT/amostras.txt"
python - <<'PY' > "$OUT/integridade.txt"
import json
from pathlib import Path
p=Path('results/raw/os_evidence_service.json')
r=json.loads(p.read_text())
for key in ('submitted','completed','lost','duplicate_ids','errors','max_queue_observed','throughput_req_s'):
    print(f'{key}: {r.get(key)}')
print('cache:', r.get('cache'))
assert r['submitted']==80 and r['completed']==80
assert r['lost']==0 and r['duplicate_ids']==0 and not r['errors']
PY
printf 'Coleta concluida. Evidencias: %s\n' "$OUT"
