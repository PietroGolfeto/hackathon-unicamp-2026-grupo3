"""Parecer consultivo, sob demanda, para justificativas de decisões divergentes."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Decisao, ParecerJustificativa, Processo, Recomendacao

log = logging.getLogger(__name__)

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
TIMEOUT_S = 20
CLASSIFICACOES = ("fundamentada", "generica", "contradiz_evidencias")

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "classificacao": {
            "type": "string",
            "enum": list(CLASSIFICACOES),
        },
        "resumo": {"type": "string"},
        "pontos": {"type": "array", "items": {"type": "string"}},
        "confianca": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["classificacao", "resumo", "pontos", "confianca"],
    "additionalProperties": False,
}


class ParecerIndisponivel(RuntimeError):
    """Indica que o provedor não conseguiu produzir um parecer válido."""


def obter_ou_gerar(db: Session, decisao_id: int) -> dict[str, Any]:
    """Retorne o parecer persistido ou gere um novo para uma divergência.

    Args:
        db: Sessão transacional do banco.
        decisao_id: Identificador da decisão divergente.

    Returns:
        Parecer estruturado pronto para a API.

    Raises:
        LookupError: Se a decisão não existir.
        ValueError: Se a decisão for aderente ou não tiver justificativa.
        ParecerIndisponivel: Se a integração não estiver configurada ou falhar.
    """
    existente = db.scalar(
        select(ParecerJustificativa).where(ParecerJustificativa.decisao_id == decisao_id)
    )
    if existente is not None:
        return existente.conteudo

    linha = db.execute(
        select(Decisao, Processo, Recomendacao)
        .join(Processo, Processo.id == Decisao.processo_id)
        .join(Recomendacao, Recomendacao.id == Decisao.recomendacao_id)
        .where(Decisao.id == decisao_id)
    ).one_or_none()
    if linha is None:
        raise LookupError("Decisão não encontrada.")

    decisao, processo, recomendacao = linha
    if decisao.aderente:
        raise ValueError("A decisão é aderente e não precisa de parecer.")
    if not decisao.justificativa:
        raise ValueError("A decisão divergente não tem justificativa.")

    try:
        conteudo = _chamar_openai(_contexto(decisao, processo, recomendacao))
    except ParecerIndisponivel:
        log.warning("Parecer consultivo indisponível: decisao_id=%s", decisao.id)
        raise
    conteudo.update({
        "decisao_id": decisao.id,
        "modelo": settings.openai_model,
        "gerado_em": datetime.now(UTC).isoformat(),
    })
    db.add(ParecerJustificativa(decisao_id=decisao.id, conteudo=conteudo))
    db.commit()
    return conteudo


def _contexto(decisao: Decisao, processo: Processo, recomendacao: Recomendacao) -> dict[str, Any]:
    """Monte apenas o contexto determinístico necessário para avaliar a justificativa.

    Args:
        decisao: Decisão tomada pelo advogado.
        processo: Processo associado.
        recomendacao: Recomendação que o advogado viu.

    Returns:
        Contexto sem documentos brutos ou dados pessoais.
    """
    scores = recomendacao.scores_snapshot
    presentes = [nome for nome, presente in processo.subsidios.items() if presente]
    ausentes = [nome for nome, presente in processo.subsidios.items() if not presente]
    return {
        "justificativa": decisao.justificativa,
        "decisao_advogado": {
            "tipo": decisao.tipo,
            "valor_proposto": decisao.valor_proposto,
        },
        "recomendacao_banco": {
            "tipo": recomendacao.tipo,
            "valor_sugerido": recomendacao.valor_sugerido,
            "valor_min": recomendacao.valor_min,
            "valor_max": recomendacao.valor_max,
            "motivos": recomendacao.motivos,
        },
        "caso": {
            "uf": processo.uf,
            "sub_assunto": processo.sub_assunto,
            "valor_causa": processo.valor_causa,
            "subsidios_presentes": presentes,
            "subsidios_ausentes": ausentes,
            "p_exito_defesa": scores.get("p_exito_defesa"),
            "condenacao_p20": scores.get("condenacao_p20"),
            "condenacao_p80": scores.get("condenacao_p80"),
        },
    }


def _chamar_openai(contexto: dict[str, Any]) -> dict[str, Any]:
    """Solicite ao provedor um parecer estruturado e estritamente consultivo.

    Args:
        contexto: Fatos determinísticos e justificativa a avaliar.

    Returns:
        Parecer validado contra o contrato mínimo.

    Raises:
        ParecerIndisponivel: Se faltar configuração, a chamada falhar ou a resposta for inválida.
    """
    if not settings.openai_api_key:
        raise ParecerIndisponivel("Análise por IA indisponível: configure OPENAI_API_KEY.")

    instrucao = (
        "Você assessora o gestor jurídico de um banco. Avalie somente se a justificativa do "
        "advogado explica de forma concreta a divergência em relação à política. Não redecida o "
        "caso, não invente fatos e não trate o parecer como aprovação. Classifique como fundamentada "
        "quando cita fatos relevantes e coerentes; genérica quando não apresenta evidência específica; "
        "contradiz_evidencias quando conflita diretamente com os fatos fornecidos. Resuma em no máximo "
        "duas frases em português e liste até três pontos objetivos."
    )
    payload = {
        "model": settings.openai_model,
        "instructions": instrucao,
        "input": json.dumps(contexto, ensure_ascii=False),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "parecer_justificativa",
                "strict": True,
                "schema": SCHEMA,
            }
        },
    }
    request = Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=TIMEOUT_S) as response:
            bruto = json.loads(response.read())
    except HTTPError as exc:
        detalhe = exc.read().decode(errors="replace")[:300]
        log.warning("OpenAI recusou parecer decisório: status=%s detalhe=%s", exc.code, detalhe)
        raise ParecerIndisponivel("A análise por IA falhou. Tente novamente.") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        log.warning("Falha ao gerar parecer decisório: erro=%s", type(exc).__name__)
        raise ParecerIndisponivel("A análise por IA falhou. Tente novamente.") from exc

    try:
        texto = bruto.get("output_text") or next(
            parte["text"]
            for item in bruto["output"]
            for parte in item.get("content", [])
            if parte.get("type") == "output_text"
        )
        parecer = json.loads(texto)
        if parecer["classificacao"] not in CLASSIFICACOES:
            raise ValueError("classificação inválida")
        parecer["confianca"] = min(1.0, max(0.0, float(parecer["confianca"])))
        parecer["pontos"] = [str(p) for p in parecer["pontos"][:3]]
        parecer["resumo"] = str(parecer["resumo"])
        return parecer
    except (KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError) as exc:
        log.warning("Resposta inválida ao gerar parecer decisório: response_id=%s", bruto.get("id"))
        raise ParecerIndisponivel("A IA retornou uma análise inválida. Tente novamente.") from exc
