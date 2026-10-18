#!/usr/bin/env bash
set -euo pipefail
mkdir -p results/raw
{
  echo "Data UTC: $(date -u +%FT%TZ)"
  echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || echo ainda-sem-commit)"
  echo '=== Python ==='; python3 --version
  echo '=== Kernel ==='; uname -a
  echo '=== Distro ==='; cat /etc/os-release
  echo '=== CPU ==='; lscpu
  echo '=== Memória ==='; free -h
  echo '=== Swap ==='; swapon --show
  echo '=== Meminfo ==='; cat /proc/meminfo
  echo '=== Discos ==='; lsblk
  echo '=== Filesystems ==='; df -h
} > results/raw/environment.txt
printf 'Criado: results/raw/environment.txt\nRevise identificadores pessoais antes de publicar.\n'
