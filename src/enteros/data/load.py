"""Carrega a base de sentenças (xlsx da Enter ou CSV sintético nosso) em colunas canônicas."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from enteros import config as cfg

log = logging.getLogger(__name__)

COLUNAS_CANONICAS = [
    "numero", "uf", "assunto", "sub_assunto", "resultado_macro", "resultado_micro",
    "valor_causa", "valor_condenacao", *cfg.DOCS,
]
COLUNAS_DERIVADAS = ["perda", "acordo", "perda_sentenca", "ratio", "n_docs"]  # cache antigo sem elas é refeito


def _ler_xlsx(caminho: Path) -> pd.DataFrame:
    res = pd.read_excel(caminho, sheet_name=cfg.ABA_RESULTADOS).rename(columns=cfg.COLUNAS_RESULTADOS)
    sub = pd.read_excel(caminho, sheet_name=cfg.ABA_SUBSIDIOS, header=1).rename(columns=cfg.COLUNAS_SUBSIDIOS)
    sub = sub[["numero", *cfg.DOCS]]
    base = res.merge(sub, on="numero", how="inner", validate="one_to_one")
    if len(base) != len(res):
        raise ValueError(f"join resultados×subsídios perdeu linhas: {len(res)} → {len(base)}")
    return base


def _ler_csv(caminho: Path) -> pd.DataFrame:
    df = pd.read_csv(caminho)
    renome = {**cfg.COLUNAS_RESULTADOS, **cfg.COLUNAS_SUBSIDIOS}
    return df.rename(columns={c: renome.get(c, c) for c in df.columns})


def enriquecer(base: pd.DataFrame) -> pd.DataFrame:
    """Tipos, colunas derivadas e validação de schema."""
    faltando = [c for c in COLUNAS_CANONICAS if c not in base.columns]
    if faltando:
        raise ValueError(f"colunas ausentes na base: {faltando}")
    base = base.copy()
    for c in cfg.DOCS:
        base[c] = base[c].astype(float).round().astype(int)
    base["valor_causa"] = base["valor_causa"].astype(float)
    base["valor_condenacao"] = base["valor_condenacao"].astype(float).fillna(0.0)
    base["perda"] = (base["resultado_macro"] == cfg.NAO_EXITO).astype(int)
    # acordo histórico não é sentença: fica fora do treino de frequência e de severidade
    base["acordo"] = (base["resultado_micro"] == cfg.MICRO_ACORDO).astype(int)
    base["perda_sentenca"] = ((base["perda"] == 1) & (base["acordo"] == 0)).astype(int)
    base["ratio"] = (base["valor_condenacao"] / base["valor_causa"]).where(base["perda"] == 1)
    base["n_docs"] = base[list(cfg.DOCS)].sum(axis=1)
    if base["numero"].duplicated().any():
        raise ValueError("números de processo duplicados na base")
    return base


def carregar_base(raw: Path | None = None, usar_cache: bool = True) -> pd.DataFrame:
    """Base completa se o xlsx existir; senão o CSV sintético versionado (o pipeline roda igual)."""
    raw = Path(raw) if raw else cfg.ARQ_RAW_XLSX
    if usar_cache and cfg.ARQ_CACHE_PARQUET.exists() and raw.exists():
        if cfg.ARQ_CACHE_PARQUET.stat().st_mtime >= raw.stat().st_mtime:
            cache = pd.read_parquet(cfg.ARQ_CACHE_PARQUET)
            if all(c in cache.columns for c in COLUNAS_DERIVADAS):
                return cache
            log.info("cache sem colunas derivadas novas; refazendo a partir do xlsx")
    if raw.exists():
        base = enriquecer(_ler_xlsx(raw))
        cfg.DIR_CACHE.mkdir(parents=True, exist_ok=True)
        base.to_parquet(cfg.ARQ_CACHE_PARQUET, index=False)
        log.info("base real carregada: %d linhas (cache em %s)", len(base), cfg.ARQ_CACHE_PARQUET)
        return base
    if cfg.ARQ_SINTETICOS.exists():
        log.warning("xlsx não encontrado em %s; usando sintéticos %s", raw, cfg.ARQ_SINTETICOS)
        return enriquecer(_ler_csv(cfg.ARQ_SINTETICOS))
    raise FileNotFoundError(f"nem {raw} nem {cfg.ARQ_SINTETICOS} existem; veja data/README.md")


def eh_base_real(raw: Path | None = None) -> bool:
    return (Path(raw) if raw else cfg.ARQ_RAW_XLSX).exists()


def main() -> None:
    ap = argparse.ArgumentParser(description="carrega a base e imprime um resumo")
    ap.add_argument("--raw", type=Path, default=cfg.ARQ_RAW_XLSX)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    base = carregar_base(args.raw, usar_cache=False)
    print(f"linhas: {len(base)}  nulos: {int(base[COLUNAS_CANONICAS].isna().sum().sum())}")
    print(f"perda global: {base['perda'].mean():.3f}  condenação total: R$ {base['valor_condenacao'].sum()/1e6:.1f}M")
    print(base.groupby("sub_assunto")["perda"].agg(["size", "mean"]).round(3))


if __name__ == "__main__":
    main()
