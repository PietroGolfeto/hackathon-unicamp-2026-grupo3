"""Decisões sorteadas para conferir o painel do gestor durante o desenvolvimento.

Exceção local e explícita à decisão 28: aderência, justificativas e resultados daqui são inventados
e o painel os exibe como se fossem medidos. Por isso o comando trava fora de banco local e nunca
roda no ambiente da banca, que continua mostrando só o que advogados registraram no portal. A
recomendação de cada processo vem do motor real, então os agregados são calculados de verdade.
`reset-demo` apaga tudo o que este módulo cria.
"""

from __future__ import annotations

import logging
import random
from datetime import UTC, datetime, timedelta
from typing import cast

from core.modelo import ModeloScores
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Decisao,
    Escritorio,
    Evento,
    ParecerJustificativa,
    Processo,
    Recomendacao,
    Usuario,
)
from app.schemas import DecisaoIn, TipoDecisao
from app.services import recomendacao as rec_service
from app.services.seed import ESCRITORIO_DEMO

log = logging.getLogger(__name__)

SEMENTE = 20260913
SEMANAS = 6

# Um escritório visivelmente pior que os outros é o que o painel existe para o gestor encontrar.
ADERENCIA_ALVO = {"Escritório A": 0.92, "Escritório B": 0.84, "Escritório C": 0.57}
ADERENCIA_PADRAO = 0.85

# Parte dos acordos ainda sem desfecho registrado: é o que exercita o aviso de cobertura.
COBERTURA_RESULTADO = 0.7
PESOS_RESULTADO = {"aceito": 0.55, "contraproposta_aceita": 0.15, "recusado": 0.18,
                   "sem_resposta": 0.12}

JUSTIFICATIVAS_TIPO = [
    "Contrato e extrato juntados pelo banco mostram crédito na conta do autor; defesa tem base.",
    "Autor já litigou três vezes pelo mesmo contrato nesta comarca; acordo premiaria a repetição.",
    "A instrução foi encerrada e a sentença sai nesta semana; acordo agora perde sentido.",
    "Vara local vem julgando improcedente com esse mesmo conjunto de provas.",
    "O caso é do mesmo polo ativo de outra ação já extinta por litispendência.",
    "Cliente sinalizou interesse em encerrar, mas não há comprovante de crédito nos autos.",
    "Divirjo porque entendo que o risco está superestimado.",
    "Melhor acordar para não correr risco.",
]
JUSTIFICATIVAS_VALOR = [
    "Autor recusou a banda e sinalizou fechar em valor acima; abaixo disso vai a julgamento.",
    "Condenação média desta vara está acima da banda sugerida para o mesmo sub-assunto.",
    "Valor cobre dano moral e repetição do indébito, que a banda não considerou.",
    "A audiência de conciliação já fixou patamar superior com o juízo presente.",
    "Acho o valor sugerido baixo demais.",
]

PARECERES_EXEMPLO = [
    {"classificacao": "fundamentada", "confianca": 0.82,
     "resumo": "A justificativa aponta prova documental concreta que sustenta a defesa.",
     "pontos": ["Cita contrato e extrato como subsídios presentes",
                "Coerente com a probabilidade de êxito do caso"]},
    {"classificacao": "generica", "confianca": 0.74,
     "resumo": "A justificativa não apresenta evidência específica do caso.",
     "pontos": ["Afirmação sobre risco sem dado de apoio",
                "Não menciona subsídios nem histórico da vara"]},
    {"classificacao": "contradiz_evidencias", "confianca": 0.66,
     "resumo": "A justificativa conflita com os subsídios registrados no processo.",
     "pontos": ["Alega prova que os autos não têm",
                "Diverge da faixa de condenação estimada"]},
]


def rodar(db: Session, modelo: ModeloScores, n: int = 120) -> dict[str, int]:
    """Crie decisões sorteadas sobre processos pendentes para popular o painel do gestor.

    Args:
        db: Sessão transacional do banco.
        modelo: Fonte dos scores, usada pelo motor real de recomendação.
        n: Quantidade máxima de decisões a criar.

    Returns:
        Contagem do que foi criado, por tipo de registro.
    """
    sorteio = random.Random(SEMENTE)
    politica = rec_service.politica_ativa(db)
    params = rec_service.params_de(politica)
    advogados = _advogados_por_escritorio(db)
    processos = _pendentes(db, advogados, n, sorteio)
    agora = datetime.now(UTC)

    criadas = divergentes = resultados = 0
    for processo in processos:
        escritorio = processo.escritorio.nome
        advogado = sorteio.choice(advogados[processo.escritorio_id])
        rec = rec_service.obter_ou_criar(db, processo, advogado, politica, modelo)
        aderir = sorteio.random() < ADERENCIA_ALVO.get(escritorio, ADERENCIA_PADRAO)
        entrada = _entrada(rec, processo, aderir, sorteio)
        aderente, tipo_desvio, status = rec_service.avaliar_decisao(
            rec, entrada, params, processo.valor_causa
        )
        criada_em = agora - timedelta(
            days=sorteio.randrange(SEMANAS * 7), hours=sorteio.randrange(24)
        )
        decisao = Decisao(
            processo_id=processo.id, recomendacao_id=rec.id, usuario_id=advogado.id,
            tipo=entrada.tipo, valor_proposto=entrada.valor_proposto,
            justificativa=entrada.justificativa, aderente=aderente, tipo_desvio=tipo_desvio,
            status=status, tempo_analise_s=entrada.tempo_analise_s,
            documentos_abertos=entrada.documentos_abertos, created_at=criada_em,
        )
        _negociar(decisao, criada_em, sorteio)
        db.add(decisao)
        processo.status = "decidido"
        _eventos(db, advogado.id, processo.id, criada_em, sorteio)
        criadas += 1
        divergentes += not aderente
        resultados += decisao.resultado is not None
    db.commit()

    pareceres = _pareceres(db, sorteio)
    log.warning("mock-painel: %d decisões sorteadas no banco; use reset-demo para apagar", criadas)
    return {"decisoes": criadas, "divergentes": divergentes, "com_resultado": resultados,
            "pareceres": pareceres}


