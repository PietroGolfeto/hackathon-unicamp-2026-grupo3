"""Ingest das pastas data/exemplos/<numero>/{autos,subsidios}: upsert em processos por número.

Prefere arquivos de P1/P3 em data/derived/ (extraidos/<numero>.json, scores/<numero>.json);
senão chama extrator e modelo carregados. Nunca toca decisoes/recomendacoes.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

from core import cnj
from core.caso import CasoFeatures
from core.docs import DadosExtraidos, ExtratorDocs, subsidios_por_arquivos
from core.modelo import ModeloScores, Scores
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Processo

log = logging.getLogger(__name__)
VALOR_CAUSA_PADRAO = 15000.0  # mediana da base quando os autos não trazem o valor
SINAIS_GOLPE = {"BOLETIM_OCORRENCIA", "CREDITO_CONTA_TERCEIRO", "RECLAMACAO_BACEN"}


def listar_documentos(pasta: Path, data_dir: Path) -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for tipo in ("autos", "subsidios"):
        sub = pasta / tipo
        if not sub.is_dir():
            continue
        for arq in sorted(sub.iterdir()):
            if arq.is_file() and not arq.name.startswith("."):
                docs.append({"tipo": tipo, "arquivo": arq.name,
                             "caminho": str(arq.resolve().relative_to(data_dir.resolve()))})
    return docs


def _ler_derivado[M: BaseModel](caminho: Path, cls: type[M]) -> M | None:
    if not caminho.exists():
        return None
    try:
        return cls.model_validate_json(caminho.read_text(encoding="utf-8"))
    except ValueError as exc:
        log.warning("ignorando %s: %s", caminho, exc)
        return None


def ingerir_pasta(
    db: Session, pasta: Path, data_dir: Path, extrator: ExtratorDocs, modelo: ModeloScores,
    escritorio_id: int,
) -> Processo:
    numero = cnj.normalizar(pasta.name) or pasta.name
    docs = listar_documentos(pasta, data_dir)
    subs = subsidios_por_arquivos(d["arquivo"] for d in docs if d["tipo"] == "subsidios")
    derived = data_dir / "derived"
    dados = _ler_derivado(derived / "extraidos" / f"{numero}.json", DadosExtraidos)
    if dados is None:
        dados = extrator.extrair(pasta, numero)
    uf = dados.uf or cnj.uf_do_numero(numero) or "NA"
    valor_causa = dados.valor_causa if dados.valor_causa and dados.valor_causa > 0 else VALOR_CAUSA_PADRAO
    codigos = set(dados.codigos_sinais())
    caso = CasoFeatures(
        numero=numero, uf=uf, sub_assunto="Golpe" if codigos & SINAIS_GOLPE else "Genérico",
        valor_causa=valor_causa, subsidios=subs, sinais={c: True for c in codigos},
    )
    scores = _ler_derivado(derived / "scores" / f"{numero}.json", Scores) or modelo.score(caso)
    analise = extrator.analisar(caso, dados, scores)

    processo = db.scalar(select(Processo).where(Processo.numero == numero))
    if processo is None:
        processo = Processo(numero=numero, escritorio_id=escritorio_id, origem="exemplo")
        db.add(processo)
    processo.uf = uf
    processo.sub_assunto = caso.sub_assunto
    processo.valor_causa = valor_causa
    processo.subsidios = subs.model_dump()
    processo.documentos = docs
    processo.dados_extraidos = dados.model_dump(mode="json")
    processo.analise = analise.model_dump(mode="json")
    processo.scores = scores.model_dump(mode="json")
    db.commit()
    log.info("ingest %s: %d docs, %d subsídios, %d sinais, extração=%s, scores=%s",
             numero, len(docs), subs.n, len(codigos), dados.origem, scores.origem)
    return processo


def pastas_de_exemplo(data_dir: Path) -> Iterable[Path]:
    raiz = data_dir / "exemplos"
    if not raiz.is_dir():
        return []
    return sorted(p for p in raiz.iterdir() if p.is_dir() and not p.name.startswith("."))


def ingerir_todos(
    db: Session, data_dir: Path, extrator: ExtratorDocs, modelo: ModeloScores, escritorio_id: int
) -> list[Processo]:
    return [ingerir_pasta(db, p, data_dir, extrator, modelo, escritorio_id)
            for p in pastas_de_exemplo(data_dir)]
