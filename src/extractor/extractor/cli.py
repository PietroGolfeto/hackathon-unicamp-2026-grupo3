"""CLI: python -m extractor <pasta-do-processo> [--numero N] [--sem-llm] [--forcar] [--brief] [--sem-cache]

Roda o pipeline numa pasta (data/exemplos/<numero>/ com autos/ e subsidios/, ou uma pasta plana com os
PDFs) e imprime JSON. `--sem-llm` mostra o brief e os fatos sem gastar tokens. Lê o .env da raiz.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m extractor", description=__doc__.split("\n", 1)[1])
    parser.add_argument("pasta", type=Path, help="pasta do processo (autos/ e subsidios/, ou PDFs soltos)")
    parser.add_argument("--numero", help="número CNJ; padrão: deduzido do nome da pasta")
    parser.add_argument("--sem-llm", action="store_true", help="só leitura, segurança, parsing e brief")
    parser.add_argument("--forcar", action="store_true", help="ignora o cache e chama o LLM de novo")
    parser.add_argument("--sem-cache", action="store_true", help="não lê nem grava cache")
    parser.add_argument("--brief", action="store_true", help="inclui o texto do brief na saída")
    parser.add_argument("--cache-dir", type=Path, help="padrão: EXTRACTOR_CACHE_DIR ou DATA_DIR/cache/extractor")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr)
    load_dotenv()

    from extractor.cache import Cache
    from extractor.llm import ErroConfiguracao, ErroLLM
    from extractor.pipeline import Extrator

    if not args.pasta.is_dir():
        print(f"pasta não encontrada: {args.pasta}", file=sys.stderr)
        return 2
    cache = Cache(args.cache_dir, ativo=not args.sem_cache)
    try:
        extrator = Extrator(cache=cache) if not args.sem_llm else Extrator(cliente=_SemLLM(), cache=cache)
        if args.sem_llm:
            prep = extrator.preparar(args.pasta, args.numero)
            saida = {
                "numero": prep.numero, "uf": prep.uf, "brief_chars": len(prep.brief),
                "subsidios_presentes": prep.presentes, "subsidios_ausentes": prep.ausentes,
                "documentos": [_doc(d) for d in prep.docs],
                "achados": [a.__dict__ for a in prep.achados],
                "fatos": {d.arquivo: {k: v for k, v in d.fatos.items() if not k.startswith("_")} for d in prep.docs},
            }
            if args.brief:
                saida["brief"] = prep.brief
        else:
            res = extrator.processar(args.pasta, args.numero, forcar=args.forcar)
            saida = {
                "numero": res.numero, "cache_hit": res.cache_hit, "modelo": res.modelo,
                "tokens": {"entrada": res.tokens_entrada, "saida": res.tokens_saida, "cache": res.tokens_cache,
                           "raciocinio": res.tokens_raciocinio, "segundos": res.segundos},
                "brief_chars": len(res.brief), "documentos": [_doc(d) for d in res.docs],
                "achados": [a.__dict__ for a in res.achados],
                "dados": res.dados.model_dump(mode="json"), "analise": res.analise.model_dump(mode="json"),
                "saida_llm": res.saida_llm.model_dump(),
            }
            if args.brief:
                saida["brief"] = res.brief
    except ErroConfiguracao as exc:
        print(f"configuração: {exc}", file=sys.stderr)
        return 2
    except ErroLLM as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(saida, ensure_ascii=False, indent=2, default=str))
    return 0


def _doc(d) -> dict:
    return {"arquivo": d.arquivo, "pasta": d.pasta, "tipo": d.tipo, "paginas": d.paginas, "leitor": d.leitor,
            "chars": d.chars, "chars_brief": d.chars_brief, "erros": d.erros,
            "achados": sorted({a.codigo for a in d.achados})}


class _SemLLM:
    """Dublê que nunca é chamado: `--sem-llm` para em `preparar`."""

    modelo = "sem-llm"

    def completar(self, *_a, **_k):  # pragma: no cover
        raise RuntimeError("--sem-llm não chama o modelo")


if __name__ == "__main__":
    sys.exit(main())