def _advogados_por_escritorio(db: Session) -> dict[int, list[Usuario]]:
    """Agrupe advogados por escritório, deixando de fora o pool reservado à banca."""
    demo = db.scalar(select(Escritorio.id).where(Escritorio.nome == ESCRITORIO_DEMO))
    porta: dict[int, list[Usuario]] = {}
    for usuario in db.scalars(select(Usuario).where(Usuario.papel == "advogado")):
        if usuario.escritorio_id is None or usuario.escritorio_id == demo:
            continue
        porta.setdefault(usuario.escritorio_id, []).append(usuario)
    if not porta:
        raise RuntimeError("nenhum advogado fora da Banca Demo: rode o seed antes")
    return porta


def _pendentes(
    db: Session, advogados: dict[int, list[Usuario]], n: int, sorteio: random.Random
) -> list[Processo]:
    processos = list(db.scalars(
        select(Processo)
        .where(Processo.status == "pendente", Processo.escritorio_id.in_(advogados))
        .order_by(Processo.id)
    ))
    sorteio.shuffle(processos)
    return processos[:n]


def _entrada(
    rec: Recomendacao, processo: Processo, aderir: bool, sorteio: random.Random
) -> DecisaoIn:
    """Monte a decisão do advogado: dentro da banda quando adere, fora dela quando diverge."""
    documentos = sorteio.sample(["contrato", "extrato", "dossie"], k=sorteio.randrange(3))
    tempo = sorteio.randrange(90, 900)
    if aderir:
        valor = None
        if rec.tipo == "acordo" and rec.valor_min is not None and rec.valor_max is not None:
            valor = round(sorteio.uniform(rec.valor_min, rec.valor_max), 2)
        return DecisaoIn(tipo=cast(TipoDecisao, rec.tipo), valor_proposto=valor,
                         tempo_analise_s=tempo, documentos_abertos=documentos)

    pode_desviar_valor = rec.tipo == "acordo" and rec.valor_max is not None
    if pode_desviar_valor and sorteio.random() < 0.6:
        return DecisaoIn(
            tipo="acordo", valor_proposto=round(rec.valor_max * sorteio.uniform(1.2, 1.6), 2),
            justificativa=sorteio.choice(JUSTIFICATIVAS_VALOR), tempo_analise_s=tempo,
            documentos_abertos=documentos,
        )
    if rec.tipo == "acordo":
        return DecisaoIn(tipo="defesa", justificativa=sorteio.choice(JUSTIFICATIVAS_TIPO),
                         tempo_analise_s=tempo, documentos_abertos=documentos)
    return DecisaoIn(
        tipo="acordo", valor_proposto=round(processo.valor_causa * sorteio.uniform(0.2, 0.45), 2),
        justificativa=sorteio.choice(JUSTIFICATIVAS_TIPO), tempo_analise_s=tempo,
        documentos_abertos=documentos,
    )


def _negociar(decisao: Decisao, criada_em: datetime, sorteio: random.Random) -> None:
    """Registre o desfecho de parte dos acordos; o resto fica sem resultado, como na operação."""
    if decisao.tipo != "acordo" or sorteio.random() > COBERTURA_RESULTADO:
        return
    resultado = sorteio.choices(list(PESOS_RESULTADO), weights=list(PESOS_RESULTADO.values()))[0]
    decisao.resultado = resultado
    decisao.resultado_em = criada_em + timedelta(days=sorteio.randrange(2, 15))
    if resultado == "aceito":
        decisao.valor_final = decisao.valor_proposto
    elif resultado == "contraproposta_aceita":
        decisao.valor_final = round((decisao.valor_proposto or 0.0) * sorteio.uniform(1.05, 1.3), 2)


def _eventos(
    db: Session, usuario_id: int, processo_id: int, criada_em: datetime, sorteio: random.Random
) -> None:
    """Deixe uma minoria sem ver recomendação ou sem abrir documento, como acontece de fato."""
    if sorteio.random() < 0.9:
        db.add(Evento(usuario_id=usuario_id, processo_id=processo_id, tipo="viu_recomendacao",
                      payload={}, created_at=criada_em))
    if sorteio.random() < 0.75:
        db.add(Evento(usuario_id=usuario_id, processo_id=processo_id, tipo="abriu_documento",
                      payload={"documento": "contrato"}, created_at=criada_em))


def _pareceres(db: Session, sorteio: random.Random) -> int:
    """Preencha a coluna de parecer de algumas divergências sem gastar chamada de API."""
    divergentes = list(db.scalars(
        select(Decisao).where(~Decisao.aderente, Decisao.justificativa.is_not(None))
        .order_by(Decisao.created_at.desc()).limit(12)
    ))
    ja_tem = set(db.scalars(select(ParecerJustificativa.decisao_id)))
    criados = 0
    for decisao in divergentes:
        if decisao.id in ja_tem or sorteio.random() > 0.6:
            continue
        conteudo = dict(sorteio.choice(PARECERES_EXEMPLO))
        conteudo.update({"decisao_id": decisao.id, "modelo": f"{settings.openai_model} (mock)",
                         "gerado_em": datetime.now(UTC).isoformat()})
        db.add(ParecerJustificativa(decisao_id=decisao.id, conteudo=conteudo))
        criados += 1
    db.commit()
    return criados
