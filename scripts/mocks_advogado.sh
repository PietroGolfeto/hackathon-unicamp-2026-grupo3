#!/usr/bin/env bash
# Monta os casos da tela do advogado a partir de data/mock-para-tela-advogado/.
#
# Cada Caso_NN/ é uma pasta plana de PDFs; o ingest espera
# data/exemplos/<numero-cnj>/{autos,subsidios}/. O número sai do nome do arquivo de autos.
# O terceiro caso é derivado do primeiro sem o extrato: mesmo autor, mesma UF, só o acervo de
# subsídios muda. Tirar só o extrato deixa o caso na zona intermediária, onde vale a pena pedir o
# documento antes de acordar; tirar contrato e extrato juntos faria dele um clone do segundo caso.
set -euo pipefail

ORIGEM="${ORIGEM:-data/mock-para-tela-advogado}"
DESTINO="${DESTINO:-data/exemplos}"
DERIVADO_NUMERO="${DERIVADO_NUMERO:-0801235-56.2024.8.10.0001}"
DERIVADO_DE="${DERIVADO_DE:-Caso_01}"
# subsídio que o caso derivado não tem
DERIVADO_SEM='extrato'

[ -d "$ORIGEM" ] || { echo "erro: $ORIGEM não existe (PDFs da Enter não são versionados)" >&2; exit 1; }

e_autos() { case "$(basename "$1")" in *Autos*|*autos*|*Peticao*|*peticao*) return 0;; *) return 1;; esac; }

# Número CNJ a partir do nome do arquivo de autos (0801234-56-2024-8-10-0001 -> pontuado).
numero_do_caso() {
  local pasta="$1" f
  for f in "$pasta"/*; do
    e_autos "$f" || continue
    basename "$f" | sed -nE 's/.*([0-9]{7})-([0-9]{2})-([0-9]{4})-([0-9])-([0-9]{2})-([0-9]{4}).*/\1-\2.\3.\4.\5.\6/p'
    return
  done
}

# copiar <pasta-origem> <numero> [regex-de-subsidio-a-pular]
copiar() {
  local pasta="$1" numero="$2" pular="${3:-}" alvo="$DESTINO/$2" f base
  rm -rf "$alvo"
  mkdir -p "$alvo/autos" "$alvo/subsidios"
  for f in "$pasta"/*; do
    [ -f "$f" ] || continue
    base=$(basename "$f")
    if e_autos "$f"; then
      cp "$f" "$alvo/autos/"
    elif [ -z "$pular" ] || ! echo "$base" | grep -qiE "$pular"; then
      cp "$f" "$alvo/subsidios/"
    fi
  done
  echo "→ $alvo ($(ls "$alvo/autos" | wc -l) autos, $(ls "$alvo/subsidios" | wc -l) subsídios)"
}

for pasta in "$ORIGEM"/*/; do
  [ -d "$pasta" ] || continue
  numero=$(numero_do_caso "$pasta")
  [ -n "$numero" ] || { echo "aviso: sem número CNJ no nome dos autos de $pasta; pulando" >&2; continue; }
  copiar "$pasta" "$numero"
done

derivado="$ORIGEM/$DERIVADO_DE"
if [ -d "$derivado" ]; then
  copiar "$derivado" "$DERIVADO_NUMERO" "$DERIVADO_SEM"
  echo "  (derivado de $DERIVADO_DE sem o extrato)"
else
  echo "aviso: $derivado não existe; caso derivado não foi criado" >&2
fi
