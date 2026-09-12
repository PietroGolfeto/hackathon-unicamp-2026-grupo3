#!/usr/bin/env bash
# Valida todos os commits de um intervalo: mensagem (check_commit_msg.sh) e
# tamanho (blast radius). Uso: check_commits.sh [base] [head]
# Base vazia, inexistente ou só zeros (push de branch nova) cai em head~1.
set -euo pipefail

aqui="$(cd "$(dirname "$0")" && pwd)"
base="${1:-origin/main}"
head="${2:-HEAD}"
max_arquivos=20
max_linhas=800
ignorar='(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|uv\.lock|\.csv|\.svg|\.png|\.jpg|\.jpeg|\.pdf|\.ico)$'

if [[ -z "$base" || "$base" =~ ^0+$ ]] || ! git rev-parse -q --verify "$base^{commit}" >/dev/null; then
  base="$(git rev-parse -q --verify "$head~1" 2>/dev/null || true)"
fi
if [[ -z "$base" ]]; then
  echo "sem base para comparar; nada a verificar"
  exit 0
fi

commits="$(git rev-list --no-merges --reverse "$base..$head")"
if [[ -z "$commits" ]]; then
  echo "nenhum commit novo em $base..$head"
  exit 0
fi

erros=0
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

for sha in $commits; do
  curto="$(git log -1 --format=%h "$sha")"
  assunto="$(git log -1 --format=%s "$sha")"
  echo "→ $curto $assunto"

  git log -1 --format=%B "$sha" > "$tmp"
  if ! "$aqui/check_commit_msg.sh" "$tmp"; then erros=1; fi

  stats="$(git show --numstat --format= "$sha" | grep -vE "$ignorar" || true)"
  arquivos="$(printf '%s\n' "$stats" | grep -c . || true)"
  linhas="$(printf '%s\n' "$stats" | awk '{ a += ($1 == "-" ? 0 : $1); d += ($2 == "-" ? 0 : $2) } END { print a + d + 0 }')"

  if [[ "$assunto" != *"[grande]"* ]]; then
    if (( arquivos > max_arquivos )); then
      echo "✗ $curto toca $arquivos arquivos (máximo $max_arquivos). Divida o commit ou justifique com [grande] no assunto"
      erros=1
    fi
    if (( linhas > max_linhas )); then
      echo "✗ $curto altera $linhas linhas (máximo $max_linhas). Divida o commit ou justifique com [grande] no assunto"
      erros=1
    fi
  fi
done

if (( erros )); then
  echo
  echo "commits fora das regras. Veja CLAUDE.md, seção 'Regras de colaboração'."
  exit 1
fi
echo "✓ commits ok"
