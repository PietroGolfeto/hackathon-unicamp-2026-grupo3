#!/usr/bin/env bash
# Bloqueia arquivos que nunca devem ser versionados e padrões de chave em arquivos rastreados.
set -euo pipefail

erros=0
rastreados="$(git ls-files)"

proibidos="$(
  {
    printf '%s\n' "$rastreados" | grep -E '(^|/)\.env(\.[^/]+)?$' | grep -vE '\.env\.example$' || true
    printf '%s\n' "$rastreados" | grep -E '^data/[^/]+\.csv$|^data/(processos_exemplo|subsidios|policy_artifacts)/|\.(joblib|pkl|pickle|pt|bin|gguf|safetensors)$|(^|/)node_modules/' || true
  } | grep . || true
)"

if [[ -n "$proibidos" ]]; then
  echo "✗ arquivos que não podem ser versionados:"
  while IFS= read -r f; do echo "  $f"; done <<<"$proibidos"
  erros=1
fi

# Padrões de chave. Ignora binários, este script e lockfiles.
if git grep -nIE 'sk-(proj-|ant-)?[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,}' -- . ':!scripts/check_secrets.sh' ':!*.lock' ':!package-lock.json'; then
  echo "✗ padrão de segredo encontrado acima; remova do histórico e rotacione a chave"
  erros=1
fi

if (( erros )); then exit 1; fi
echo "✓ sem segredos nem dados versionados"
