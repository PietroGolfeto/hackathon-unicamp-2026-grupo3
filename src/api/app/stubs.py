"""Stubs de P1 e P3. Existem desde a hora 1 para a API funcionar ponta a ponta sem o time.

StubModelo: P(êxito) por lookup (contrato, extrato, comprovante, sub_assunto) no histórico em
memória; sem histórico, 0,03 + 0,16·n_docs. Condenação 0,55/0,74/0,86 × valor da causa.
StubExtrator: flags por nome de arquivo, UF pelo CNJ, regex no texto dos autos, textos por template.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from core import cnj
from core.caso import CODIGOS_SINAIS, NOMES_SUBSIDIOS, CasoFeatures
from core.colunas import FLAGS_SUBSIDIOS, parse_brl
from core.docs import (
    Advogado,
    Analise,
    ContratoInfo,
    DadosExtraidos,
    Minutas,
    Pessoa,
    SinalAlerta,
    subsidios_por_arquivos,
)
from core.modelo import Contribuicao, ModeloInfo, Scores
from core.politica import Recomendacao, brl

log = logging.getLogger(__name__)

# Diferença de taxa de êxito com e sem o subsídio (dados.md), usada quando não há histórico.
EFEITOS_PADRAO: dict[str, float] = {
    "contrato": 0.62, "extrato": 0.63, "comprovante_credito": 0.27,
    "dossie": 0.0, "demonstrativo_divida": 0.0, "laudo_referenciado": 0.0,
}
EFEITO_GOLPE = -0.19
CHAVE = ("contrato", "extrato", "comprovante_credito", "sub_assunto")
MIN_GRUPO = 30


class StubModelo:
    versao = "stub-lookup-v1"

    def __init__(self, historico: pd.DataFrame | None = None) -> None:
        self._tabela: dict[tuple, float] = {}
        self._efeitos = dict(EFEITOS_PADRAO)
        self._n = 0
        self._treinado_em = datetime.now(UTC)
        if historico is not None and len(historico) and "resultado_macro" in historico:
            self._ajustar(historico)

    def _ajustar(self, df: pd.DataFrame) -> None:
        base = df.dropna(subset=["resultado_macro"])
        grupos = base.groupby(list(CHAVE), dropna=False)["resultado_macro"].agg(["mean", "count"])
        for chave, linha in grupos.iterrows():
            if linha["count"] >= MIN_GRUPO:
                c = tuple(chave)
                self._tabela[(bool(c[0]), bool(c[1]), bool(c[2]), c[3])] = float(linha["mean"])
        for flag in FLAGS_SUBSIDIOS:
            com = base.loc[base[flag].astype(bool), "resultado_macro"].mean()
            sem = base.loc[~base[flag].astype(bool), "resultado_macro"].mean()
            if pd.notna(com) and pd.notna(sem):
                self._efeitos[flag] = float(com - sem)
        self._n = len(base)

    def p_exito(self, caso: CasoFeatures) -> float:
        s = caso.subsidios
        p = self._tabela.get((s.contrato, s.extrato, s.comprovante_credito, caso.sub_assunto))
        if p is None:
            p = 0.03 + 0.16 * s.n
        return float(min(max(p, 0.01), 0.99))

    def score(self, caso: CasoFeatures) -> Scores:
        s = caso.subsidios
        contribs = [
            Contribuicao(
                feature=flag, valor=getattr(s, flag),
                contribuicao=round(self._efeitos[flag] / 2 * (1 if getattr(s, flag) else -1), 3),
                descricao=f"{NOMES_SUBSIDIOS[flag]} {'presente' if getattr(s, flag) else 'ausente'}",
            )
            for flag in FLAGS_SUBSIDIOS
        ]
        if caso.sub_assunto:
            golpe = caso.sub_assunto.lower() == "golpe"
            contribs.append(Contribuicao(
                feature="sub_assunto", valor=caso.sub_assunto,
                contribuicao=round(EFEITO_GOLPE / 2 * (1 if golpe else -1), 3),
                descricao=f"Sub-assunto {caso.sub_assunto}",
            ))
        contribs.sort(key=lambda c: abs(c.contribuicao), reverse=True)
        return Scores(
            numero=caso.numero, modelo_versao=self.versao, origem="stub",
            p_exito_defesa=self.p_exito(caso),
            condenacao_p20=0.55 * caso.valor_causa, condenacao_p50=0.74 * caso.valor_causa,
            condenacao_p80=0.86 * caso.valor_causa,
            contribuicoes=contribs[:5], gerado_em=datetime.now(UTC),
        )

    def score_batch(self, casos: list[CasoFeatures]) -> list[Scores]:
        return [self.score(c) for c in casos]

    def info(self) -> ModeloInfo:
        return ModeloInfo(
            versao=self.versao, treinado_em=self._treinado_em, n_treino=self._n,
            metricas={}, importancias={k: abs(v) for k, v in self._efeitos.items()},
        )


# ---------------------------------------------------------------- extrator

_RE = {
    "cpf": re.compile(r"\b(\d{3})\.(\d{3})\.(\d{3})-(\d{2})\b"),
    "oab": re.compile(r"OAB\s*[/\-]?\s*([A-Z]{2})?\s*(?:n[º°.]?\s*)?([\d.]{3,7})", re.IGNORECASE),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "telefone": re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b"),
    "idade": re.compile(r"\b(\d{2,3})\s+anos\b", re.IGNORECASE),
    "valor_causa": re.compile(
        r"(?:valor\s+da\s+causa|causa\s+o\s+valor)[^\d]{0,60}?([\d.]+,\d{2})", re.IGNORECASE
    ),
    "comarca": re.compile(r"comarca\s+d[eao]s?\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁ-ú]+(?:\s+(?:d[eao]s?\s+)?[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁ-ú]+)*)"),
    "autor": re.compile(
        r"(?:autor(?:a)?|requerente|reclamante|demandante)\s*[:\-–]?\s*\n?\s*"
        r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç]+){1,5})",
        re.IGNORECASE,
    ),
}
_SINAIS = (
    ("CREDITO_CONTA_TERCEIRO", r"conta\s+de\s+terceiro|terceiro[s]?\s+desconhecid|n[aã]o\s+(?:é|e)\s+(?:de\s+)?(?:sua\s+)?titularidade|conta\s+que\s+n[aã]o\s+(?:lhe\s+)?pertence", "alta"),
    ("BOLETIM_OCORRENCIA", r"boletim\s+de\s+ocorr[êe]ncia|\bB\.?O\.?\b", "media"),
    ("RECLAMACAO_BACEN", r"\bbacen\b|banco\s+central", "media"),
    ("ASSINATURA_DIVERGENTE", r"assinatura[s]?\s+(?:divergente|falsa|n[aã]o\s+(?:é|e)\s+(?:sua|d[oa]\s+autor))", "alta"),
)
_PEDIDOS = (
    (r"inexist[êe]ncia|declara", "Declaração de inexistência do débito"),
    (r"danos?\s+mora", "Indenização por danos morais"),
    (r"repeti[çc][ãa]o|em\s+dobro|devolu[çc][ãa]o", "Repetição do indébito"),
    (r"tutela|liminar|suspens[ãa]o\s+dos\s+descontos", "Tutela de urgência para suspender os descontos"),
)


def texto_dos_arquivos(pasta: Path, max_paginas: int = 8) -> str:
    """Concatena o texto de .txt e .pdf (pypdf, primeiras páginas). Falha de leitura vira vazio."""
    partes: list[str] = []
    for arq in sorted(pasta.glob("*")) if pasta.is_dir() else []:
        try:
            if arq.suffix.lower() == ".txt":
                partes.append(arq.read_text(encoding="utf-8", errors="ignore"))
            elif arq.suffix.lower() == ".pdf":
                from pypdf import PdfReader

                leitor = PdfReader(str(arq))
                partes.extend((pg.extract_text() or "") for pg in leitor.pages[:max_paginas])
        except Exception as exc:  # noqa: BLE001 - PDF ruim não derruba o ingest
            log.warning("não li %s: %s", arq.name, exc)
    return "\n".join(partes)


class StubExtrator:
    origem = "stub"

    def extrair(self, processo_dir: Path, numero: str) -> DadosExtraidos:
        texto = texto_dos_arquivos(processo_dir / "autos")
        subs = subsidios_por_arquivos(p.name for p in (processo_dir / "subsidios").glob("*"))
        plano = re.sub(r"[ \t]+", " ", texto)

        cpf = _RE["cpf"].search(plano)
        idade_m = _RE["idade"].search(plano)
        idade = int(idade_m.group(1)) if idade_m else None
        autor_m = _RE["autor"].search(plano)
        oab_m = _RE["oab"].search(plano)
        email_m = _RE["email"].search(plano)
        tel_m = _RE["telefone"].search(plano)
        valor_m = _RE["valor_causa"].search(plano)
        comarca_m = _RE["comarca"].search(plano)

        sinais: list[SinalAlerta] = []
        if idade is not None and idade >= 60:
            sinais.append(SinalAlerta(codigo="IDOSO", descricao=f"Autor com {idade} anos",
                                      severidade="media", fonte="autos"))
        for codigo, padrao, sev in _SINAIS:
            if re.search(padrao, plano, re.IGNORECASE):
                sinais.append(SinalAlerta(codigo=codigo, descricao=CODIGOS_SINAIS[codigo],
                                          severidade=sev, fonte="autos"))  # type: ignore[arg-type]
        if not subs.contrato:
            sinais.append(SinalAlerta(codigo="SEM_CONTRATO", descricao=CODIGOS_SINAIS["SEM_CONTRATO"],
                                      severidade="alta", fonte="subsidios"))
        digital = bool(re.search(r"aplicativo|\bapp\b|internet\s*banking|celular", plano, re.IGNORECASE))
        if digital and idade is not None and idade >= 60:
            sinais.append(SinalAlerta(codigo="CANAL_DIGITAL_SEM_PERFIL",
                                      descricao=CODIGOS_SINAIS["CANAL_DIGITAL_SEM_PERFIL"],
                                      severidade="media", fonte="autos"))
        codigos = {s.codigo for s in sinais}

        pedidos = [nome for padrao, nome in _PEDIDOS if re.search(padrao, plano, re.IGNORECASE)]
        resumo = re.sub(r"\s+", " ", plano).strip()[:500] or "Autos sem texto extraível."
        return DadosExtraidos(
            numero=numero, origem="stub", modelo=None,
            autor=Pessoa(
                nome=autor_m.group(1).strip().title() if autor_m else None,
                cpf_mascarado=f"***.***.{cpf.group(3)}-{cpf.group(4)}" if cpf else None,
                idade=idade,
            ),
            advogado_autor=Advogado(
                oab=f"{oab_m.group(1) or ''} {oab_m.group(2)}".strip() if oab_m else None,
                email=email_m.group(0) if email_m else None,
                telefone=tel_m.group(0) if tel_m else None,
            ),
            comarca=comarca_m.group(1).strip() if comarca_m else None,
            uf=cnj.uf_do_numero(numero),
            valor_causa=parse_brl(valor_m.group(1)) if valor_m else None,
            pedidos=pedidos,
            contrato=ContratoInfo(
                canal="app" if digital else "desconhecido",
                credito_conta_terceiro="CREDITO_CONTA_TERCEIRO" in codigos or None,
            ),
            sinais_alerta=sinais, resumo_fatos=resumo, confianca=0.3, gerado_em=datetime.now(UTC),
        )

    def analisar(self, caso: CasoFeatures, dados: DadosExtraidos, scores: Scores) -> Analise:
        presentes = [NOMES_SUBSIDIOS[k] for k in caso.subsidios.presentes()]
        ausentes = [NOMES_SUBSIDIOS[k] for k in caso.subsidios.ausentes()]
        fortes = [f"{p} disponível para juntar à defesa" for p in presentes]
        fracos = [f"Sem {a.lower()} para comprovar a contratação" for a in ausentes]
        fracos += [s.descricao for s in dados.sinais_alerta if s.severidade == "alta"]
        riscos = [s.descricao for s in dados.sinais_alerta]
        tese = (
            "Contratação fraudulenta por terceiro: o autor nega ter contratado e pede a "
            "declaração de inexistência do débito, a devolução dos valores e danos morais."
        )
        texto = (
            f"Probabilidade estimada de êxito na defesa: {scores.p_exito_defesa:.0%} "
            f"({'modelo' if scores.origem == 'modelo' else 'estimativa por lookup no histórico'}). "
            f"Subsídios presentes: {', '.join(presentes) or 'nenhum'}. "
            f"Ausentes: {', '.join(ausentes) or 'nenhum'}. "
            + (f"Sinais nos autos: {'; '.join(riscos)}. " if riscos else "")
            + f"Se perder, a condenação mediana esperada é {brl(scores.condenacao_p50)}."
        )
        return Analise(numero=caso.numero, origem="stub", pontos_fortes_banco=fortes,
                       pontos_fracos_banco=fracos, tese_provavel_autor=tese, riscos=riscos, texto=texto)

    def redigir(self, caso: CasoFeatures, dados: DadosExtraidos, rec: Recomendacao) -> Minutas:
        autor = dados.autor.nome or "a parte autora"
        adv = dados.advogado_autor
        contato = adv.nome or (f"advogado(a) OAB {adv.oab}" if adv.oab else "advogado(a) da parte autora")
        valor = brl(rec.valor_sugerido or 0)
        proposta = (
            f"PROPOSTA DE ACORDO — processo {caso.numero}\n\n"
            f"O Banco UFMG, sem reconhecer a procedência dos pedidos, propõe a {autor} o pagamento "
            f"de {valor} em parcela única, em até 15 dias úteis após a homologação, mediante: "
            f"(i) declaração de inexigibilidade do contrato discutido; (ii) quitação ampla e "
            f"irrevogável quanto ao objeto da ação; (iii) renúncia a recursos; (iv) cada parte "
            f"arcando com os honorários dos próprios patronos.\n\n"
            f"Banda autorizada pela política: {brl(rec.valor_min or 0)} a {brl(rec.valor_max or 0)}."
        ) if rec.tipo == "acordo" else ""
        roteiro = (
            f"ROTEIRO DE DEFESA — processo {caso.numero}\n\n"
            f"1. Preliminares: legitimidade e interesse; impugnar a gratuidade se cabível.\n"
            f"2. Mérito: juntar {', '.join(NOMES_SUBSIDIOS[k] for k in caso.subsidios.presentes()) or 'os subsídios disponíveis'}; "
            f"demonstrar a regularidade da contratação e o crédito em favor do autor.\n"
            f"3. Danos morais: ausência de ato ilícito; subsidiariamente, redução do quantum.\n"
            f"4. Pedido: improcedência total; subsidiariamente, compensação com valores creditados.\n"
            f"Probabilidade de êxito estimada: {rec.scores_snapshot.p_exito_defesa:.0%}."
        )
        mensagem = (
            f"Prezado(a) {contato},\n\nRepresentamos o Banco UFMG no processo {caso.numero}. "
            f"Gostaríamos de tratar de uma proposta de acordo para encerrar o litígio de forma célere. "
            f"Poderia indicar um horário para conversarmos ainda esta semana?\n\nAtenciosamente,"
        ) if rec.tipo == "acordo" else ""
        return Minutas(numero=caso.numero, politica_id=rec.politica_id, origem="stub",
                       proposta_acordo=proposta, roteiro_defesa=roteiro, mensagem_contato=mensagem)
