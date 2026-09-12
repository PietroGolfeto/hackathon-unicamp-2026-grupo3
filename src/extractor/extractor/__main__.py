"""CLI: `python -m extractor <arquivo.pdf | pasta do processo> [--modelo gpt-4o-mini] [--json]`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from openai import OpenAIError

from extractor.caso import resumir_caso
from extractor.leitura import ErroLeitura
from extractor.resumo import ErroResumo, ResumoDocumento, resumir_pdf


def _texto(r: ResumoDocumento) -> str:
    linhas = [f"# {r.arquivo}", f"{r.paginas} página(s) · PDF {r.tipo_pdf} · modelo {r.modelo}"]
    if r.paginas_ocr:
        linhas.append(f"OCR nas páginas: {', '.join(map(str, r.paginas_ocr))}")
    if r.paginas_sem_texto:
        linhas.append(f"Atenção: sem texto nas páginas {', '.join(map(str, r.paginas_sem_texto))}")
    if r.texto_truncado:
        linhas.append("Atenção: documento longo; só o início foi resumido.")
    linhas += ["", "## Resumo", r.resumo, "", "## Pontos principais"]
    linhas += [f"- {p}" for p in r.pontos_principais]
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m extractor",
        description="Resume um PDF ou monta a ficha do caso a partir da pasta do processo.",
    )
    parser.add_argument("caminho", help="arquivo PDF (resumo) ou pasta do processo (ficha do caso)")
    parser.add_argument("--modelo", help="modelo da OpenAI (padrão: OPENAI_MODEL ou gpt-4o-mini)")
    parser.add_argument("--json", action="store_true", help="imprime o resultado em JSON")
    args = parser.parse_args(argv)
    # fora do make, OPENAI_API_KEY e OPENAI_MODEL vêm do .env da raiz; o ambiente tem precedência
    load_dotenv(find_dotenv(usecwd=True))

    try:
        if Path(args.caminho).is_dir():
            ficha = resumir_caso(args.caminho, modelo=args.modelo)
            print(ficha.model_dump_json(indent=2) if args.json else ficha.texto())
        else:
            r = resumir_pdf(args.caminho, modelo=args.modelo)
            print(r.model_dump_json(indent=2) if args.json else _texto(r))
    except (ErroLeitura, ErroResumo) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    except OpenAIError as exc:
        print(f"erro na chamada à OpenAI: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
