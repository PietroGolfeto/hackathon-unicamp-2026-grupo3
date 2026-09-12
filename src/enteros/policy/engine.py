"""Engine de decisão: probabilidade → valor esperado de litigar → escada de oferta → faixa/decisão.

Determinístico, sem LLM, < 1 ms por caso. Toda constante vem de policy.yaml e dos modelos em models/.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from enteros import config as cfg
from enteros.policy.model import ModeloPerda, SegmentTable
from enteros.policy.negotiation import decompor, escada, ev_acordo
from enteros.policy.params import Politica, carregar_politica
from enteros.policy.ratio import RatioCondenacao
from enteros.schemas import CaseFeatures, Recomendacao

SINAL_CONTA_TERCEIRO = "CREDITO_CONTA_TERCEIRO"
SINAL_LIVENESS = "LIVENESS_AUSENTE_CANAL_DIGITAL"


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
        """Média entre tabela de segmentos e logística; intervalo = min/max dos dois (discordância = incerteza)."""
        p_seg, n = self.segmentos.p_perda(sub, flags, uf)
        p_log = self.modelo.p_perda(sub, flags, uf)
        p = 0.5 * (p_seg + p_log) if n >= 30 else p_log
        return float(p), (float(min(p_seg, p_log)), float(max(p_seg, p_log))), n

    def ev_defesa(self, p: float, uf: str, sub: str, valor_causa: float) -> tuple[float, dict]:
        c = self.politica.custos
        r = self.ratio.para(uf, sub)
        cond_media = r["media"] * valor_causa
        custo_se_perde = cond_media * (1 + c.honorarios_sucumbencia_pct) * c.fator_tempo + c.custas_pct_valor_causa * valor_causa
        ev = c.custo_escritorio_defesa + p * custo_se_perde
        return float(ev), {"media": cond_media, "p20": r["p20"] * valor_causa, "p50": r["p50"] * valor_causa,
                           "p80": r["p80"] * valor_causa}

    def voi(self, caso: CaseFeatures, flags: dict[str, int], ev_atual: float) -> dict[str, float]:
        """Queda do EV de litigar se cada subsídio preditivo ausente fosse obtido."""
        out: dict[str, float] = {}
        for d in cfg.DOCS_PREDITIVOS:
            if flags[d] == 0:
                f2 = {**flags, d: 1}
                p2, _, _ = self.p_perda(caso.sub_assunto, f2, caso.uf)
                ev2, _ = self.ev_defesa(p2, caso.uf, caso.sub_assunto, caso.valor_causa)
                out[d] = round(max(ev_atual - ev2, 0.0), 2)
        return out

    # ---------- decisão ----------
    def recomendar(self, caso: CaseFeatures) -> Recomendacao:
        pol = self.politica
        flags, regras = self.flags_efetivos(caso)
        sinais = self.sinais(caso)
        p, intervalo, _ = self.p_perda(caso.sub_assunto, flags, caso.uf)
        ev_def, cond = self.ev_defesa(p, caso.uf, caso.sub_assunto, caso.valor_causa)
        esc = escada(caso, ev_def, pol.oferta, pol.custos)
        ev_aco = ev_acordo(esc, ev_def, pol.custos)
        voi = self.voi(caso, flags, ev_def)
        motivos: list[str] = []

        forcado = [s for s in sinais if s in pol.regras_duras.sinais_forcam_acordo]
        if forcado:
            regras += [f"SINAL_FORCA_ACORDO:{s}" for s in forcado]

        if forcado or p > pol.faixas.limiar_vermelha:
            faixa, decisao = cfg.FAIXA_VERMELHA, cfg.DECISAO_ACORDO
            motivos.append(f"Probabilidade de perda {p:.0%} acima do limiar de {pol.faixas.limiar_vermelha:.0%}."
                           if not forcado else f"Sinal que força acordo: {', '.join(forcado)}.")
        elif p < pol.faixas.limiar_verde:
            faixa, decisao = cfg.FAIXA_VERDE, cfg.DECISAO_DEFESA
            motivos.append(f"Probabilidade de perda {p:.0%} abaixo do limiar de {pol.faixas.limiar_verde:.0%}.")
        else:
            faixa = cfg.FAIXA_AMARELA
            decisao = cfg.DECISAO_ACORDO if ev_aco < ev_def else cfg.DECISAO_DEFESA
            motivos.append(f"Zona intermediária (p={p:.0%}): custo esperado de litigar R$ {ev_def:,.0f} × "
                           f"de propor acordo R$ {ev_aco:,.0f} → {decisao}.")

        # instruir antes de acordar: se recuperar contrato/extrato vale mais que o custo de buscar e é relevante
        docs_solicitar = [d for d, g in voi.items()
                          if g >= pol.faixas.voi_min_pct_causa * caso.valor_causa and g > pol.custos.custo_recuperar_subsidio]
        decisao_fallback = None
        if decisao == cfg.DECISAO_ACORDO and docs_solicitar and not forcado:
            decisao_fallback = cfg.DECISAO_ACORDO
            decisao = cfg.DECISAO_INSTRUIR
            faixa = cfg.FAIXA_AMARELA
            nomes = ", ".join(cfg.NOME_DOC[d] for d in docs_solicitar)
            motivos.append(f"Antes de propor acordo, solicitar ao banco: {nomes} "
                           f"(prazo {pol.faixas.prazo_instrucao_dias} dias; ganho esperado R$ {sum(voi[d] for d in docs_solicitar):,.0f}). "
                           f"Se não vier, seguir para acordo.")
            regras.append("INSTRUIR_ANTES_DE_ACORDAR")

        if decisao == cfg.DECISAO_DEFESA:
            esc_out, dec_out, ev_aco_out = None, None, ev_aco
            motivos.append(f"Custo esperado de litigar: R$ {ev_def:,.0f} (condenação esperada R$ {cond['media']*p:,.0f}).")
        else:
            esc_out, dec_out, ev_aco_out = esc, decompor(caso, esc.alvo), ev_aco
            motivos.append(f"Escada: abrir em R$ {esc.abertura:,.0f}, alvo R$ {esc.alvo:,.0f} "
                           f"(aceite estimado {esc.p_aceite_alvo:.0%}), teto R$ {esc.teto:,.0f} = "
                           f"{1-pol.oferta.margem_teto:.0%} do custo esperado de litigar.")
        if caso.contradicoes:
            motivos.append("Contradições petição × subsídios: " + "; ".join(caso.contradicoes))

        economia = max(ev_def - (ev_aco if decisao != cfg.DECISAO_DEFESA else ev_def), 0.0)
        return Recomendacao(
            decisao=decisao, faixa=faixa, decisao_se_nao_recuperar=decisao_fallback,
            p_perda=round(p, 4), p_perda_intervalo=(round(intervalo[0], 4), round(intervalo[1], 4)),
            condenacao_esperada=round(cond["media"] * p, 2), condenacao_p20=round(cond["p20"], 2),
            condenacao_p50=round(cond["p50"], 2), condenacao_p80=round(cond["p80"], 2),
            ev_defesa=round(ev_def, 2), ev_acordo=round(ev_aco_out, 2), economia_esperada=round(economia, 2),
            escada=esc_out, decomposicao=dec_out, voi_por_doc=voi, docs_a_solicitar=docs_solicitar,
            motivos=motivos, regras_acionadas=regras,
            contribuicoes=self.modelo.contribuicoes(caso.sub_assunto, flags, caso.uf),
            versao_politica=pol.versao, versao_modelo=self.modelo.versao,
        )


@lru_cache(maxsize=1)
def engine_padrao() -> Engine:
    return Engine.carregar()
