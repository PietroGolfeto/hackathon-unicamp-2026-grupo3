"""Ajuda dos testes com LLM real: casos de exemplo, medidas da resposta, gravação e resumo no terminal."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from extractor.benchmark import PRECOS
from extractor.pipeline import Resultado
from extractor.prompts import INSTRUCOES, montar_entrada
from extractor.schema import SaidaLLM

RAIZ = Path(__file__).resolve().parents[3]
DESTINO = RAIZ / "data" / "cache" / "testes-llm"
CPF_INTEIRO = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
TAG_FONTE = re.compile(r"\[(Peti[cç][ãa]o|Contrato|Extrato|Comprovante|Dossi[êe]|Demonstrativo|Laudo)\]", re.IGNORECASE)
TAG_SUBSIDIO = {"contrato": "contrato", "extrato": "extrato", "comprovante_credito": "comprovante",
                "dossie": "dossi", "demonstrativo_divida": "demonstrativo", "laudo_referenciado": "laudo"}

# O que tem de valer no resultado final (após as regras) para os dois processos exemplo da Enter.
ESPERADOS: dict[str, dict[str, Any]] = {
    "0801234-56.2024.8.10.0001": {
        "uf": "MA", "valor_causa": 20000.0, "obrigatorios": {"IDOSO"},
        "proibidos": {"SEM_CONTRATO", "CREDITO_CONTA_TERCEIRO", "LIVENESS_AUSENTE_CANAL_DIGITAL"},
    },
    "0654321-09.2024.8.04.0001": {
        "uf": "AM", "valor_causa": 25000.0, "proibidos": set(),
        "obrigatorios": {"IDOSO", "BOLETIM_OCORRENCIA", "RECLAMACAO_BACEN", "SEM_CONTRATO",
                         "CREDITO_CONTA_TERCEIRO", "LIVENESS_AUSENTE_CANAL_DIGITAL"},
    },
}


def pastas_casos() -> list[Path]:
    """docs/Caso_*/ com PDFs (não versionados; ver memory-bank/contexto.md)."""
    return sorted(p for p in (RAIZ / "docs").glob("Caso_*") if p.is_dir() and any(p.glob("*.pdf")))


def _palavras(s: str) -> int:
    return len(s.split())


def _custo_usd(modelo: str, entrada: int, cache: int, saida: int) -> float | None:
    precos = next((v for k, v in PRECOS.items() if modelo.startswith(k)), None)
    if not precos:
        return None
    pe, ps = precos
    return ((entrada - cache) * pe + cache * pe / 10 + saida * ps) / 1_000_000


def observacoes(saida: SaidaLLM, ausentes: list[str], arquivos: list[str]) -> list[str]:
    """Regras do prompt que só o LLM cumpre (ou não); informativas, não falham o teste."""
    a, d = saida.analise, saida.dados
    itens = a.pontos_fortes_banco + a.pontos_fracos_banco + a.riscos + a.contradicoes
    obs: list[str] = []
    if longos := [i for i in itens if _palavras(i) > 20]:
        obs.append(f"{len(longos)} item(ns) de análise com mais de 20 palavras")
    if sem_fonte := [i for i in a.pontos_fortes_banco + a.pontos_fracos_banco if not TAG_FONTE.search(i)]:
        obs.append(f"{len(sem_fonte)} ponto(s) forte/fraco sem fonte entre colchetes")
    if (n := _palavras(a.texto)) > 120:
        obs.append(f"parecer com {n} palavras (pedido: até 120)")
    if len(a.contradicoes) > 3:
        obs.append(f"{len(a.contradicoes)} contradições (pedido: até 3)")
    if len(a.riscos) > 4:
        obs.append(f"{len(a.riscos)} riscos (pedido: até 4)")
    if CPF_INTEIRO.search(saida.model_dump_json()):
        obs.append("CPF inteiro na saída (o prompt pede ***.***.123-45)")
    if fontes := [s.fonte for s in d.sinais_alerta if s.fonte and s.fonte not in arquivos]:
        obs.append(f"fonte de sinal que não é arquivo da pasta: {fontes}")
    tags = [TAG_SUBSIDIO[t] for t in ausentes if t in TAG_SUBSIDIO]
    if cita := [i for i in itens if any(re.search(rf"\[{t}", i, re.IGNORECASE) for t in tags)
                and not re.search(r"ausente|n[ãa]o\s+(foi\s+)?(apresentad|juntad|entregu)", i, re.IGNORECASE)]:
        obs.append(f"{len(cita)} item(ns) citam subsídio que o banco não entregou")
    return obs


def medir(res: Resultado, ausentes: list[str]) -> dict[str, Any]:
    s, a, d = res.saida_llm, res.saida_llm.analise, res.saida_llm.dados
    bruto = json.dumps(s.model_dump(), ensure_ascii=False)
    return {
        "numero": res.numero, "modelo": res.modelo, "segundos": res.segundos,
        "tokens_entrada": res.tokens_entrada, "tokens_cache": res.tokens_cache,
        "tokens_saida": res.tokens_saida, "tokens_raciocinio": res.tokens_raciocinio,
        "custo_usd": _custo_usd(res.modelo, res.tokens_entrada, res.tokens_cache, res.tokens_saida),
        "chars_instrucoes": len(INSTRUCOES), "chars_entrada": len(montar_entrada(res.brief)),
        "chars_brief": len(res.brief), "chars_saida": len(bruto),
        "docs": len(res.docs), "chars_docs": sum(x.chars for x in res.docs),
        "contagens": {
            "pedidos": len(d.pedidos), "sinais": len(d.sinais_alerta),
            "pontos_fortes": len(a.pontos_fortes_banco), "pontos_fracos": len(a.pontos_fracos_banco),
            "contradicoes": len(a.contradicoes), "riscos": len(a.riscos),
            "palavras_resumo": _palavras(d.resumo_fatos), "palavras_texto": _palavras(a.texto),
            "confianca": d.confianca,
        },
        "sinais_llm": sorted(x.codigo for x in d.sinais_alerta),
        "sinais_finais": sorted(res.dados.codigos_sinais()),
        "observacoes": observacoes(s, ausentes, [x.arquivo for x in res.docs]),
    }


def gravar(res: Resultado, medidas: dict[str, Any], pasta_run: Path) -> Path:
    """JSON completo da chamada: medidas, saída crua do LLM, dados/análise finais e o brief enviado."""
    pasta_run.mkdir(parents=True, exist_ok=True)
    destino = pasta_run / f"{res.numero}__{res.modelo}.json"
    destino.write_text(json.dumps({
        "medidas": medidas, "saida_llm": res.saida_llm.model_dump(),
        "dados_finais": res.dados.model_dump(mode="json"), "analise_final": res.analise.model_dump(mode="json"),
        "brief": res.brief,
    }, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return destino


def pasta_da_rodada() -> Path:
    return DESTINO / datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")


def resumo_terminal(chamadas: list[dict[str, Any]]) -> str:
    linhas: list[str] = []
    for c in chamadas:
        m = c["medidas"]
        linhas.append(f"\n── {m['numero']} · {m['modelo']} · {m['segundos']} s ──")
        linhas.append(json.dumps(c["saida"], ensure_ascii=False, indent=2))
    linhas.append("\n| processo | modelo | tokens entrada (cache) | tokens saída (raciocínio) | s | "
                  "docs → brief → saída (chars) | US$ |")
    linhas.append("|---|---|---|---|---|---|---|")
    for c in chamadas:
        m = c["medidas"]
        custo = f"{m['custo_usd']:.4f}" if m["custo_usd"] is not None else "?"
        linhas.append(f"| {m['numero'][:7]} | {m['modelo']} | {m['tokens_entrada']} ({m['tokens_cache']}) | "
                      f"{m['tokens_saida']} ({m['tokens_raciocinio']}) | {m['segundos']} | "
                      f"{m['chars_docs']} → {m['chars_brief']} → {m['chars_saida']} | {custo} |")
    linhas.append("\n| processo | pedidos | sinais LLM → finais | fortes | fracos | contrad. | riscos | "
                  "palavras resumo / parecer | confiança |")
    linhas.append("|---|---|---|---|---|---|---|---|---|")
    for c in chamadas:
        m, n = c["medidas"], c["medidas"]["contagens"]
        linhas.append(f"| {m['numero'][:7]} | {n['pedidos']} | {len(m['sinais_llm'])} → {len(m['sinais_finais'])} | "
                      f"{n['pontos_fortes']} | {n['pontos_fracos']} | {n['contradicoes']} | {n['riscos']} | "
                      f"{n['palavras_resumo']} / {n['palavras_texto']} | {n['confianca']} |")
    for c in chamadas:
        m = c["medidas"]
        linhas.append(f"\n{m['numero'][:7]} · sinais do LLM: {m['sinais_llm']}")
        linhas.append(f"{m['numero'][:7]} · sinais finais (após regras): {m['sinais_finais']}")
        for o in m["observacoes"]:
            linhas.append(f"{m['numero'][:7]} · obs: {o}")
    linhas.append(f"\nJSON completo de cada chamada (saída crua, dados finais e brief): {chamadas[0]['arquivo'].parent}")
    return "\n".join(linhas)
