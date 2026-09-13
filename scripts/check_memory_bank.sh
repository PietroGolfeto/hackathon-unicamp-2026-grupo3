#!/usr/bin/env bash
# Regra: mudança que toca código (src/ ou infra/) precisa tocar memory-bank/*.md.
# Uso: check_memory_bank.sh --staged          (cada commit, via hook)
#      check_memory_bank.sh [base] [head]     (CI: o conjunto das mudanças de base...head)
# Na CI o que importa é o PR (ou o push) chegar com o memory-bank atualizado. Checar commit a commit
# tornaria impossível passar uma branch de integração com merges de várias pessoas, porque commit
# antigo não se reescreve. O hook continua cobrando em cada commit na origem.
set -euo pipefail

codigo='^(src|infra)/'
memoria='^memory-bank/.*\.md$'

verifica() {
  local rotulo="$1" arquivos
  arquivos="$(cat)"
  if grep -qE "$codigo" <<<"$arquivos" && ! grep -qE "$memoria" <<<"$arquivos"; then
    echo "✗ $rotulo toca código sem atualizar memory-bank/"
    echo "  edite ao menos arquitetura.md ou features.md junto com o código (ver memory-bank/README.md)"
    return 1
  fi
  return 0
}

if [[ "${1:-}" == "--staged" ]]; then
  if git diff --cached --name-only | verifica "o commit em preparação"; then
    echo "✓ memory-bank ok"
    exit 0
  fi
  exit 1
fi

base="${1:-origin/main}"
head="${2:-HEAD}"
if [[ -z "$base" || "$base" =~ ^0+$ ]] || ! git rev-parse -q --verify "$base^{commit}" >/dev/null; then
  base="$(git rev-parse -q --verify "$head~1" 2>/dev/null || true)"
fi
if [[ -z "$base" ]]; then
  echo "sem base para comparar; nada a verificar"
  exit 0
fi

rotulo="o intervalo $(git rev-parse --short "$base")...$(git rev-parse --short "$head")"
if git diff --name-only "$base...$head" | verifica "$rotulo"; then
  echo "✓ memory-bank ok"
  exit 0
fi
exit 1
