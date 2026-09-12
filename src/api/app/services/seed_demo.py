"""Processos sintéticos (data/exemplos/sinteticos_processos.csv) → tabela processos, todos pendentes.

O CSV traz só o que a base real tem (UF, sub-assunto, valor da causa, seis flags) mais o
escritório; nada de autor, advogado ou sinais dos autos (decisão 27). Não cria decisões, eventos
nem resultados: o painel do gestor só mostra o que advogados registraram de fato no portal
(decisão 28). Idempotente: processos por número. Os do escritório "Banca Demo" são o pool que o
link /demo reserva para a banca.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from core.caso import CasoFeatures, Subsidios
from core.colunas import FLAGS_SUBSIDIOS
from core.modelo import ModeloScores
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.models import Escritorio, Processo
from app.services.seed import ESCRITORIO_DEMO


def rodar(db: Session, csv: Path, modelo: ModeloScores) -> dict[str, int]:
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
    return {"processos_criados": criados}


def _criar_processo(linha, escritorio_id: int, modelo: ModeloScores) -> Processo:
    """Só o que a base real tem: UF, sub-assunto, valor da causa e as seis flags."""
    subs = Subsidios(**{f: bool(int(getattr(linha, f))) for f in FLAGS_SUBSIDIOS})
    caso = CasoFeatures(numero=linha.numero, uf=linha.uf, sub_assunto=linha.sub_assunto,
                        valor_causa=float(linha.valor_causa), subsidios=subs)
    scores = modelo.score(caso)
    return Processo(
        numero=linha.numero, uf=linha.uf, sub_assunto=linha.sub_assunto,
        valor_causa=float(linha.valor_causa), escritorio_id=escritorio_id, origem="sintetico",
        subsidios=subs.model_dump(), documentos=[], dados_extraidos=None, analise=None,
        scores=scores.model_dump(mode="json"), status="pendente",
    )


def reset_demo(db: Session) -> None:
    """Apaga decisões, eventos e recomendações; mantém processos e políticas."""
    db.execute(text("TRUNCATE decisoes, eventos, recomendacoes RESTART IDENTITY CASCADE"))
    db.execute(update(Processo).values(status="pendente", reservado_ate=None))
    db.commit()
