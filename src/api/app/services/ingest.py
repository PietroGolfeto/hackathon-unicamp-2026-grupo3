"""Ingest das pastas data/exemplos/<numero>/{autos,subsidios}: upsert em processos por número.

Determinístico sem P3: flags dos subsídios pelos nomes dos arquivos e UF pelo número CNJ. Prefere
arquivos de P1/P3 em data/derived/ (extraidos/<numero>.json, scores/<numero>.json); senão chama o
extrator, se plugado, e o modelo carregados. Sem extrator, `dados_extraidos` e `analise` ficam
nulos: nada é inferido do conteúdo dos documentos. Nunca toca decisoes/recomendacoes.

Duas entradas: `ingerir_base` grava só a parte determinística (milissegundos, sem LLM) e
`ingerir_pasta` faz a passada completa com a leitura dos documentos. A preparação usa as duas,
uma em cada fase; o job `ingest` usa só a completa.
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
VALOR_CAUSA_PADRAO = 15000.0  # mediana da base (dados.md) quando ninguém extraiu o valor dos autos


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


def numero_da_pasta(pasta: Path) -> str:
    return cnj.normalizar(pasta.name) or pasta.name


def ingerir_pasta(
    db: Session, pasta: Path, data_dir: Path, extrator: ExtratorDocs | None, modelo: ModeloScores,
    escritorio_id: int,
) -> Processo:
    """Base + leitura dos documentos numa passada. É o caminho do job `ingest` e da fase 2."""
    numero = numero_da_pasta(pasta)
    dados = _ler_derivado(data_dir / "derived" / "extraidos" / f"{numero}.json", DadosExtraidos)
    if dados is None and extrator is not None:
        dados = extrator.extrair(pasta, numero)
    return _gravar(db, numero, pasta, data_dir, dados, extrator, modelo, escritorio_id)


def ingerir_base(
    db: Session, pasta: Path, data_dir: Path, modelo: ModeloScores, escritorio_id: int
) -> Processo:
    """Fase 1 da preparação: só o que os nomes dos arquivos e o número CNJ já dizem, sem LLM.

    Roda em milissegundos, então a lista do advogado carrega antes de qualquer leitura de PDF.
    Processo que a extração já preencheu fica como está: a base só apagaria o que a fase 2 achou.
    """
    numero = numero_da_pasta(pasta)
    processo = db.scalar(select(Processo).where(Processo.numero == numero))
    if processo is not None and processo.dados_extraidos is not None:
        return processo
    return _gravar(db, numero, pasta, data_dir, None, None, modelo, escritorio_id)


def _gravar(
    db: Session, numero: str, pasta: Path, data_dir: Path, dados: DadosExtraidos | None,
    extrator: ExtratorDocs | None, modelo: ModeloScores, escritorio_id: int,
) -> Processo:
    docs = listar_documentos(pasta, data_dir)
    subs = subsidios_por_arquivos(d["arquivo"] for d in docs if d["tipo"] == "subsidios")
    uf = (dados.uf if dados else None) or cnj.uf_do_numero(numero) or "NA"
    valor_extraido = dados.valor_causa if dados else None
    valor_causa = valor_extraido if valor_extraido and valor_extraido > 0 else VALOR_CAUSA_PADRAO
    codigos = set(dados.codigos_sinais()) if dados else set()
    caso = CasoFeatures(  # sub-assunto só viria dos autos; sem P3 fica desconhecido
        numero=numero, uf=uf, sub_assunto=None, valor_causa=valor_causa, subsidios=subs,
        sinais={c: True for c in codigos},
    )
    scores = (_ler_derivado(data_dir / "derived" / "scores" / f"{numero}.json", Scores)
              or modelo.score(caso))
    analise = extrator.analisar(caso, dados, scores) if extrator is not None and dados else None

    processo = db.scalar(select(Processo).where(Processo.numero == numero))
    if processo is None:
        processo = Processo(numero=numero, escritorio_id=escritorio_id, origem="exemplo")
        db.add(processo)
    processo.uf = uf
    processo.sub_assunto = caso.sub_assunto
    processo.valor_causa = valor_causa
    processo.subsidios = subs.model_dump()
    processo.documentos = docs
    processo.dados_extraidos = dados.model_dump(mode="json") if dados else None
    processo.analise = analise.model_dump(mode="json") if analise else None
    processo.scores = scores.model_dump(mode="json")
    db.commit()
    log.info("ingest %s: %d docs, %d subsídios, %d sinais, extração=%s, scores=%s",
             numero, len(docs), subs.n, len(codigos), dados.origem if dados else "nenhuma",
             scores.origem)
    return processo


def pastas_de_exemplo(data_dir: Path) -> Iterable[Path]:
    raiz = data_dir / "exemplos"
    if not raiz.is_dir():
        return []
    return sorted(p for p in raiz.iterdir() if p.is_dir() and not p.name.startswith("."))


def ingerir_todos(
    db: Session, data_dir: Path, extrator: ExtratorDocs | None, modelo: ModeloScores,
    escritorio_id: int,
) -> list[Processo]:
    return [ingerir_pasta(db, p, data_dir, extrator, modelo, escritorio_id)
            for p in pastas_de_exemplo(data_dir)]
