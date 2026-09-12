"""Stub de P1. Existe desde a hora 1 para a API funcionar ponta a ponta sem o time.

StubModelo: P(êxito) por lookup (contrato, extrato, comprovante, sub_assunto) no histórico em
memória; sem histórico, 0,03 + 0,16·n_docs. Condenação 0,55/0,74/0,86 × valor da causa.

Não há stub de extração (decisão 27): sem P3 plugado, nada é inferido do conteúdo dos documentos.
`plugins.carregar_extrator` devolve None e o portal mostra só flags, scores e recomendação.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from core.caso import NOMES_SUBSIDIOS, CasoFeatures
from core.colunas import FLAGS_SUBSIDIOS
from core.modelo import Contribuicao, ModeloInfo, Scores

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
