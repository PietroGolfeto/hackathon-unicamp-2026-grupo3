"""Carga dos 2 CSVs da Enter (+ scores OOF de P1 ou stub) em historico_sentencas e cache."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from core.colunas import FLAGS_SUBSIDIOS, mapear_colunas, parse_brl, resultado_macro_para_int
from core.modelo import COLUNAS_HISTORICO_SCORED
from sqlalchemy import text
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)

COLUNAS_TABELA = [
    "numero", "uf", "sub_assunto", "valor_causa", "resultado_macro", "resultado_micro",
    "valor_condenacao", *FLAGS_SUBSIDIOS, "p_exito_oof", "condenacao_p20_oof",
    "condenacao_p50_oof", "condenacao_p80_oof", "fold", "scores_origem",
]
CHAVE_STUB = ["contrato", "extrato", "comprovante_credito", "sub_assunto"]


def localizar_csvs(data_dir: Path) -> tuple[Path, Path] | None:
    resultados = sorted(data_dir.glob("*esultados*.csv"))
    subsidios = sorted(p for p in data_dir.glob("*ubs*dios*.csv"))
    if not resultados or not subsidios:
        return None
    return resultados[0], subsidios[0]


def ler_csv_enter(caminho: Path) -> pd.DataFrame:
    """Tenta header=0 e header=1 (o CSV de subsídios tem uma linha de legenda antes)."""
    for header in (0, 1):
        df = pd.read_csv(caminho, header=header, dtype=str)
        mapa = mapear_colunas(df.columns)
        if "numero" in mapa.values():
            return df.rename(columns=mapa)[list(mapa.values())]
    raise ValueError(f"não reconheci as colunas de {caminho.name}")


def montar(data_dir: Path) -> pd.DataFrame:
    caminhos = localizar_csvs(data_dir)
    if caminhos is None:
        raise FileNotFoundError(f"CSVs da Enter não encontrados em {data_dir} (ver SETUP.md)")
    res = ler_csv_enter(caminhos[0])
    sub = ler_csv_enter(caminhos[1])
    df = res.merge(sub, on="numero", how="inner")
    df["numero"] = df["numero"].str.strip()
    df["valor_causa"] = df["valor_causa"].map(parse_brl)
    df["valor_condenacao"] = df["valor_condenacao"].map(parse_brl)
    df["resultado_macro"] = df["resultado_macro"].map(resultado_macro_para_int)
    for flag in FLAGS_SUBSIDIOS:
        df[flag] = df[flag].astype(str).str.strip().isin({"1", "1.0", "true", "True"})
    df = df.drop_duplicates("numero")
    log.info("histórico: %d linhas após merge (%d resultados, %d subsídios)", len(df), len(res), len(sub))
    return anexar_scores(df, data_dir / "derived" / "historico_scored.csv")


def anexar_scores(df: pd.DataFrame, scored: Path) -> pd.DataFrame:
    """Prefere o arquivo de P1; sem ele, stub in-sample por lookup (marcado como 'stub')."""
    if scored.exists():
        s = pd.read_csv(scored)
        faltam = set(COLUNAS_HISTORICO_SCORED) - set(s.columns)
        if faltam:
            raise ValueError(f"{scored} sem colunas {sorted(faltam)}")
        cols = ["numero", "p_exito_oof", "condenacao_p20_oof", "condenacao_p50_oof",
                "condenacao_p80_oof", "fold"]
        df = df.merge(s[cols], on="numero", how="left")
        df["scores_origem"] = "modelo"
        log.info("scores OOF de P1 anexados de %s", scored)
        return df
    return scores_do_engine(df)


def scores_do_engine(df: pd.DataFrame) -> pd.DataFrame:
    """Logística do engine (30 coeficientes; in-sample ≈ OOF, métricas honestas em ModeloInfo). Falha → stub."""
    try:
        from app.modelo_enteros import ModeloEnteros

        modelo = ModeloEnteros()
    except Exception as exc:  # noqa: BLE001 - sem enteros/models cai no stub
        log.warning("engine indisponível para o histórico (%s); usando stub", exc)
        return stub_scores(df)
    df = df.copy()
    df["p_exito_oof"] = modelo.p_exito_lote(df).clip(0.001, 0.999)
    for q, valores in modelo.quantis_lote(df).items():
        df[f"condenacao_{q}_oof"] = valores
    df["fold"] = None
    df["scores_origem"] = "modelo"
    log.info("scores do histórico pelo engine %s", modelo.versao)
    return df


def stub_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    grupo = df.groupby(CHAVE_STUB, dropna=False)["resultado_macro"]
    media = grupo.transform("mean")
    n = grupo.transform("count")
    n_docs = df[list(FLAGS_SUBSIDIOS)].sum(axis=1)
    fallback = (0.03 + 0.16 * n_docs).clip(0.01, 0.99)
    df["p_exito_oof"] = media.where(n >= 30, fallback).clip(0.01, 0.99).astype(float)
    df["condenacao_p20_oof"] = 0.55 * df["valor_causa"]
    df["condenacao_p50_oof"] = 0.74 * df["valor_causa"]
    df["condenacao_p80_oof"] = 0.86 * df["valor_causa"]
    df["fold"] = None
    df["scores_origem"] = "stub"
    return df


def gravar(engine: Engine, df: pd.DataFrame) -> int:
    """TRUNCATE + COPY. Colunas ausentes entram como NULL."""
    for col in COLUNAS_TABELA:
        if col not in df.columns:
            df[col] = None
    linhas = df[COLUNAS_TABELA].astype(object).where(df[COLUNAS_TABELA].notna(), None).values.tolist()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE historico_sentencas"))
        raw = conn.connection.driver_connection
        sql = f"COPY historico_sentencas ({', '.join(COLUNAS_TABELA)}) FROM STDIN"
        with raw.cursor() as cur, cur.copy(sql) as copy:
            for linha in linhas:
                copy.write_row(linha)
    log.info("historico_sentencas: %d linhas gravadas", len(linhas))
    return len(linhas)


def carregar_cache(engine: Engine) -> pd.DataFrame | None:
    """DataFrame do histórico para backtest e stub. None se a tabela estiver vazia."""
    try:
        df = pd.read_sql("SELECT * FROM historico_sentencas", engine)
    except Exception as exc:  # noqa: BLE001 - tabela pode não existir ainda
        log.warning("não consegui ler historico_sentencas: %s", exc)
        return None
    if df.empty:
        return None
    df["n_docs"] = df[list(FLAGS_SUBSIDIOS)].astype(int).sum(axis=1)
    return df
