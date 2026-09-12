"""Gera docs/analises/{resumo.md,resumo.json} e as figuras da demo a partir do replay e das três análises.

Nada aqui altera o modelo: lê models/*.json, policy.yaml e a base; escreve só em docs/analises/.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from enteros import config as cfg  # noqa: E402
from enteros.analise import aceite, fronteira, severidade  # noqa: E402
from enteros.analise.comum import brl  # noqa: E402
from enteros.backtest.replay import pontuar_base, resumo  # noqa: E402
from enteros.data.load import carregar_base  # noqa: E402
from enteros.policy.engine import Engine  # noqa: E402
from enteros.util import json_dumps  # noqa: E402

log = logging.getLogger(__name__)
COR_ACORDO, COR_DEFESA, COR_INSTRUIR = "#ffae35", "#171717", "#1565c0"


def _fig_mapa_uf(res_bt: dict, out: Path) -> None:
    t = pd.DataFrame(res_bt["por_uf"]).sort_values("economia_pct")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 6), sharey=True)
    a1.barh(t["uf"], t["economia_pct"] * 100, color=COR_ACORDO)
    for uf, v in zip(t["uf"], t["economia_pct"], strict=True):
        a1.text(v * 100 + 0.5, uf, f"{v:.0%}", va="center", fontsize=8)
    a1.set_xlabel("economia da política vs. defender tudo (%)")
    a1.set_title("Onde a política economiza mais")
    a2.barh(t["uf"], t["share_acordo"] * 100, color="#9e9e9e")
    a2.barh(t["uf"], t["perda_real"] * 100, color=COR_DEFESA, height=0.35)
    a2.set_xlabel("% de casos encaminhados a acordo (cinza) · % de perda real (preto)")
    a2.set_title("Onde o banco mais perde, mais acorda")
    for a in (a1, a2):
        a.tick_params(axis="y", labelsize=8)
    fig.suptitle("Por UF: AP e AM concentram perda, severidade e acordos; MA é o oposto", fontsize=11)
    fig.tight_layout()
    fig.savefig(out / "mapa_uf.png", dpi=150)
    plt.close(fig)


def _fig_breakeven(df: pd.DataFrame, res_bt: dict, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.4))
    bins = np.linspace(0, 1, 41)
    p = df["p_perda_hat"]
    for decisao, cor, rotulo in ((cfg.DECISAO_DEFESA, COR_DEFESA, "defender"), (cfg.DECISAO_ACORDO, COR_ACORDO, "propor acordo")):
        m = (df["decisao"] == decisao) & ~df["instruir"]
        ax.hist(p[m], bins=bins, color=cor, alpha=.9, label=f"{rotulo} ({m.mean():.0%} dos casos)")
    m = df["instruir"]
    ax.hist(p[m], bins=bins, color=COR_INSTRUIR, alpha=.85, label=f"pedir o documento antes de acordar ({m.mean():.0%})")
    pb = res_bt["breakeven"]["medio"]
    ax.axvline(pb, color="grey", ls="--", lw=1.2)
    ax.text(pb + 0.01, ax.get_ylim()[1] * 0.92, f"ponto de indiferença médio {pb:.0%}", fontsize=8, color="grey")
    ax.set_xlabel("probabilidade de o banco perder (modelo)")
    ax.set_ylabel("processos")
    ax.set_title("Quem defende, quem acorda, quem espera o documento — 60 mil processos")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "quem_acorda.png", dpi=150)
    plt.close(fig)


def _fig_instruir(res_bt: dict, out: Path) -> None:
    q = pd.DataFrame(res_bt["instruir"]["por_mult_q"])
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.bar([f"× {m}" for m in q["mult_q"]], q["share_instruir"] * 100, color=COR_INSTRUIR)
    for i, (s, e) in enumerate(zip(q["share_instruir"], q["evsi_total"], strict=True)):
        ax.text(i, s * 100 + 0.6, f"{s:.0%} dos casos\n{brl(e)} de valor", ha="center", fontsize=8)
    ax.set_ylim(0, max(q["share_instruir"]) * 100 * 1.35)
    ax.set_xlabel("chance de o back-office localizar o documento (× a observada na base)")
    ax.set_ylabel("% dos casos em que vale esperar 5 dias")
    ax.set_title("Pedir contrato/extrato antes de acordar: quanto vale esperar")
    fig.tight_layout()
    fig.savefig(out / "instruir.png", dpi=150)
    plt.close(fig)


def _md(res: dict, res_bt: dict) -> str:
    sev, fr, ac = res["severidade"], res["fronteira"], res["aceite"]
    dec = sev["decomposicao"]
    t_uf = pd.DataFrame(sev["por_uf"])
    extremos = pd.concat([t_uf.head(3), t_uf.tail(3)])
    atual, robusta, melhor = fr["atual"], fr["robusta"], fr["melhor_base"]
    linhas = [
        "# Análises para a demo (`make analises`)",
        "",
        "Só leitura dos modelos e da base; nada aqui altera o engine. Figuras em `docs/analises/*.png`.",
        "",
        "## 1. Severidade: quanto o banco paga quando perde não é constante",
        f"- Amplitude entre UFs: **{dec['amplitude'][0]:.2f} ({dec['uf_min']}) → {dec['amplitude'][1]:.2f} ({dec['uf_max']})** do valor da causa; sd entre UFs {dec['sd_entre_ufs']:.3f}.",
        f"- Procedência total paga em média {dec['media_procedencia_nacional']:.2f} do pedido em **toda** UF (sd entre UFs {dec['sd_media_procedencia_entre_ufs']:.3f}); "
        f"a parcial paga {dec['media_parcial_nacional']:.2f} em média e varia por UF (sd {dec['sd_media_parcial_entre_ufs']:.3f}); "
        f"{dec['p_procedencia_nacional']:.0%} das perdas são procedência total.",
        f"- Da variação entre UFs, **{dec['share_var_explicada_pela_parcial']:.0%}** vem do nível da parcial e **{dec['share_var_explicada_pela_mistura']:.0%}** da fatia de procedência total.",
        "",
        "| UF | perdas | condenação ÷ VC | % procedência total | média parcial | média procedência |", "|---|---|---|---|---|---|",
        *[f"| {r.uf} | {int(r.n):,} | {r.ratio:.2f} | {r.p_procedencia:.0%} | {r.media_parcial:.2f} | {r.media_procedencia:.2f} |" for r in extremos.itertuples()],
        "",
    ]
    if sev["estabilidade_resumo"]:
        e = sev["estabilidade_resumo"]
        linhas += [f"- Células UF × sub-assunto com menos de {severidade.N_CELULA_PEQUENA} perdas: {e['n_celulas_pequenas']}; sd (bootstrap) do p50 empírico "
                   f"{e['sd_p50_empirico_medio']:.3f} × {e['sd_p50_encolhido_medio']:.3f} com o encolhimento que o modelo usa — a mediana bruta de uma célula pequena pula entre as duas populações.", ""]
    linhas += [
        "![severidade_uf](severidade_uf.png)", "![severidade_distribuicao](severidade_distribuicao.png)", "",
        "## 2. Fronteira de política: quanto oferecer, e quanto risco de aceite correr",
        f"- {fr['n_configuracoes']} configurações (âncora da curva de aceite usada no desenho × teto × margem × limiar verde), cada uma avaliada sob um mundo que aceita segundo s50 ∈ {fr['mundos_s50']} (a política assume {res_bt['premissas']['oferta']['aceite_s50']}; 0,50 é estresse: a 30% do VC quase ninguém aceita).",
        f"- **Política atual**: acordo em {atual['share_acordo']:.1%} dos casos; economia {atual['economia_pct_base']:.1%} no mundo assumido, {atual['economia_pct_s50_0.40']:.1%} se s50 = 0,40 e {atual['economia_pct_pior']:.1%} no estresse.",
        f"- **Maior economia esperada**: oferta ancorada em s50 {melhor['aceite_s50']:.2f}, teto {melhor['teto_pct_causa']:.0%} do VC, margem {melhor['margem_teto']:.0%} → {melhor['economia_pct_base']:.1%} (estresse {melhor['economia_pct_pior']:.1%}).",
        f"- **Mais robusta**: oferta ancorada em s50 {robusta['aceite_s50']:.2f}, teto {robusta['teto_pct_causa']:.0%}, margem {robusta['margem_teto']:.0%} → {robusta['economia_pct_base']:.1%} esperado, {robusta['economia_pct_pior']:.1%} no estresse, {robusta['share_acordo']:.0%} de acordos.",
        f"- **Melhor na média dos mundos**: s50 {fr['melhor_media']['aceite_s50']:.2f}, teto {fr['melhor_media']['teto_pct_causa']:.0%}, margem {fr['melhor_media']['margem_teto']:.0%} → média {fr['melhor_media']['economia_pct_media']:.1%}.",
        "",
        "| knob | valor | % acordo | economia (mundo assumido) | economia (média dos mundos) | economia (estresse) |", "|---|---|---|---|---|---|",
        *[f"| {u['knob']} | {u['valor']:.2f}{' ← atual' if u['atual'] else ''} | {u['share_acordo']:.1%} | {u['economia_pct_base']:.1%} | {u['economia_pct_media']:.1%} | {u['economia_pct_pior']:.1%} |" for u in fr["um_de_cada_vez"]],
        "",
        "Leitura: os limiares das faixas quase não movem nada — a regra de custo esperado já decide. O que troca retorno por robustez é o nível da oferta: ancorar a escada num aceite mais exigente (s50 maior) oferece mais, perde um pouco no mundo assumido e protege se o autor for mais duro do que a base sugere. É a decisão do gestor, e ela não precisa de otimização sofisticada: o backtest inteiro custa milissegundos.",
        "",
        "![fronteira_politica](fronteira_politica.png)", "",
        "## 3. Curva de aceite: premissa hoje, aprendida em produção",
        f"- Prior: s50 = {ac['prior']['s50']} ± {ac['prior']['sd']} (fraco), largura uniforme. Cada acordo registrado no portal informa um intervalo do limiar do autor (aceitou no degrau k ⇒ limiar entre o degrau k−1 e o k; recusou tudo ⇒ acima do teto); {ac['exploracao']['fracao_exploracao']:.0%} dos casos recebem uma banda aleatória {ac['exploracao']['bandas_pct_causa']} para explorar.",
        "",
        "| mundo verdadeiro (s50) | acordos registrados | s50 estimado | ± | IC90 | erro |", "|---|---|---|---|---|---|",
        *[f"| {m['s50_mundo']:.2f} | {m['n']:,} | {m['s50_media']:.3f} | {m['s50_sd']:.3f} | {m['s50_ic90'][0]:.2f}–{m['s50_ic90'][1]:.2f} | {m['erro']:+.3f} |" for m in ac["marcos"]],
        "",
        "| mundo (s50, largura) | economia com a premissa | economia com a curva aprendida | % acordo (premissa → aprendida) | ganho de aprender |", "|---|---|---|---|---|",
        *[f"| ({i['s50_mundo']:.2f}, {i['largura_mundo']:.2f}) | {i['economia_pct_com_premissa']:.1%} | {i['economia_pct_com_curva_aprendida']:.1%} | {i['share_acordo_com_premissa']:.0%} → {i['share_acordo_com_curva_aprendida']:.0%} | {brl(i['ganho_de_aprender'])} |" for i in ac["impacto"]],
        "",
        "Leitura: com ~300 acordos registrados a estimativa já fica a menos de 0,02 do valor verdadeiro; o gestor recalibra a escada mensalmente com o que o portal grava.",
        "",
        "![aprendizado_aceite](aprendizado_aceite.png)", "",
        "## 4. Figuras adicionais para a demo",
        "- `mapa_uf.png` — economia e % de acordos por UF: onde o banco mais perde, mais acorda.",
        "- `quem_acorda.png` — distribuição da probabilidade de perder com as três ações e o ponto de indiferença.",
        "- `instruir.png` — quanto vale pedir contrato/extrato antes de acordar, sob três chances de localizar.",
        "- `../backtest/baselines.png` — o que aconteceu × heurísticas × limiar fixo × política × teto teórico.",
        "- `../backtest/subsidios.png` — o que cada documento muda no resultado e quanto vale recuperá-lo.",
        "- `../backtest/faixas.png` — poucos casos concentram o custo.",
    ]
    return "\n".join(linhas) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="análises agregadas e figuras para a demo")
    ap.add_argument("--raw", type=Path, default=cfg.ARQ_RAW_XLSX)
    ap.add_argument("--out", type=Path, default=cfg.DIR_ANALISES)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    base = carregar_base(args.raw)
    eng = Engine.carregar()
    df = pontuar_base(base, eng)
    res_bt = resumo(df, eng)
    args.out.mkdir(parents=True, exist_ok=True)
    log.info("severidade")
    sev = severidade.analisar(base, args.out)
    log.info("fronteira de política")
    fr = fronteira.analisar(df, eng, args.out)
    log.info("curva de aceite")
    ac = aceite.analisar(df, eng, args.out)
    _fig_mapa_uf(res_bt, args.out)
    _fig_breakeven(df, res_bt, args.out)
    _fig_instruir(res_bt, args.out)
    res = {"severidade": sev, "fronteira": fr, "aceite": ac, "politica_versao": eng.politica.versao, "modelo_versao": eng.modelo.versao}
    (args.out / "resumo.json").write_text(json_dumps(res, default=float), encoding="utf-8")
    md = _md(res, res_bt)
    (args.out / "resumo.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
