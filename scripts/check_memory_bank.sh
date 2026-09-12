#!/usr/bin/env bash
# Regra: commit que toca código (src/ ou infra/) precisa tocar memory-bank/*.md.
# Uso: check_memory_bank.sh --staged          (antes de commitar, via hook)
#      check_memory_bank.sh [base] [head]     (intervalo de commits, CI)
set -euo pipefail

codigo='^(src|infra)/'
memoria='^memory-bank/.*\.md$'

verifica() {
  local rotulo="$1" arquivos
  arquivos="$(cat)"
  if grep -qE "$codigo" <<<"$arquivos" && ! grep -qE "$memoria" <<<"$arquivos"; then
    echo "✗ $rotulo toca código sem atualizar memory-bank/"
    echo "  edite ao menos arquitetura.md ou features.md no mesmo commit (ver memory-bank/README.md)"
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

erros=0
for sha in $(git rev-list --no-merges --reverse "$base..$head"); do
  rotulo="$(git log -1 --format='%h %s' "$sha")"
  if ! git show --name-only --format= "$sha" | verifica "$rotulo"; then erros=1; fi
done

if (( erros )); then exit 1; fi
echo "✓ memory-bank ok"
