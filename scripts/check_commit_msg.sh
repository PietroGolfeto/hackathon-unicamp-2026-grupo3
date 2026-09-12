#!/usr/bin/env bash
# Valida UMA mensagem de commit (caminho do arquivo como argumento).
# Regras: assunto "<area>(escopo opcional): <tl;dr>" com até 72 caracteres,
# sem trailers ou frases de atribuição a IA. Linhas começando com # são ignoradas.
set -euo pipefail

arquivo="${1:?uso: check_commit_msg.sh <arquivo-da-mensagem>}"
areas='api|web|core|model|extractor|infra|docs|ci|chore|data|scripts'
padrao="^($areas)(\([a-z0-9._/-]+\))?: [^[:space:]].{4,}$"

mensagem="$(grep -v '^#' "$arquivo" || true)"
assunto="$(printf '%s\n' "$mensagem" | sed -n '1p')"
erros=0

if [[ ! "$assunto" =~ $padrao ]]; then
  echo "✗ assunto fora do padrão '<area>: <tl;dr>' (áreas: ${areas//|/, })"
  echo "  recebido: '$assunto'"
  erros=1
fi

if (( ${#assunto} > 72 )); then
  echo "✗ assunto com ${#assunto} caracteres (máximo 72)"
  erros=1
fi

if printf '%s\n' "$mensagem" | grep -qiE '^co-authored-by:.*(claude|anthropic|openai|chatgpt|gpt|copilot|gemini|cursor|codex|noreply@)|generated (with|by) .*(claude|copilot|chatgpt|gpt|gemini|cursor|codex)|🤖'; then
  echo "✗ mensagem contém atribuição a IA; remova trailers e frases do tipo"
  erros=1
fi

if (( erros )); then
  cat <<'EXEMPLO'

exemplo válido:
  api: grava recomendação ao abrir o caso, sob a política ativa

  A decisão do advogado passa a apontar para a recomendação que ele viu.
EXEMPLO
  exit 1
fi
