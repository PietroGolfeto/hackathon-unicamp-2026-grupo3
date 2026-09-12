"""Lista, detalhe, recomendação, decisão, resultado, eventos e resumo em texto."""

from __future__ import annotations

from typing import Annotated

from core.politica import brl
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import UsuarioLogado, pode_ver_processo
from app.db import get_db
from app.models import Decisao, Processo, Recomendacao, Usuario
from app.schemas import (
    DecisaoIn,
    DecisaoOut,
    DecisaoRegistrada,
    DocumentoOut,
    EventoIn,
    ProcessoDetalhe,
    ProcessoResumo,
    RecomendacaoOut,
    RecomendacaoResumo,
    ResultadoIn,
)
from app.services import recomendacao as svc

router = APIRouter(tags=["processos"])
Db = Annotated[Session, Depends(get_db)]


def obter_processo(db: Session, processo_id: int, usuario: Usuario) -> Processo:
    processo = db.get(Processo, processo_id)
    if processo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Processo não encontrado.")
    if not pode_ver_processo(usuario, processo.escritorio_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="Este processo pertence a outro escritório.")
    return processo


def decisao_atual(db: Session, processo_id: int) -> Decisao | None:
    return db.scalar(select(Decisao).where(Decisao.processo_id == processo_id)
                     .order_by(Decisao.id.desc()).limit(1))


def _autor(p: Processo) -> str | None:
    return ((p.dados_extraidos or {}).get("autor") or {}).get("nome")


def _sinais(p: Processo) -> list[dict]:
    return list((p.dados_extraidos or {}).get("sinais_alerta") or [])


def _resumo(p: Processo, rec: Recomendacao | None, dec: Decisao | None) -> ProcessoResumo:
    return ProcessoResumo(
        id=p.id, numero=p.numero, uf=p.uf, sub_assunto=p.sub_assunto, valor_causa=p.valor_causa,
        autor=_autor(p), status=p.status, origem=p.origem, escritorio_id=p.escritorio_id,
        escritorio=p.escritorio.nome, n_subsidios=sum(1 for v in (p.subsidios or {}).values() if v),
        sinais=[s.get("codigo", "") for s in _sinais(p)],
        scores_origem=(p.scores or {}).get("origem"),
        extracao_origem=(p.dados_extraidos or {}).get("origem"),
        recomendacao=RecomendacaoResumo.model_validate(rec) if rec else None,
        decisao_tipo=dec.tipo if dec else None, decisao_status=dec.status if dec else None,
        reservado_ate=p.reservado_ate,
    )


@router.get("/processos", response_model=list[ProcessoResumo])
def listar(
    usuario: UsuarioLogado, db: Db,
    busca: Annotated[str | None, Query(max_length=40)] = None,
    escritorio_id: int | None = None,
    situacao: Annotated[str | None, Query(alias="status")] = None,
    limite: Annotated[int, Query(ge=1, le=2000)] = 500,
) -> list[ProcessoResumo]:
    q = select(Processo).order_by(Processo.id)
    if usuario.papel != "gestor":
        q = q.where(Processo.escritorio_id == usuario.escritorio_id)
    elif escritorio_id is not None:
        q = q.where(Processo.escritorio_id == escritorio_id)
    if busca:
        q = q.where(Processo.numero.ilike(f"%{busca.strip()}%"))
    if situacao:
        q = q.where(Processo.status == situacao)
    processos = list(db.scalars(q.limit(limite)))
    ids = [p.id for p in processos]
    recs: dict[int, Recomendacao] = {}
    for r in db.scalars(select(Recomendacao).where(Recomendacao.processo_id.in_(ids))
                        .order_by(Recomendacao.id)):
        recs[r.processo_id] = r
    decs: dict[int, Decisao] = {}
    for d in db.scalars(select(Decisao).where(Decisao.processo_id.in_(ids)).order_by(Decisao.id)):
        decs[d.processo_id] = d
    return [_resumo(p, recs.get(p.id), decs.get(p.id)) for p in processos]


@router.get("/processos/{processo_id}", response_model=ProcessoDetalhe)
def detalhe(processo_id: int, usuario: UsuarioLogado, db: Db) -> ProcessoDetalhe:
    p = obter_processo(db, processo_id, usuario)
    svc.registrar_evento(db, usuario.id, p.id, "abriu_caso")
    dec = decisao_atual(db, p.id)
    return ProcessoDetalhe(
        id=p.id, numero=p.numero, uf=p.uf, sub_assunto=p.sub_assunto, valor_causa=p.valor_causa,
        status=p.status, origem=p.origem, escritorio_id=p.escritorio_id,
        escritorio=p.escritorio.nome, subsidios={k: bool(v) for k, v in (p.subsidios or {}).items()},
        documentos=[DocumentoOut(tipo=d["tipo"], arquivo=d["arquivo"],
                                 url=f"/api/files/{p.id}/{d['arquivo']}") for d in p.documentos or []],
        dados_extraidos=p.dados_extraidos, analise=p.analise, sinais=_sinais(p), scores=p.scores,
        decisao_atual=DecisaoOut.model_validate(dec) if dec else None,
        reservado_ate=p.reservado_ate, created_at=p.created_at,
    )


