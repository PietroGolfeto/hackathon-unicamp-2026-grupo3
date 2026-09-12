"""Gera docs/backtest/resumo.{json,md} e gráficos a partir do replay. Os números do deck saem daqui."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from enteros import config as cfg  # noqa: E402
from enteros.backtest.replay import custo_politica, pontuar_base, resumo  # noqa: E402
from enteros.data.load import carregar_base  # noqa: E402
from enteros.policy.engine import Engine  # noqa: E402
from enteros.util import json_dumps  # noqa: E402

log = logging.getLogger(__name__)


def brl(v: float) -> str:
    if abs(v) >= 1e6:
        return f"R$ {v/1e6:,.1f}M"
    return f"R$ {v:,.0f}"


def _grafico_reliability(res: dict, out: Path) -> None:
    cal = pd.DataFrame(res["calibracao"])
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot([0, 1], [0, 1], "--", color="grey", lw=1)
    ax.scatter(cal["p_prevista"], cal["taxa_real"], s=cal["n"] / cal["n"].max() * 400 + 20, alpha=.8)
    ax.set_xlabel("probabilidade de perda prevista (OOF)")
    ax.set_ylabel("taxa de perda observada")
    ax.set_title(f"Calibração — AUC {res['metricas_modelo']['auc_oof']:.3f}, ECE {res['metricas_modelo']['ece_oof']:.3f}")
    fig.tight_layout()
    fig.savefig(out / "calibracao.png", dpi=150)
    plt.close(fig)


def _grafico_sensibilidade(res: dict, out: Path) -> None:
    s = pd.DataFrame(res["sensibilidade"])
    s = s[s["taxa_aceite"] != "curva"]
    fig, ax = plt.subplots(figsize=(6, 4))
    for mult, g in s.groupby("mult_oferta"):
        ax.plot(g["taxa_aceite"].astype(float), g["economia"] / 1e6, marker="o", label=f"oferta × {mult}")
    ax.axhline(0, color="grey", lw=1)
    ax.set_xlabel("taxa de aceite dos acordos")
    ax.set_ylabel("economia vs. defender tudo (R$ M)")
    ax.set_title("Sensibilidade da economia ao aceite e ao valor da oferta")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "sensibilidade.png", dpi=150)
    plt.close(fig)


def _grafico_faixas(res: dict, out: Path) -> None:
    f = pd.DataFrame(res["por_faixa"]).set_index("faixa").reindex([cfg.FAIXA_VERDE, cfa := cfg.FAIXA_AMARELA, cfg.FAIXA_VERMELHA])
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(f.index, f["share"] * 100, color=["#2e7d32", "#f9a825", "#c62828"], alpha=.85, label="% dos casos")
    ax2 = ax.twinx()
    ax2.plot(f.index, f["custo_real_defesa"] / f["custo_real_defesa"].sum() * 100, "ko-", label="% do custo real")
    ax.set_ylabel("% dos casos")
    ax2.set_ylabel("% do custo real de defender")
    ax.set_title("Faixas da política: poucos casos concentram o custo")
    fig.tight_layout()
    fig.savefig(out / "faixas.png", dpi=150)
    plt.close(fig)
    del cfa


def _grafico_voi(res: dict, out: Path) -> None:
    v = pd.DataFrame(res["voi"]).T
    e = pd.DataFrame(res["efeito_docs"]).T
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    axes[0].bar([cfg.NOME_DOC[d].split(" (")[0] for d in e.index], (e["perda_sem"] - e["perda_com"]) * 100)
    axes[0].set_ylabel("p.p. de perda a mais quando ausente")
    axes[0].set_title("Efeito observado de cada subsídio")
    axes[0].tick_params(axis="x", rotation=30)
    axes[1].bar([cfg.NOME_DOC[d].split(" (")[0] for d in v.index], v["ganho_total"] / 1e6)
    axes[1].set_ylabel("R$ M evitáveis se recuperado")
    axes[1].set_title("Valor de recuperar o subsídio ausente")
    axes[1].tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(out / "subsidios.png", dpi=150)
    plt.close(fig)


def _grafico_baselines(res: dict, out: Path) -> None:
    b = pd.DataFrame(res["baselines"]["linhas"])
    b["rotulo"] = [n.split(" (")[0].split(":")[-1].strip() for n in b["nome"]]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    cores = ["#9e9e9e"] * (len(b) - 1) + ["#2e7d32"]
    for i, nome in enumerate(b["nome"]):
        if nome.startswith("Política EV") and "curva" in nome:
            cores[i] = "#ffae35"
    ax.barh(b["rotulo"], b["custo"] / 1e6, color=cores)
    for i, (c, e) in enumerate(zip(b["custo"], b["economia_pct"], strict=True)):
        ax.text(c / 1e6 + 2, i, f"R$ {c/1e6:.0f}M  (−{e:.0%})" if e > 0 else f"R$ {c/1e6:.0f}M", va="center", fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("custo total de litigar nos 60 mil processos (R$ M)")
    ax.set_title("Baselines: o que aconteceu, heurísticas, limiar fixo, política e teto teórico")
    ax.set_xlim(0, b["custo"].max() / 1e6 * 1.25)
    fig.tight_layout()
    fig.savefig(out / "baselines.png", dpi=150)
    plt.close(fig)


MARCADOR_INICIO = "<!-- backtest:inicio -->"
MARCADOR_FIM = "<!-- backtest:fim -->"


def linhas_resumo(res: dict, h: str = "#", imagens_prefixo: str = "") -> list[str]:
    """Linhas Markdown do resumo. `h` é o prefixo do título de topo ("#" no resumo.md, "###" dentro do README)."""
    m = res["metricas_modelo"]
    img = (lambda nome: f"![{nome}]({imagens_prefixo}{nome}.png)") if imagens_prefixo is not None else (lambda nome: "")
    linhas = [
        f"{h} Backtest da política `{res['politica_versao']}` (modelo `{res['modelo_versao']}`)",
        "",
        f"Base: **{res['n_casos']:,} processos** ({'base completa da Enter' if res['base_real'] else 'CSV sintético — números ilustrativos'}).",
        "Custos reais de defender usam o resultado que de fato ocorreu (condenação, êxito, extinção); ver premissas em `docs/premissas.md`.",
        "",
        f"{h}# Modelo de probabilidade de perda (out-of-fold, 5 folds)",
        f"- AUC **{m['auc_oof']:.3f}** · Brier {m['brier_oof']:.3f} · acurácia@0,5 {m['acuracia_oof_0.5']:.1%} · ECE **{m['ece_oof']:.3f}** · taxa de perda {m['taxa_perda_base']:.1%}",
        "",
        "| p prevista | n | prevista média | observada |", "|---|---|---|---|",
        *[f"| {c['p_min']:.1f}–{c['p_max']:.1f} | {c['n']:,} | {c['p_prevista']:.3f} | {c['taxa_real']:.3f} |" for c in res["calibracao"]],
        "",
        img("calibracao"),
        "",
        f"{h}# Financeiro",
        f"- Condenações históricas: **{brl(res['condenacao_total'])}** ({brl(res['condenacao_por_caso'])} por caso; ~{brl(res['condenacao_por_caso']*5000)}/mês em 5 mil casos)",
        f"- Custo real de **defender tudo** (condenação + honorários + custas + tempo + escritório): **{brl(res['custo_defender_tudo'])}**",
        f"- Custo de **acordar tudo** no alvo (curva de aceite): {brl(res['custo_acordar_tudo'])}",
        f"- Custo sob a **política** (curva de aceite): **{brl(res['custo_politica_curva'])}** → economia **{brl(res['economia_politica_curva'])} ({res['economia_pct_curva']:.1%})**, acordo em {res['share_acordo']:.1%} dos casos",
        f"- Probabilidade usada no replay: {'**out-of-fold** (5 folds; cada caso pontuado por um modelo que não o viu)' if res.get('p_out_of_fold') else 'in-sample'}; "
        f"acordos históricos ({res.get('n_acordos_historicos', 0)}) entram com o valor que de fato pagaram.",
        "",
        f"{h}## Baselines (mesmos custos; só a regra de decisão muda)",
        "| regra | custo | economia | % | % acordo | captura do ganho máximo |", "|---|---|---|---|---|---|",
        *[f"| {b['nome']} | {brl(b['custo'])} | {brl(b['economia'])} | {b['economia_pct']:.1%} | {b['share_acordo']:.1%} | {b['captura_do_ganho_maximo']:.0%} |"
          for b in res["baselines"]["linhas"]],
        "",
        "Leitura: o ganho vem de decidir pelo custo total de litigar, não de prever melhor a sentença; a política captura a maior parte do que um oráculo capturaria.",
        "",
        img("baselines"),
        "",
        f"{h}## Banda do número (variação amostral)",
        f"- Economia por fold: {' · '.join(f'{v:.1%}' for v in res['banda']['economia_pct_por_fold'])} → média **{res['banda']['media']:.1%} ± {res['banda']['sd']*100:.1f} p.p.**"
        if res["banda"].get("media") is not None else "- Banda por fold indisponível (base pequena)",
        f"- Bootstrap por caso ({res['banda']['n_bootstrap']}×): IC95 **{res['banda']['bootstrap_ic95'][0]:.1%} – {res['banda']['bootstrap_ic95'][1]:.1%}**",
        "- O lado *acordo* é hipótese (curva de aceite): a banda mede só a variação amostral do modelo, não a incerteza sobre o aceite — ver sensibilidade.",
        "",
        f"{h}## Ponto de indiferença (breakeven) e decisões sensíveis",
        f"- p\\* médio (p_perda em que acordar no alvo da escada custa o mesmo que defender): **{res['breakeven']['medio']:.2f}** "
        f"(p5 {res['breakeven']['p05']:.2f} · p95 {res['breakeven']['p95']:.2f}); casos cujo IC95 de p cruza p\\*: **{res['breakeven']['share_sensiveis']:.1%}** (vão para revisão)",
        "",
        f"{h}## Sensibilidade ao aceite e ao valor da oferta (economia vs. defender tudo)",
        "| taxa de aceite | oferta × | custo | economia | % |", "|---|---|---|---|---|",
        *[f"| {s['taxa_aceite']} | {s['mult_oferta']} | {brl(s['custo'])} | {brl(s['economia'])} | {s['economia_pct']:.1%} |" for s in res["sensibilidade"]],
        "",
        img("sensibilidade"),
        "",
        f"{h}## Sensibilidade à âncora da curva de aceite (s50 = fração do VC em que 50% aceitam)",
        "| s50 | custo da política | economia | % acordo |", "|---|---|---|---|",
        *[f"| {s['s50']:.2f} | {brl(s['custo_politica'])} | {s['economia_pct']:.1%} | {s['share_acordo']:.1%} |" for s in res["sensibilidade_s50"]],
        "",
        f"{h}## Sensibilidade aos custos de litigar (defender tudo e política recalculados)",
        "| cenário | defender tudo | política | economia | % acordo | p\\* médio |", "|---|---|---|---|---|---|",
        *[f"| {s['cenario']} | {brl(s['custo_defender_tudo'])} | {brl(s['custo_politica'])} | {s['economia_pct']:.1%} | {s['share_acordo']:.1%} | {s['p_breakeven_medio']:.2f} |"
          for s in res["sensibilidade_custos"]],
        "",
        f"{h}## Instruir antes de acordar (valor esperado da informação)",
        f"- Casos em que vale pedir {' e/ou '.join(cfg.NOME_DOC[d].lower() for d in res['instruir']['docs_avaliados'])} antes de propor acordo: "
        f"**{res['instruir']['n_instruir']:,} ({res['instruir']['share_instruir']:.1%} dos casos; {res['instruir']['share_dos_acordos']:.0%} dos acordos)**; "
        f"EVSI total {brl(res['instruir']['evsi_total'])} — hipótese: q_d = P(doc | outros docs) é a chance de o back-office localizar o documento.",
        "| chance de localizar (× q_d) | casos instruir | % | EVSI total | EVSI médio |", "|---|---|---|---|---|",
        *[f"| × {q['mult_q']} | {q['n_instruir']:,} | {q['share_instruir']:.1%} | {brl(q['evsi_total'])} | {brl(q['evsi_medio'])} |" for q in res["instruir"]["por_mult_q"]],
        "",
        f"{h}## Por UF",
        "| UF | % acordo | p\\* médio | severidade (cond/VC) | perda real | defender tudo | política | economia |", "|---|---|---|---|---|---|---|---|",
        *[f"| {u['uf']} | {u['share_acordo']:.0%} | {u['p_breakeven']:.2f} | {u['ratio_media']:.2f} | {u['perda_real']:.0%} | {brl(u['defender_tudo'])} | {brl(u['politica'])} | {u['economia_pct']:.1%} |"
          for u in res["por_uf"]],
        "",
        f"{h}## Faixas",
        "| faixa | casos | % casos | p perda prevista | perda real | condenação real | custo real defesa |", "|---|---|---|---|---|---|---|",
        *[f"| {f['faixa']} | {f['n']:,} | {f['share']:.1%} | {f['p_perda_prevista']:.1%} | {f['perda_real']:.1%} | {brl(f['condenacao_real'])} | {brl(f['custo_real_defesa'])} |" for f in res["por_faixa"]],
        "",
        img("faixas"),
        "",
        f"{h}# Subsídios",
        "| documento | perda quando presente | perda quando ausente | Δ p.p. |", "|---|---|---|---|",
        *[f"| {cfg.NOME_DOC[d]} | {e['perda_com']:.1%} | {e['perda_sem']:.1%} | {(e['perda_sem']-e['perda_com'])*100:+.1f} |" for d, e in res["efeito_docs"].items()],
        "",
        "Ganho se encontrar — queda do custo esperado de litigar se o subsídio ausente fosse recuperado (limite superior do valor da informação):",
        "| documento | casos sem | ganho total | por caso |", "|---|---|---|---|",
        *[f"| {cfg.NOME_DOC[d]} | {v['casos_sem']:,} | {brl(v['ganho_total'])} | {brl(v['ganho_por_caso'])} |" for d, v in res["voi"].items()],
        "",
        img("subsidios"),
    ]
    return [l for l in linhas if l is not None]


def escrever_md(res: dict, out: Path) -> None:
    (out / "resumo.md").write_text("\n".join(linhas_resumo(res, "#", "")) + "\n", encoding="utf-8")


def atualizar_readme(res: dict, readme: Path, out: Path) -> bool:
    """Substitui o bloco entre os marcadores no README pelas tabelas geradas. Devolve True se atualizou."""
    if not readme.exists():
        return False
    texto = readme.read_text(encoding="utf-8")
    if MARCADOR_INICIO not in texto or MARCADOR_FIM not in texto:
        return False
    prefixo = out.relative_to(readme.parent).as_posix() + "/"
    bloco = "\n".join([MARCADOR_INICIO, "_Bloco gerado por `make backtest`; não edite à mão._", "",
                       *linhas_resumo(res, "###", prefixo), MARCADOR_FIM])
    ini = texto.index(MARCADOR_INICIO)
    fim = texto.index(MARCADOR_FIM) + len(MARCADOR_FIM)
    readme.write_text(texto[:ini] + bloco + texto[fim:], encoding="utf-8")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="backtest da política na base histórica")
    ap.add_argument("--raw", type=Path, default=cfg.ARQ_RAW_XLSX)
    ap.add_argument("--out", type=Path, default=cfg.DIR_BACKTEST)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    base = carregar_base(args.raw)
    eng = Engine.carregar()
    df = pontuar_base(base, eng)
    res = resumo(df, eng)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "resumo.json").write_text(json_dumps(res, default=float), encoding="utf-8")
    escrever_md(res, args.out)
    if atualizar_readme(res, cfg.RAIZ / "README.md", args.out):
        log.info("README atualizado com as tabelas do backtest")
    _grafico_reliability(res, args.out)
    _grafico_sensibilidade(res, args.out)
    _grafico_faixas(res, args.out)
    _grafico_voi(res, args.out)
    _grafico_baselines(res, args.out)
    print((args.out / "resumo.md").read_text(encoding="utf-8"))
    _ = custo_politica  # exportado para uso externo


if __name__ == "__main__":
    main()
