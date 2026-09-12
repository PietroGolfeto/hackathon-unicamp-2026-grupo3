"""Benchmark da ficha do caso: mesmos PDFs, modelos diferentes da OpenAI, gabarito dos processos exemplo.

`python -m extractor.benchmark [--modelos gpt-4o-mini gpt-5.4-mini] [--repeticoes 3]`
Mede acerto contra o gabarito, decisão do engine, alucinações, latência, tokens e custo.
Grava o JSON bruto e a tabela em `data/derived/` (não versionado).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.caso import Subsidios
from core.docs import subsidios_por_arquivos
from dotenv import find_dotenv, load_dotenv

from extractor.caso import (
    Documento,
    ExtracaoCaso,
    _doc_do_destaque_presente,
    _pedir_extracao,
    ler_caso,
    para_case_features,
)
from extractor.leitura import ErroLeitura
from extractor.resumo import ErroResumo, _cliente

# US$ por 1M tokens (entrada, entrada em cache, saída); tabela padrão de
# developers.openai.com/api/docs/pricing. Tokens de raciocínio são cobrados como saída.
PRECOS: dict[str, tuple[float, float, float]] = {
    "gpt-5.5": (5.00, 0.50, 30.00),
    "gpt-5.4": (2.50, 0.25, 15.00),
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
    "gpt-5.4-nano": (0.20, 0.02, 1.25),
    "gpt-5.2": (1.75, 0.175, 14.00),
    "gpt-5.1": (1.25, 0.125, 10.00),
    "gpt-5": (1.25, 0.125, 10.00),
    "gpt-5-mini": (0.25, 0.025, 2.00),
    "gpt-5-nano": (0.05, 0.005, 0.40),
    "gpt-4.1": (2.00, 0.50, 8.00),
    "gpt-4.1-mini": (0.40, 0.10, 1.60),
    "gpt-4.1-nano": (0.10, 0.025, 0.40),
    "gpt-4o": (2.50, 1.25, 10.00),
    "gpt-4o-mini": (0.15, 0.075, 0.60),
    "o4-mini": (1.10, 0.275, 4.40),
    "o3": (2.00, 0.50, 8.00),
}

MODELOS_PADRAO = [
    "gpt-4o-mini", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4.1",
    "gpt-5-nano", "gpt-5-mini", "gpt-5.4-nano", "gpt-5.4-mini", "gpt-5.4", "gpt-5.5",
]


@dataclass(frozen=True)
class Gabarito:
    """Fatos conferidos nos PDFs de cada processo exemplo. Textos livres são regex."""

    uf: str
    comarca: str
    valor_causa: float
    dano_moral_pedido: float
    contrato_valor: float
    contrato_parcelas: int
    valor_parcela: float
    parcelas_pagas: int
    autor_idade: int
    canal: str
    assinatura: str
    sub_assunto: str
    conta_credito_titular_autor: bool
    liveness_presente: bool
    decisao: str
    proveito: tuple[str, ...] = ()  # todos precisam aparecer na prova de proveito
    indicios: tuple[str, ...] = ()  # todos precisam aparecer nos indícios
    contradicao: tuple[str, ...] = ()  # todos juntos numa mesma contradição


GABARITOS: dict[str, Gabarito] = {
    "processo_01": Gabarito(
        uf="MA", comarca="são luís", valor_causa=20000, dano_moral_pedido=15000,
        contrato_valor=5000, contrato_parcelas=72, valor_parcela=120, parcelas_pagas=21,
        autor_idade=65, canal=r"telemarketing|telef", assinatura=r"manuscrit",
        sub_assunto="Genérico", conta_credito_titular_autor=True, liveness_presente=True,
        decisao="defesa", proveito=(r"\bTED\b", r"\bPIX\b", r"saque"),
        contradicao=(r"extrato", r"moviment|\bTED\b|\bPIX\b|saque"),
    ),
    "processo_02": Gabarito(
        uf="AM", comarca="manaus", valor_causa=25000, dano_moral_pedido=18000,
        contrato_valor=8500, contrato_parcelas=84, valor_parcela=180, parcelas_pagas=8,
        autor_idade=61, canal=r"\bapp\b|aplicativo|mobile", assinatura=r"biometr",
        sub_assunto="Golpe", conta_credito_titular_autor=False, liveness_presente=False,
        decisao="acordo", proveito=(r"caixa",),
        indicios=(r"boletim|\bB\.?O\.?\b", r"\bRDR\b|BACEN|Banco Central"),
    ),
}


@dataclass
class Rodada:
    modelo: str
    caso: str
    repeticao: int
    segundos: float = 0.0
    tokens_entrada: int = 0
    tokens_cache: int = 0
    tokens_saida: int = 0
    tokens_raciocinio: int = 0
    custo_usd: float | None = None
    erro: str | None = None
    extracao: ExtracaoCaso | None = None
    decisao: str | None = None
    checks: dict[str, bool] = field(default_factory=dict)

    @property
    def nota(self) -> float:
        return sum(self.checks.values()) / len(self.checks) if self.checks else 0.0

    def para_json(self) -> dict[str, Any]:
        dados = {k: v for k, v in self.__dict__.items() if k != "extracao"}
        dados["nota"] = round(self.nota, 4)
        dados["extracao"] = self.extracao.model_dump() if self.extracao else None
        return dados


def custo(modelo: str, entrada: int, cache: int, saida: int) -> float | None:
    """US$ da chamada; snapshots datados (gpt-4o-mini-2024-07-18) usam o preço do alias."""
    preco = PRECOS.get(modelo) or PRECOS.get(re.sub(r"-\d{4}-\d{2}-\d{2}$", "", modelo))
    if preco is None:
        return None
    p_entrada, p_cache, p_saida = preco
    return ((entrada - cache) * p_entrada + cache * p_cache + saida * p_saida) / 1_000_000


def _tem(padroes: tuple[str, ...], textos: list[str]) -> bool:
    junto = " | ".join(textos)
    return all(re.search(p, junto, re.IGNORECASE) for p in padroes)


def avaliar(ex: ExtracaoCaso, subsidios: Subsidios, decisao: str | None, g: Gabarito) -> dict[str, bool]:
    """Um critério por fato do gabarito, mais alucinação de documento e a decisão do engine."""
    return {
        "uf": (ex.uf or "").upper() == g.uf,
        "comarca": g.comarca in (ex.comarca or "").lower(),
        "valor_causa": ex.valor_causa == g.valor_causa,
        "dano_moral": ex.dano_moral_pedido == g.dano_moral_pedido,
        "contrato_valor": ex.contrato_valor == g.contrato_valor,
        "contrato_parcelas": ex.contrato_parcelas == g.contrato_parcelas,
        "valor_parcela": ex.valor_parcela == g.valor_parcela,
        "parcelas_pagas": ex.parcelas_pagas == g.parcelas_pagas,
        "idade": ex.autor_idade is not None and abs(ex.autor_idade - g.autor_idade) <= 1,
        "canal": bool(re.search(g.canal, ex.canal_contratacao or "", re.IGNORECASE)),
        "assinatura": bool(re.search(g.assinatura, ex.assinatura or "", re.IGNORECASE)),
        "sub_assunto": ex.sub_assunto == g.sub_assunto,
        "conta_do_autor": ex.conta_credito_titular_autor is g.conta_credito_titular_autor,
        "liveness": ex.liveness_presente is g.liveness_presente,
        "prova_de_proveito": _tem(g.proveito, ex.prova_de_proveito),
        "indicios": _tem(g.indicios, ex.indicios),
        "contradicao_chave": not g.contradicao or any(_tem(g.contradicao, [c]) for c in ex.contradicoes),
        "sem_destaque_de_doc_ausente": all(
            _doc_do_destaque_presente(d, subsidios) for d in ex.destaques_subsidios
        ),
        "sem_contradicao_com_doc_ausente": all(
            _doc_do_destaque_presente(c.split("×", 1)[-1].strip(), subsidios) for c in ex.contradicoes
        ),
        "decisao": decisao == g.decisao,
    }


def executar(modelo: str, caso: str, repeticao: int, documentos: list[Documento], client: Any) -> Rodada:
    """Uma chamada à OpenAI; erro de um modelo vira registro, não derruba o benchmark."""
    r = Rodada(modelo, caso, repeticao)
    inicio = time.perf_counter()
    try:
        resposta = _pedir_extracao(documentos, client, modelo)
    except Exception as exc:  # noqa: BLE001
        r.segundos = time.perf_counter() - inicio
        r.erro = f"{type(exc).__name__}: {exc}"[:300]
        return r
    r.segundos = time.perf_counter() - inicio
    uso = getattr(resposta, "usage", None)
    if uso is not None:
        r.tokens_entrada = uso.input_tokens
        r.tokens_cache = getattr(uso.input_tokens_details, "cached_tokens", 0) or 0
        r.tokens_saida = uso.output_tokens
        r.tokens_raciocinio = getattr(uso.output_tokens_details, "reasoning_tokens", 0) or 0
        r.custo_usd = custo(modelo, r.tokens_entrada, r.tokens_cache, r.tokens_saida)
    if resposta.output_parsed is None:
        r.erro = "sem saída estruturada"
    else:
        r.extracao = resposta.output_parsed
    return r


def pontuar(r: Rodada, subsidios: Subsidios, g: Gabarito, engine: Any) -> None:
    if r.extracao is None:
        return
    try:
        r.decisao = engine.recomendar(para_case_features(r.extracao, subsidios)).decisao
    except ErroResumo:
        r.decisao = None
    r.checks = avaliar(r.extracao, subsidios, r.decisao, g)


def _fracao(rodadas: list[Rodada], chave: str) -> float:
    return sum(r.checks.get(chave, False) for r in rodadas) / len(rodadas) if rodadas else 0.0


def resumo_por_modelo(rodadas: list[Rodada]) -> list[dict[str, Any]]:
    """Erro conta como nota zero: modelo que falha não sobe no ranking por ter menos rodadas."""
    linhas = []
    for modelo in dict.fromkeys(r.modelo for r in rodadas):
        rs = [r for r in rodadas if r.modelo == modelo]
        ok = [r for r in rs if r.erro is None]
        com_contradicao = [r for r in rs if r.caso in GABARITOS and GABARITOS[r.caso].contradicao]
        falhas = Counter(k for r in ok for k, v in r.checks.items() if not v)
        custos = [r.custo_usd for r in ok if r.custo_usd is not None]
        linhas.append({
            "modelo": modelo,
            "rodadas": len(rs),
            "erros": len(rs) - len(ok),
            "nota": sum(r.nota for r in rs) / len(rs),
            "decisao": _fracao(rs, "decisao"),
            "contradicao_chave": _fracao(com_contradicao, "contradicao_chave"),
            "alucinacoes": sum(
                not (r.checks.get("sem_destaque_de_doc_ausente", True)
                     and r.checks.get("sem_contradicao_com_doc_ausente", True))
                for r in ok
            ),
            "latencia_p50": statistics.median(r.segundos for r in ok) if ok else None,
            "latencia_max": max((r.segundos for r in ok), default=None),
            "tokens_saida": statistics.mean(r.tokens_saida for r in ok) if ok else None,
            "tokens_raciocinio": statistics.mean(r.tokens_raciocinio for r in ok) if ok else None,
            "custo_por_caso": statistics.mean(custos) if custos else None,
            "custo_total": sum(custos),
            "falhas": [f"{k} ({n})" for k, n in falhas.most_common(3)],
            "exemplo_erro": next((r.erro for r in rs if r.erro), None),
        })
    return sorted(linhas, key=lambda x: (-x["nota"], x["custo_por_caso"] or 0))


def _num(valor: float | None, formato: str) -> str:
    return "—" if valor is None else format(valor, formato)


def tabela_markdown(linhas: list[dict[str, Any]]) -> str:
    cabecalho = (
        "| Modelo | Nota | Decisão | Contradição-chave | Alucinações | Latência p50 / máx (s) "
        "| Tokens saída (raciocínio) | US$/caso | Erros | Falhas mais comuns |\n"
        "|---|---|---|---|---|---|---|---|---|---|"
    )
    corpo = [
        f"| {x['modelo']} | {x['nota']:.0%} | {x['decisao']:.0%} | {x['contradicao_chave']:.0%} "
        f"| {x['alucinacoes']} | {_num(x['latencia_p50'], '.1f')} / {_num(x['latencia_max'], '.1f')} "
        f"| {_num(x['tokens_saida'], '.0f')} ({_num(x['tokens_raciocinio'], '.0f')}) "
        f"| {_num(x['custo_por_caso'], '.4f')} | {x['erros']}/{x['rodadas']} "
        f"| {', '.join(x['falhas']) or (x['exemplo_erro'] or '—')} |"
        for x in linhas
    ]
    return "\n".join([cabecalho, *corpo])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m extractor.benchmark",
        description="Compara modelos da OpenAI na ficha do caso contra o gabarito dos processos exemplo.",
    )
    parser.add_argument("--modelos", nargs="+", default=MODELOS_PADRAO)
    parser.add_argument("--repeticoes", type=int, default=3)
    parser.add_argument("--pasta", default="data/processos_exemplo")
    parser.add_argument("--paralelo", type=int, default=6, help="chamadas simultâneas à OpenAI")
    parser.add_argument("--saida", default="data/derived")
    args = parser.parse_args(argv)
    load_dotenv(find_dotenv(usecwd=True))

    from enteros.policy.engine import engine_padrao

    try:
        casos = {}
        for nome, gabarito in GABARITOS.items():
            docs = ler_caso(Path(args.pasta) / nome)
            subsidios = subsidios_por_arquivos(d.nome for d in docs if d.tipo == "subsidio")
            casos[nome] = (docs, subsidios, gabarito)
        client = _cliente()
    except (ErroLeitura, ErroResumo) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1

    tarefas = [(m, c, i) for i in range(1, args.repeticoes + 1) for m in args.modelos for c in casos]
    print(f"{len(tarefas)} chamadas ({len(args.modelos)} modelos × {len(casos)} casos × "
          f"{args.repeticoes} repetições)", file=sys.stderr)
    rodadas: list[Rodada] = []
    with ThreadPoolExecutor(max_workers=args.paralelo) as pool:
        futuros = [pool.submit(executar, m, c, i, casos[c][0], client) for m, c, i in tarefas]
        for futuro in as_completed(futuros):
            r = futuro.result()
            rodadas.append(r)
            estado = f"erro: {r.erro[:80]}" if r.erro else f"{r.segundos:.1f}s"
            print(f"  [{len(rodadas)}/{len(tarefas)}] {r.modelo} {r.caso} #{r.repeticao} {estado}",
                  file=sys.stderr)

    engine = engine_padrao()
    for r in rodadas:
        _, subsidios, gabarito = casos[r.caso]
        pontuar(r, subsidios, gabarito, engine)

    linhas = resumo_por_modelo(rodadas)
    tabela = tabela_markdown(linhas)
    print(tabela)

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")
    (saida / f"benchmark_extractor_{carimbo}.md").write_text(tabela + "\n", encoding="utf-8")
    (saida / f"benchmark_extractor_{carimbo}.json").write_text(
        json.dumps({"resumo": linhas, "rodadas": [r.para_json() for r in rodadas]},
                   ensure_ascii=False, indent=1, default=str),
        encoding="utf-8",
    )
    print(f"\nresultados em {saida}/benchmark_extractor_{carimbo}.{{md,json}}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
