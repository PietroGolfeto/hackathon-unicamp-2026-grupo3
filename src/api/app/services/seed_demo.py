"""Processos sintéticos (data/exemplos/sinteticos_processos.csv) → tabela processos, todos pendentes.

O CSV traz só o que a base real tem (UF, sub-assunto, valor da causa, seis flags) mais o
escritório; nada de autor, advogado ou sinais dos autos (decisão 27). Não cria decisões, eventos
nem resultados: o painel do gestor só mostra o que advogados registraram de fato no portal
(decisão 28). Idempotente: processos por número. Os do escritório "Banca Demo" são o pool que o
link /demo reserva para a banca.

Documento único de demonstração: como o caso é sintético (sem autos reais), todo processo aponta
para o mesmo PDF de exemplo em `data/cache/sinteticos/exemplo.pdf` (baixado sob demanda; `data/cache/`
é o único ponto gravável do container e já é ignorado pelo git), só para a tela de documentos não ficar
vazia. Sem rede ou sem permissão de escrita o job avisa e segue: o link do documento dá 404, nada mais.
`popular_documentos_sinteticos` faz o backfill em processos já existentes.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd
from core.caso import CasoFeatures, Subsidios
from core.colunas import FLAGS_SUBSIDIOS
from core.modelo import ModeloScores
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.models import Escritorio, Processo
from app.services.seed import ESCRITORIO_DEMO

log = logging.getLogger(__name__)

# PDF genérico (não jurídico), só para a tela de documentos não ficar vazia em processo sintético;
# baixado uma vez para data/cache/sinteticos/ (o compose monta data/ só leitura e data/cache/ gravável).
URL_DOCUMENTO_SINTETICO = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
CAMINHO_DOCUMENTO_SINTETICO = "cache/sinteticos/exemplo.pdf"
DOCUMENTO_SINTETICO = [
    {"tipo": "autos", "arquivo": "peticao_inicial_exemplo.pdf", "caminho": CAMINHO_DOCUMENTO_SINTETICO},
]


def rodar(db: Session, csv: Path, modelo: ModeloScores, data_dir: Path) -> dict[str, int]:
    df = pd.read_csv(csv, dtype={"numero": str})
    escritorios = {e.nome: e for e in db.scalars(select(Escritorio))}
    existentes = set(db.scalars(select(Processo.numero)))
    criados = 0
    for linha in df.itertuples(index=False):
        if linha.numero in existentes:
            continue
        escritorio = escritorios.get(str(linha.escritorio)) or escritorios[ESCRITORIO_DEMO]
        db.add(_criar_processo(linha, escritorio.id, modelo))
        existentes.add(linha.numero)
        criados += 1
    db.commit()
    _garantir_pdf_exemplo(data_dir)
    populados = popular_documentos_sinteticos(db)
    return {"processos_criados": criados, "documentos_populados": populados}


def _garantir_pdf_exemplo(data_dir: Path) -> None:
    """Baixa uma vez o PDF de demonstração usado por todo processo sintético."""
    destino = data_dir / CAMINHO_DOCUMENTO_SINTETICO
    if destino.exists():
        return
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL_DOCUMENTO_SINTETICO, destino)
    except (urllib.error.URLError, OSError) as exc:
        log.warning("não baixou o PDF de exemplo (%s): documentos sintéticos ficarão indisponíveis", exc)


def _criar_processo(linha, escritorio_id: int, modelo: ModeloScores) -> Processo:
    """Só o que a base real tem: UF, sub-assunto, valor da causa e as seis flags."""
    subs = Subsidios(**{f: bool(int(getattr(linha, f))) for f in FLAGS_SUBSIDIOS})
    caso = CasoFeatures(numero=linha.numero, uf=linha.uf, sub_assunto=linha.sub_assunto,
                        valor_causa=float(linha.valor_causa), subsidios=subs)
    scores = modelo.score(caso)
    return Processo(
        numero=linha.numero, uf=linha.uf, sub_assunto=linha.sub_assunto,
        valor_causa=float(linha.valor_causa), escritorio_id=escritorio_id, origem="sintetico",
        subsidios=subs.model_dump(), documentos=DOCUMENTO_SINTETICO, dados_extraidos=None, analise=None,
        scores=scores.model_dump(mode="json"), status="pendente",
    )


def popular_documentos_sinteticos(db: Session) -> int:
    """Backfill: processos sintéticos já existentes sem documentos passam a ter o PDF de exemplo."""
    sem_docs = db.scalars(select(Processo).where(Processo.origem == "sintetico")).all()
    populados = 0
    for p in sem_docs:
        if not p.documentos:
            p.documentos = DOCUMENTO_SINTETICO
            populados += 1
    db.commit()
    return populados


def reset_demo(db: Session) -> None:
    """Apaga decisões, eventos e recomendações; mantém processos e políticas."""
    db.execute(text("TRUNCATE decisoes, eventos, recomendacoes RESTART IDENTITY CASCADE"))
    db.execute(update(Processo).values(status="pendente", reservado_ate=None))
    db.commit()
