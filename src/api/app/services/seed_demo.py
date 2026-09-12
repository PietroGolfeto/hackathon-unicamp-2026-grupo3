"""Processos sintéticos (data/exemplos/sinteticos_processos.csv) + decisões simuladas em 8 semanas.

O CSV traz só o que a base real tem (UF, sub-assunto, valor da causa, seis flags) mais o
escritório; nada de autor, advogado ou sinais dos autos (decisão 27). Idempotente: processos por
número; nunca cria decisão para processo que já tem uma. Os do escritório "Banca Demo" ficam sem
decisão: são o pool que o link /demo reserva para a banca. Tudo que é simulado leva
payload.simulado=true nos eventos.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
from core.caso import CasoFeatures, Subsidios
from core.colunas import FLAGS_SUBSIDIOS
from core.modelo import ModeloScores
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.models import Decisao, Escritorio, Evento, Processo, Usuario
from app.schemas import DecisaoIn
from app.services.recomendacao import avaliar_decisao, obter_ou_criar, params_de, politica_ativa
from app.services.seed import ESCRITORIO_DEMO

# Justificativas simuladas: só o que o advogado saberia sem ler os autos (negociação, jurisprudência,
# subsídios presentes), nunca conteúdo de documento.
JUSTIFICATIVAS = [
    "Jurisprudência da comarca é consistentemente favorável ao consumidor neste tema.",
    "Valor sugerido abaixo do que a parte já sinalizou aceitar; ajustei para fechar.",
    "Dossiê e laudo presentes; entendo que a defesa tem chance maior que o score indica.",
    "Autor já tem outro processo idêntico julgado improcedente; preferi defender.",
    "Parte autora pediu valor menor que a banda; aceitei para encerrar rápido.",
]
DOCS_POR_FLAG = {f: f"{f}.pdf" for f in FLAGS_SUBSIDIOS}
PCT_PENDENTES = 15  # % dos processos com_decisao que ficam pendentes (fila do advogado)


def rodar(
    db: Session, csv: Path, modelo: ModeloScores, semanas: int = 8, seed: int = 2026,
) -> dict[str, int]:
    df = pd.read_csv(csv, dtype={"numero": str})
    rnd = random.Random(seed)
    escritorios = {e.nome: e for e in db.scalars(select(Escritorio))}
    advogados: dict[int, list[Usuario]] = {}
    for u in db.scalars(select(Usuario).where(Usuario.papel == "advogado")):
        advogados.setdefault(u.escritorio_id or 0, []).append(u)
    gestor = db.scalar(select(Usuario).where(Usuario.papel == "gestor"))
    politica = politica_ativa(db)
    prm = params_de(politica)
    agora = datetime.now(UTC)
    existentes = {p.numero: p for p in db.scalars(select(Processo))}
    com_decisao = set(db.scalars(select(Decisao.processo_id).distinct()))
    criados = decisoes = 0

    for linha in df.itertuples(index=False):
        escritorio = escritorios.get(str(linha.escritorio)) or escritorios[ESCRITORIO_DEMO]
        processo = existentes.get(linha.numero)
        if processo is None:
            processo = _criar_processo(linha, escritorio.id, modelo)
            db.add(processo)
            db.flush()
            existentes[linha.numero] = processo
            criados += 1
        if not int(linha.com_decisao) or processo.id in com_decisao or escritorio.nome == ESCRITORIO_DEMO:
            continue
        if int(linha.numero[:7]) % 100 < PCT_PENDENTES:  # determinístico: sobra fila para o advogado
            continue
        advs = advogados.get(escritorio.id) or []
        if not advs:
            continue
        rec = obter_ou_criar(db, processo, None, politica, modelo)
        advogado = rnd.choice(advs)
        quando = agora - timedelta(days=rnd.uniform(0.5, semanas * 7))
        dados_in = _decisao_simulada(rnd, rec, processo.valor_causa)
        aderente, tipo_desvio, status_dec = avaliar_decisao(rec, dados_in, prm, processo.valor_causa)
        decisao = Decisao(
            processo_id=processo.id, recomendacao_id=rec.id, usuario_id=advogado.id,
            tipo=dados_in.tipo, valor_proposto=dados_in.valor_proposto,
            justificativa=dados_in.justificativa, aderente=aderente, tipo_desvio=tipo_desvio,
            status=status_dec, tempo_analise_s=dados_in.tempo_analise_s,
            documentos_abertos=dados_in.documentos_abertos, created_at=quando,
        )
        if status_dec == "pendente_aprovacao" and gestor and rnd.random() < 0.7:
            decisao.status = "aprovada" if rnd.random() < 0.75 else "rejeitada"
            decisao.aprovado_por = gestor.id
            decisao.comentario_aprovacao = "Avaliado no lote semanal."
        _resultado_simulado(rnd, decisao, quando, agora)
        processo.status = "encerrado" if decisao.resultado else "decidido"
        db.add(decisao)
        inicio = quando - timedelta(seconds=dados_in.tempo_analise_s or 300)
        db.add(Evento(usuario_id=advogado.id, processo_id=processo.id, tipo="abriu_caso",
                      payload={"simulado": True}, created_at=inicio))
        if rnd.random() < 0.85:
            db.add(Evento(usuario_id=advogado.id, processo_id=processo.id, tipo="viu_recomendacao",
                          payload={"simulado": True, "recomendacao_id": rec.id},
                          created_at=inicio + timedelta(seconds=20)))
        com_decisao.add(processo.id)
        decisoes += 1
    db.commit()
    return {"processos_criados": criados, "decisoes_criadas": decisoes}


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


def _arredondar(v: float, passo: float = 50) -> float:
    return round(v / passo) * passo


def _decisao_simulada(rnd: random.Random, rec, valor_causa: float) -> DecisaoIn:
    docs = [DOCS_POR_FLAG[f] for f in FLAGS_SUBSIDIOS if rnd.random() < 0.5]
    tempo = rnd.randint(90, 1200)
    if rnd.random() < 0.8:  # aderente
        if rec.tipo == "defesa":
            return DecisaoIn(tipo="defesa", tempo_analise_s=tempo, documentos_abertos=docs)
        valor = _arredondar(rnd.uniform(rec.valor_min, rec.valor_max), 10)
        valor = min(max(valor, rec.valor_min), rec.valor_max)
        return DecisaoIn(tipo="acordo", valor_proposto=valor, tempo_analise_s=tempo,
                         documentos_abertos=docs)
    just = rnd.choice(JUSTIFICATIVAS)
    if rec.tipo == "acordo" and rnd.random() < 0.5:  # desvio de valor
        valor = _arredondar(rec.valor_max * 1.35 if rnd.random() < 0.6 else rec.valor_min * 0.6)
        return DecisaoIn(tipo="acordo", valor_proposto=max(valor, 100.0), justificativa=just,
                         tempo_analise_s=tempo, documentos_abertos=docs)
    if rec.tipo == "acordo":  # desvio de tipo: defender
        return DecisaoIn(tipo="defesa", justificativa=just, tempo_analise_s=tempo,
                         documentos_abertos=docs)
    valor = max(_arredondar(valor_causa * rnd.uniform(0.15, 0.4)), 100.0)  # desvio: acordar
    return DecisaoIn(tipo="acordo", valor_proposto=valor, justificativa=just, tempo_analise_s=tempo,
                     documentos_abertos=docs)


def _resultado_simulado(rnd: random.Random, d: Decisao, quando: datetime, agora: datetime) -> None:
    if quando > agora - timedelta(days=2):
        return
    if d.tipo == "defesa":
        if rnd.random() < 0.7:
            d.resultado = "seguiu_defesa"
            d.resultado_em = min(quando + timedelta(days=rnd.uniform(0.5, 3)), agora)
        return
    if d.status == "rejeitada" or rnd.random() > 0.75:
        return
    d.resultado = rnd.choices(
        ["aceito", "contraproposta_aceita", "recusado", "sem_resposta"], [0.55, 0.15, 0.2, 0.1]
    )[0]
    if d.resultado == "aceito":
        d.valor_final = d.valor_proposto
    elif d.resultado == "contraproposta_aceita":
        d.valor_final = _arredondar((d.valor_proposto or 0) * rnd.uniform(0.8, 0.97), 10)
    d.resultado_em = min(quando + timedelta(days=rnd.uniform(1, 10)), agora)


def reset_demo(db: Session) -> None:
    """Apaga decisões, eventos e recomendações; mantém processos e políticas."""
    db.execute(text("TRUNCATE decisoes, eventos, recomendacoes RESTART IDENTITY CASCADE"))
    db.execute(update(Processo).values(status="pendente", reservado_ate=None))
    db.commit()