@router.get("/processos/{processo_id}/recomendacao", response_model=RecomendacaoOut)
def recomendacao(processo_id: int, request: Request, usuario: UsuarioLogado, db: Db) -> RecomendacaoOut:
    """Get-or-create sob a política ativa. O que o advogado vê aqui é o que a aderência mede."""
    p = obter_processo(db, processo_id, usuario)
    politica = svc.politica_ativa(db)
    rec = svc.obter_ou_criar(db, p, usuario, politica, request.app.state.modelo)
    svc.registrar_evento(db, usuario.id, p.id, "viu_recomendacao",
                         {"recomendacao_id": rec.id, "politica_id": politica.id})
    return svc.para_saida(rec, politica, p)


@router.post("/processos/{processo_id}/decisoes", response_model=DecisaoRegistrada,
             status_code=status.HTTP_201_CREATED)
def decidir(
    processo_id: int, dados: DecisaoIn, request: Request, usuario: UsuarioLogado, db: Db
) -> DecisaoRegistrada:
    p = obter_processo(db, processo_id, usuario)
    politica = svc.politica_ativa(db)
    rec = svc.obter_ou_criar(db, p, usuario, politica, request.app.state.modelo)
    prm = svc.params_de(politica)
    aderente, tipo_desvio, situacao = svc.avaliar_decisao(rec, dados, prm, p.valor_causa)
    decisao = Decisao(
        processo_id=p.id, recomendacao_id=rec.id, usuario_id=usuario.id, tipo=dados.tipo,
        valor_proposto=dados.valor_proposto if dados.tipo == "acordo" else None,
        justificativa=(dados.justificativa or "").strip() or None, aderente=aderente,
        tipo_desvio=tipo_desvio, status=situacao, tempo_analise_s=dados.tempo_analise_s,
        documentos_abertos=list(dados.documentos_abertos),
    )
    p.status = "decidido"
    db.add(decisao)
    db.commit()
    db.refresh(decisao)

    minutas = contato = None
    if dados.tipo == "acordo":
        extrator = request.app.state.extrator
        dados_ext = (p.dados_extraidos or {})
        from core.docs import DadosExtraidos

        de = DadosExtraidos.model_validate(dados_ext) if dados_ext else None
        if de is not None:
            minutas = extrator.redigir(svc.caso_de(p), de, svc.rec_core_de(rec)).model_dump(mode="json")
            contato = de.advogado_autor.model_dump(mode="json")
    if situacao == "pendente_aprovacao":
        mensagem = "Decisão registrada e enviada para aprovação do gestor."
    elif aderente:
        mensagem = "Decisão registrada, aderente à política."
    else:
        mensagem = "Decisão registrada com desvio justificado."
    return DecisaoRegistrada(decisao=DecisaoOut.model_validate(decisao),
                             recomendacao=svc.para_saida(rec, politica, p),
                             minutas=minutas, contato_adverso=contato, mensagem=mensagem)


@router.post("/decisoes/{decisao_id}/resultado", response_model=DecisaoOut)
def resultado(decisao_id: int, dados: ResultadoIn, usuario: UsuarioLogado, db: Db) -> Decisao:
    decisao = db.get(Decisao, decisao_id)
    if decisao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Decisão não encontrada.")
    p = obter_processo(db, decisao.processo_id, usuario)
    if decisao.tipo == "defesa" and dados.resultado != "seguiu_defesa":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="Decisão de defesa só admite o resultado 'seguiu_defesa'.")
    if decisao.tipo == "acordo" and dados.resultado == "seguiu_defesa":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="Informe o resultado da negociação do acordo.")
    if dados.resultado in ("aceito", "contraproposta_aceita") and dados.valor_final is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="Informe o valor final acordado.")
    decisao.resultado = dados.resultado
    decisao.valor_final = dados.valor_final
    decisao.observacao = (dados.observacao or "").strip() or None
    decisao.resultado_em = svc.agora()
    p.status = "encerrado"
    db.commit()
    db.refresh(decisao)
    return decisao


@router.post("/eventos", status_code=status.HTTP_204_NO_CONTENT)
def evento(dados: EventoIn, usuario: UsuarioLogado, db: Db) -> None:
    if dados.processo_id is not None:
        obter_processo(db, dados.processo_id, usuario)
    svc.registrar_evento(db, usuario.id, dados.processo_id, dados.tipo, dados.payload)


@router.get("/processos/{processo_id}/resumo.txt", response_class=PlainTextResponse)
def resumo_txt(processo_id: int, request: Request, usuario: UsuarioLogado, db: Db) -> str:
    """Texto plano para copiar ou mandar no WhatsApp."""
    p = obter_processo(db, processo_id, usuario)
    politica = svc.politica_ativa(db)
    rec = svc.obter_ou_criar(db, p, usuario, politica, request.app.state.modelo)
    sinais = ", ".join(s.get("descricao", s.get("codigo", "")) for s in _sinais(p)) or "nenhum"
    linhas = [
        f"Processo {p.numero} ({p.uf}) — {_autor(p) or 'autor não identificado'}",
        (f"Valor da causa: {brl(p.valor_causa)} · Subsídios: "
         f"{sum(1 for v in (p.subsidios or {}).values() if v)}/6 · Sinais: {sinais}"),
        f"RECOMENDAÇÃO: {rec.tipo.upper()}"
        + (f" — oferta {brl(rec.valor_sugerido or 0)} (banda {brl(rec.valor_min or 0)} a "
           f"{brl(rec.valor_max or 0)})" if rec.tipo == "acordo" else ""),
        *[f"- {m}" for m in rec.motivos or []],
        f"Política v{politica.versao} · P(êxito) {rec.scores_snapshot.get('p_exito_defesa', 0):.0%}",
        f"{request.url.scheme}://{request.url.netloc}/casos/{p.id}",
    ]
    return "\n".join(linhas)
