"""Engine de decisão: probabilidade → custo esperado de litigar → escada de oferta → três ações por valor esperado.

Determinístico, sem LLM, < 1 ms por caso. Toda constante vem de policy.yaml e dos modelos em models/.

Ações: defesa, acordo e instruir(S) — pedir ao banco o conjunto S de subsídios ausentes antes de propor acordo.
    V(p)            = min(EV_defesa(p), EV_acordo(p))
    p_falha_d       = (p − q_d·p_com_d) / (1 − q_d)   (probabilidade total: buscar e não achar é notícia ruim)
    EV_instruir(S)  = custo_busca(S) + custo_atraso + Σ_outcomes P(outcome)·V(p_outcome)
    EVSI(S)         = V(p) − EV_instruir(S)           (> 0 → vale esperar os documentos)
Para conjuntos, os deslocamentos em log-odds de cada documento (achado → p_com_d; não achado → p_falha_d) somam,
com buscas independentes entre documentos — premissa declarada (H12). Um documento sozinho raramente vira a
decisão de um caso sem contrato nem extrato; os dois juntos, sim.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from functools import lru_cache
from pathlib import Path

import numpy as np

from enteros import config as cfg
from enteros.policy import custos as cst
from enteros.policy.model import ModeloPerda, SegmentTable
from enteros.policy.negotiation import decompor, escada, ev_acordo
from enteros.policy.params import Politica, carregar_politica
from enteros.policy.ratio import RatioCondenacao
from enteros.schemas import CaseFeatures, Escada, Recomendacao

SINAL_CONTA_TERCEIRO = "CREDITO_CONTA_TERCEIRO"
SINAL_LIVENESS = "LIVENESS_AUSENTE_CANAL_DIGITAL"
REGRA_INSTRUIR = "INSTRUIR_ANTES_DE_ACORDAR"
REGRA_SENSIVEL = "DECISAO_SENSIVEL_REVISAR"
REGRA_FORTALECER = "SOLICITAR_EM_PARALELO_A_DEFESA"


def _logit(p: float) -> float:
    p = min(max(p, 1e-9), 1 - 1e-9)
    return float(np.log(p / (1 - p)))


@dataclass
class Avaliacao:
    """Custos esperados de um caso para uma probabilidade de perda."""

    p: float
    ev_defesa: float
    escada: Escada
    ev_acordo: float

    @property
    def valor(self) -> float:
        return min(self.ev_defesa, self.ev_acordo)

    @property
    def acordo_e_melhor(self) -> bool:
        return self.ev_acordo < self.ev_defesa


@dataclass
class Engine:
    politica: Politica
    segmentos: SegmentTable
    modelo: ModeloPerda
    ratio: RatioCondenacao

    @classmethod
    def carregar(cls, politica: Path | None = None) -> "Engine":
        return cls(
            politica=carregar_politica(politica),
            segmentos=SegmentTable.from_json(cfg.ARQ_SEGMENTOS),
            modelo=ModeloPerda.from_json(cfg.ARQ_MODELO_PERDA),
            ratio=RatioCondenacao.from_json(cfg.ARQ_RATIO),
        )

    # ---------- blocos ----------
    def flags_efetivos(self, caso: CaseFeatures) -> tuple[dict[str, int], list[str]]:
        """Presença efetiva dos subsídios: inconsistente = ausente; sinais da IA rebaixam o extrato."""
        flags = caso.docs.flags()
        regras: list[str] = []
        if self.politica.regras_duras.inconsistente_vale_ausente:
            for d in cfg.DOCS:
                if getattr(caso.docs, d) == cfg.STATUS_INCONSISTENTE:
                    regras.append(f"{d.upper()}_INCONSISTENTE_VALE_AUSENTE")
        if caso.conta_deposito_titular_autor is False and flags["extrato"]:
            flags["extrato"] = 0
            regras.append("EXTRATO_REBAIXADO_CONTA_TERCEIRO")
        return flags, regras

    def sinais(self, caso: CaseFeatures) -> list[str]:
        s = set(caso.red_flags)
        if caso.conta_deposito_titular_autor is False:
            s.add(SINAL_CONTA_TERCEIRO)
        if caso.liveness_presente is False:
            s.add(SINAL_LIVENESS)
        return sorted(s)

    def p_perda(self, sub: str, flags: dict[str, int], uf: str) -> tuple[float, tuple[float, float], int]:
        """p da logística, intervalo de credibilidade de 95% (Laplace; incerteza do modelo) e n da célula observada."""
        p = self.modelo.p_perda(sub, flags, uf)
        lo, hi = self.modelo.p_perda_intervalo(sub, flags, uf)
        _, n = self.segmentos.p_perda(sub, flags, uf)
        return float(p), (float(lo), float(hi)), n

    def saldo_no_ev(self, caso: CaseFeatures) -> float:
        if self.politica.oferta.saldo_devedor_no_acordo and caso.saldo_devedor:
            return float(caso.saldo_devedor)
        return 0.0

    def severidade(self, uf: str, sub: str, valor_causa: float) -> dict[str, float]:
        r = self.ratio.para(uf, sub)
        return {
            "media": r["media"] * valor_causa, "p20": r["p20"] * valor_causa, "p50": r["p50"] * valor_causa,
            "p80": r["p80"] * valor_causa, "p_procedencia": r.get("p_procedencia", float("nan")),
            "custo_se_perde": float(cst.custo_se_perde(r["media"], valor_causa, self.politica.custos)),
        }

    def ev_defesa(self, p: float, uf: str, sub: str, valor_causa: float, saldo: float = 0.0) -> tuple[float, dict]:
        sev = self.severidade(uf, sub, valor_causa)
        return float(cst.ev_defesa(p, sev["custo_se_perde"], self.politica.custos, saldo)), sev

    def avaliar(self, caso: CaseFeatures, p: float, saldo: float) -> Avaliacao:
        ev_def, _ = self.ev_defesa(p, caso.uf, caso.sub_assunto, caso.valor_causa, saldo)
        esc = escada(caso, ev_def, self.politica.oferta, self.politica.custos, saldo)
        return Avaliacao(p=p, ev_defesa=ev_def, escada=esc, ev_acordo=ev_acordo(esc, ev_def, self.politica.custos, saldo))

    def breakeven(self, caso: CaseFeatures, esc: Escada, saldo: float) -> float:
        sev = self.severidade(caso.uf, caso.sub_assunto, caso.valor_causa)
        return float(cst.breakeven(esc.alvo, esc.p_aceite_alvo, sev["custo_se_perde"], self.politica.custos, saldo))

    def analise_subsidios(self, caso: CaseFeatures, flags: dict[str, int], atual: Avaliacao, saldo: float) -> tuple[dict[str, dict], dict | None]:
        """Por subsídio preditivo ausente: chance de localizar, p se achar / se não achar, ganho e EVSI isolado.
        Devolve também o melhor conjunto a pedir (maior EVSI entre todos os subconjuntos dos ausentes)."""
        pol, c = self.politica, self.politica.custos
        atraso = (c.fator_atraso(pol.faixas.prazo_instrucao_dias) - 1) * atual.ev_defesa
        z0 = _logit(atual.p)
        docs: dict[str, dict] = {}
        for d in cfg.DOCS_PREDITIVOS:
            if flags[d]:
                continue
            q = self.modelo.q_doc_para(d, flags, pol.faixas.q_doc_padrao)
            p_com = self.modelo.p_perda(caso.sub_assunto, {**flags, d: 1}, caso.uf)
            p_falha = min(max((atual.p - q * p_com) / (1 - q), atual.p), 1 - 1e-6) if q < 1 else atual.p
            com = self.avaliar(caso, p_com, saldo)
            docs[d] = {"q": q, "p_com": p_com, "p_falha": p_falha,
                       "ganho_se_encontrar": max(atual.ev_defesa - com.ev_defesa, 0.0),
                       "muda_decisao": bool(com.acordo_e_melhor != atual.acordo_e_melhor),
                       "_dz_com": _logit(p_com) - z0, "_dz_falha": _logit(p_falha) - z0}

        def ev_instruir(conjunto: tuple[str, ...]) -> tuple[float, float]:
            """Custo esperado de pedir `conjunto` e decidir depois; e P(achar todos)."""
            total = c.custo_recuperar_subsidio * len(conjunto) + atraso
            for achados in product((1, 0), repeat=len(conjunto)):
                prob = float(np.prod([docs[d]["q"] if a else 1 - docs[d]["q"] for d, a in zip(conjunto, achados, strict=True)]))
                if prob == 0.0:
                    continue
                z = z0 + sum(docs[d]["_dz_com"] if a else docs[d]["_dz_falha"] for d, a in zip(conjunto, achados, strict=True))
                total += prob * self.avaliar(caso, float(1 / (1 + np.exp(-z))), saldo).valor
            return total, float(np.prod([docs[d]["q"] for d in conjunto]))

        melhor: dict | None = None
        for k in range(1, len(docs) + 1):
            for conjunto in combinations(docs, k):
                evi, p_todos = ev_instruir(conjunto)
                evsi = atual.valor - evi
                if k == 1:
                    docs[conjunto[0]].update({"ev_instruir": evi, "evsi": evsi})
                if melhor is None or evsi > melhor["evsi"]:
                    melhor = {"docs": list(conjunto), "evsi": evsi, "ev_instruir": evi, "p_todos_encontrados": p_todos}
        for a in docs.values():
            for k in ("_dz_com", "_dz_falha"):
                a.pop(k)
            for k, v in a.items():
                if isinstance(v, float):
                    a[k] = round(v, 4 if k in ("q", "p_com", "p_falha") else 2)
        if melhor:
            melhor.update({k: round(v, 2 if k != "p_todos_encontrados" else 4) for k, v in melhor.items() if isinstance(v, float)})
        return docs, melhor

    # ---------- decisão ----------
    def recomendar(self, caso: CaseFeatures) -> Recomendacao:
        pol = self.politica
        flags, regras = self.flags_efetivos(caso)
        sinais = self.sinais(caso)
        p, intervalo, _ = self.p_perda(caso.sub_assunto, flags, caso.uf)
        saldo = self.saldo_no_ev(caso)
        atual = self.avaliar(caso, p, saldo)
        ev_def, esc, ev_aco = atual.ev_defesa, atual.escada, atual.ev_acordo
        sev = self.severidade(caso.uf, caso.sub_assunto, caso.valor_causa)
        p_star = self.breakeven(caso, esc, saldo)
        analise, instrucao = self.analise_subsidios(caso, flags, atual, saldo)
        motivos: list[str] = []

        forcado = [s for s in sinais if s in pol.regras_duras.sinais_forcam_acordo]
        if forcado:
            regras += [f"SINAL_FORCA_ACORDO:{s}" for s in forcado]

        motivos.append(f"Probabilidade de perda {p:.0%} (IC95 {intervalo[0]:.0%}–{intervalo[1]:.0%}, incerteza do modelo); "
                       f"ponto de indiferença entre defender e acordar: {p_star:.0%}.")
        if forcado or p > pol.faixas.limiar_vermelha:
            faixa, decisao = cfg.FAIXA_VERMELHA, cfg.DECISAO_ACORDO
            motivos.append(f"Sinal que força acordo: {', '.join(forcado)}." if forcado
                           else f"Perda acima do limiar de {pol.faixas.limiar_vermelha:.0%}: acordo sem comparar custos.")
        elif p < pol.faixas.limiar_verde:
            faixa, decisao = cfg.FAIXA_VERDE, cfg.DECISAO_DEFESA
            motivos.append(f"Perda abaixo do limiar de {pol.faixas.limiar_verde:.0%}: defesa clara.")
        else:
            faixa = cfg.FAIXA_AMARELA
            decisao = cfg.DECISAO_ACORDO if atual.acordo_e_melhor else cfg.DECISAO_DEFESA
            motivos.append(f"Zona intermediária: custo esperado de litigar R$ {ev_def:,.0f} × de propor acordo "
                           f"R$ {ev_aco:,.0f} → {decisao}.")

        # instruir por valor esperado da informação: só faz sentido adiar um acordo
        minimo = pol.faixas.evsi_min_pct_causa * caso.valor_causa
        vale_instruir = instrucao is not None and instrucao["evsi"] > 0 and instrucao["evsi"] >= minimo
        docs_solicitar = list(instrucao["docs"]) if vale_instruir else []
        fortalecem = sorted((d for d, a in analise.items() if a["ganho_se_encontrar"] > pol.custos.custo_recuperar_subsidio),
                            key=lambda d: -analise[d]["ganho_se_encontrar"])
        ev_instruir = instrucao["ev_instruir"] if instrucao else None
        decisao_fallback = None
        if decisao == cfg.DECISAO_ACORDO and vale_instruir and not forcado:
            decisao_fallback = cfg.DECISAO_ACORDO
            decisao, faixa = cfg.DECISAO_INSTRUIR, cfg.FAIXA_AMARELA
            regras.append(REGRA_INSTRUIR)
            nomes = ", ".join(f"{cfg.NOME_DOC[d]} (chance {analise[d]['q']:.0%})" for d in docs_solicitar)
            motivos.append(f"Antes de propor acordo, solicitar ao banco: {nomes}; prazo {pol.faixas.prazo_instrucao_dias} dias. "
                           f"Valor esperado da informação R$ {instrucao['evsi']:,.0f} "
                           f"(chance de localizar todos {instrucao['p_todos_encontrados']:.0%}). Se não vier, seguir para acordo.")
        elif decisao == cfg.DECISAO_DEFESA and fortalecem:
            regras.append(REGRA_FORTALECER)
            nomes = ", ".join(cfg.NOME_DOC[d] for d in fortalecem)
            motivos.append(f"Em paralelo à defesa, solicitar {nomes}: se localizado, o custo esperado de litigar cai "
                           f"R$ {sum(analise[d]['ganho_se_encontrar'] for d in fortalecem):,.0f}.")

        sensivel = bool(intervalo[0] < p_star < intervalo[1]) and not forcado
        if sensivel:
            regras.append(REGRA_SENSIVEL)
            motivos.append("Decisão sensível: o intervalo de p cruza o ponto de indiferença; revisar com o gestor.")

        if decisao == cfg.DECISAO_DEFESA:
            esc_out, dec_out = None, None
            motivos.append(f"Custo esperado de litigar: R$ {ev_def:,.0f} (condenação esperada R$ {sev['media'] * p:,.0f}; "
                           f"se perder, {sev['p_procedencia']:.0%} de chance de procedência total).")
        else:
            esc_out, dec_out = esc, decompor(caso, esc.alvo)
            saldo_txt = f" + saldo baixado R$ {saldo:,.0f}" if saldo else ""
            motivos.append(f"Escada: abrir em R$ {esc.abertura:,.0f}, alvo R$ {esc.alvo:,.0f}{saldo_txt} "
                           f"(aceite estimado {esc.p_aceite_alvo:.0%}), teto R$ {esc.teto:,.0f} = "
                           f"{1 - pol.oferta.margem_teto:.0%} do custo esperado de litigar.")
        if caso.contradicoes:
            motivos.append("Contradições petição × subsídios: " + "; ".join(caso.contradicoes))

        economia = max(ev_def - (ev_aco if decisao != cfg.DECISAO_DEFESA else ev_def), 0.0)
        return Recomendacao(
            decisao=decisao, faixa=faixa, decisao_se_nao_recuperar=decisao_fallback,
            p_perda=round(p, 4), p_perda_intervalo=(round(intervalo[0], 4), round(intervalo[1], 4)),
            condenacao_esperada=round(sev["media"] * p, 2), condenacao_p20=round(sev["p20"], 2),
            condenacao_p50=round(sev["p50"], 2), condenacao_p80=round(sev["p80"], 2),
            ev_defesa=round(ev_def, 2), ev_acordo=round(ev_aco, 2), economia_esperada=round(economia, 2),
            escada=esc_out, decomposicao=dec_out,
            voi_por_doc={d: a["ganho_se_encontrar"] for d, a in analise.items()}, docs_a_solicitar=docs_solicitar,
            motivos=motivos, regras_acionadas=regras,
            contribuicoes=self.modelo.contribuicoes(caso.sub_assunto, flags, caso.uf),
            versao_politica=pol.versao, versao_modelo=self.modelo.versao,
            p_breakeven=round(p_star, 4), decisao_sensivel=sensivel,
            ev_instruir=None if ev_instruir is None else round(ev_instruir, 2),
            evsi_por_doc={d: a["evsi"] for d, a in analise.items()}, q_por_doc={d: a["q"] for d, a in analise.items()},
            analise_subsidios=analise, docs_que_fortalecem=fortalecem, instrucao=instrucao,
            p_procedencia_se_perder=None if sev["p_procedencia"] != sev["p_procedencia"] else round(sev["p_procedencia"], 4),
            saldo_no_ev=round(saldo, 2),
        )


@lru_cache(maxsize=1)
def engine_padrao() -> Engine:
    return Engine.carregar()
