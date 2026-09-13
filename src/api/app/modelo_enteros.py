"""Adapter: o modelo do engine de P1 (`enteros`) visto pelo portal como `ModeloScores`.

O engine dá P(perda) (média entre tabela de segmentos e logística calibrada) e os quantis de
condenação por UF × sub-assunto; a política operacional continua em `core.politica`. Se `enteros`
ou `models/*.json` não estiverem disponíveis, `plugins.carregar_modelo` cai no stub.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from core.caso import CasoFeatures
from core.modelo import CalibracaoBin, Contribuicao, ModeloInfo, Scores

# flag do portal (core.caso.Subsidios) -> flag do engine (enteros.config.DOCS)
FLAGS_ENTEROS: dict[str, str] = {
    "contrato": "contrato", "extrato": "extrato", "comprovante_credito": "comprovante",
    "dossie": "dossie", "demonstrativo_divida": "demonstrativo", "laudo_referenciado": "laudo",
}
QUANTIS = ("p20", "p50", "p80")
log = logging.getLogger(__name__)
# volta do nome do engine para a flag do portal
FLAGS_PORTAL: dict[str, str] = {v: k for k, v in FLAGS_ENTEROS.items()}


def _clip(v: float) -> float:
    return float(min(max(v, 0.0), 1.0))


class ModeloEnteros:
    def __init__(self) -> None:
        from enteros import config as cfg
        from enteros.policy.engine import Engine

        self._cfg = cfg
        self._eng = Engine.carregar()
        self.versao = f"enteros-{self._eng.modelo.versao}"

    def _entrada(self, caso: CasoFeatures) -> tuple[str, dict[str, int], str]:
        flags = {alvo: int(getattr(caso.subsidios, nosso)) for nosso, alvo in FLAGS_ENTEROS.items()}
        sub = caso.sub_assunto if caso.sub_assunto in self._cfg.SUB_ASSUNTOS else self._cfg.SUB_GOLPE
        uf = caso.uf if caso.uf in self._cfg.UFS else ""  # UF desconhecida cai na referência do modelo
        return sub, flags, uf

    def _instrucao(self, caso: CasoFeatures, sub: str, uf: str) -> tuple[bool, list[str], dict[str, float]]:
        """Subsídios ausentes que compensa pedir antes de acordar, pelo valor esperado da informação.

        Precisa da recomendação do engine (o EVSI depende de custo de busca e de atraso, não só de p).
        Falha do engine não pode derrubar o score: sem instrução, o portal decide como antes.
        """
        from enteros.schemas import CaseFeatures, DocsStatus

        try:
            docs = DocsStatus(**{alvo: (self._cfg.STATUS_PRESENTE if getattr(caso.subsidios, nosso)
                                        else self._cfg.STATUS_AUSENTE)
                                 for nosso, alvo in FLAGS_ENTEROS.items()})
            rec = self._eng.recomendar(CaseFeatures(
                numero=caso.numero, uf=uf or self._cfg.UFS[0], sub_assunto=sub,
                valor_causa=caso.valor_causa, docs=docs,
            ))
        except Exception:  # noqa: BLE001 - engine indisponível só desliga a instrução
            log.warning("engine não recomendou para %s; sem instrução de subsídios", caso.numero)
            return False, [], {}
        pedir = [FLAGS_PORTAL[d] for d in rec.docs_a_solicitar if d in FLAGS_PORTAL]
        evsi = {FLAGS_PORTAL[d]: round(float(v), 2) for d, v in rec.evsi_por_doc.items() if d in FLAGS_PORTAL}
        return rec.decisao == self._cfg.DECISAO_INSTRUIR and bool(pedir), pedir, evsi

    def score(self, caso: CasoFeatures) -> Scores:
        sub, flags, uf = self._entrada(caso)
        p_perda, _, _ = self._eng.p_perda(sub, flags, uf)
        r = self._eng.ratio.para(uf, sub)
        instruir, pedir, evsi = self._instrucao(caso, sub, uf)
        contribs = [
            Contribuicao(
                feature=c["feature"], valor=c["valor"],
                contribuicao=round(-float(c["contribuicao"]), 3),  # engine: + = risco; portal: + = êxito
                descricao=f"{c['feature']}: {c['valor']}",
            )
            for c in self._eng.modelo.contribuicoes(sub, flags, uf)
        ]
        return Scores(
            numero=caso.numero, modelo_versao=self.versao, origem="modelo",
            p_exito_defesa=_clip(1.0 - p_perda),
            condenacao_p20=r["p20"] * caso.valor_causa, condenacao_p50=r["p50"] * caso.valor_causa,
            condenacao_p80=r["p80"] * caso.valor_causa, contribuicoes=contribs, gerado_em=datetime.now(UTC),
            instruir_recomendado=instruir, docs_a_solicitar=pedir, evsi_por_doc=evsi,
        )

    def score_batch(self, casos: list[CasoFeatures]) -> list[Scores]:
        return [self.score(c) for c in casos]

    def p_exito_lote(self, df: pd.DataFrame) -> np.ndarray:
        """P(êxito) pela logística para um DataFrame nas colunas do portal (flags snake_case, sub_assunto, uf)."""
        base = pd.DataFrame({alvo: df[nosso].astype(int).to_numpy() for nosso, alvo in FLAGS_ENTEROS.items()})
        base["sub_assunto"] = df["sub_assunto"].to_numpy()
        base["uf"] = df["uf"].to_numpy()
        return 1.0 - self._eng.modelo.p_perda_lote(base)

    def quantis_lote(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        """Condenação p20/p50/p80 (R$) por linha, pela razão condenação/causa de cada UF × sub-assunto."""
        pares = df[["uf", "sub_assunto"]].astype(str)
        chaves = pares["uf"] + "|" + pares["sub_assunto"]
        cache = {k: self._eng.ratio.para(*k.split("|", 1)) for k in chaves.unique()}
        causa = df["valor_causa"].to_numpy(dtype=float)
        return {q: np.array([cache[k][q] for k in chaves]) * causa for q in QUANTIS}

    def info(self) -> ModeloInfo:
        m = self._eng.modelo
        treinado = datetime.now(UTC)
        if data := re.search(r"(\d{8})$", m.versao):
            treinado = datetime.strptime(data.group(1), "%Y%m%d").replace(tzinfo=UTC)
        calibracao = [
            CalibracaoBin(
                p_min=_clip(1.0 - c["p_max"]), p_max=_clip(1.0 - c["p_min"]), n=int(c["n"]),
                p_prevista_media=_clip(1.0 - c["p_prevista"]), taxa_exito_real=_clip(1.0 - c["taxa_real"]),
            )
            for c in reversed(m.calibracao)
        ]
        return ModeloInfo(
            versao=self.versao, treinado_em=treinado, n_treino=int(m.metricas.get("n_treino", 0)),
            metricas={k: float(v) for k, v in m.metricas.items()}, calibracao=calibracao,
            importancias={col: abs(float(coef)) for col, coef in zip(m.colunas, m.coef, strict=True)
                          if not col.startswith("uf_")},
        )
