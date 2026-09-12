"""Extrator de P3: implementa `core.docs.ExtratorDocs` (EXTRACTOR_IMPL=extractor.pipeline:Extrator).

Fluxo por processo: ler PDFs/TXT → validar segurança → parsing → brief → cache? → LLM (uma chamada
devolve dados + análise) → mapear para os contratos de core → gravar cache. `extrair` e `analisar`
servem do mesmo resultado; `redigir` é template, sem LLM. Instanciável sem argumentos: lê
OPENAI_API_KEY, OPENAI_MODEL, EXTRACTOR_CACHE_DIR e DATA_DIR do ambiente. Sem chave, responde só do cache.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from core import cnj
from core.caso import CasoFeatures
from core.docs import (
    Advogado,
    Analise,
    ContratoInfo,
    DadosExtraidos,
    Minutas,
    Pessoa,
    SinalAlerta,
    subsidios_por_arquivos,
)
from core.modelo import Scores
from core.politica import Recomendacao

from extractor import minutas as minutas_mod
from extractor import parsing, prompts, seguranca, texto
from extractor.cache import Cache
from extractor.cache import chave as chave_cache
from extractor.llm import MODELO_PADRAO, ClienteLLM, ErroConfiguracao, ErroLLM, cliente_do_ambiente
from extractor.schema import AnaliseLLM, SaidaLLM, hash_esquema
from extractor.seguranca import Achado

log = logging.getLogger(__name__)
ORIGEM = "llm"


@dataclass
class Preparacao:
    """Tudo que acontece antes do LLM: determinístico e gratuito."""

    numero: str
    uf: str | None
    docs: list[parsing.DocParseado]
    brief: str
    hashes: list[tuple[str, str]]
    achados: list[Achado] = field(default_factory=list)
    presentes: list[str] = field(default_factory=list)
    ausentes: list[str] = field(default_factory=list)

    @property
    def fatos_peticao(self) -> dict[str, Any]:
        return next((d.fatos for d in self.docs if d.tipo == "peticao"), {})


@dataclass
class Resultado:
    numero: str
    dados: DadosExtraidos
    analise: Analise
    saida_llm: SaidaLLM
    chave: str
    modelo: str
    cache_hit: bool
    tokens_entrada: int
    tokens_saida: int
    brief: str
    docs: list[parsing.DocParseado]
    achados: list[Achado]
    tokens_cache: int = 0
    tokens_raciocinio: int = 0
    segundos: float = 0.0


class Extrator:
    def __init__(self, cliente: ClienteLLM | None = None, cache: Cache | None = None,
                 usar_cache: bool = True) -> None:
        self.cliente: ClienteLLM | None = cliente if cliente is not None else cliente_do_ambiente()
        self.cache = cache if cache is not None else Cache(ativo=usar_cache)
        self.modelo = self.cliente.modelo if self.cliente else (os.environ.get("OPENAI_MODEL", "").strip()
                                                                or MODELO_PADRAO)
        self._memoria: dict[str, Resultado] = {}

    # ---------------------------------------------------------------- etapas

    def preparar(self, processo_dir: Path, numero: str | None = None) -> Preparacao:
        processo_dir = Path(processo_dir)
        numero_norm = cnj.normalizar(numero or _numero_da_pasta(processo_dir)) or (numero or processo_dir.name)
        docs: list[parsing.DocParseado] = []
        hashes: list[tuple[str, str]] = []
        achados: list[Achado] = []
        for d in texto.ler_pasta(processo_dir):
            ach = seguranca.inspecionar_pdf(d.reader, d.arquivo) if d.reader is not None else []
            limpo, ach_texto = seguranca.validar_texto(d.texto, d.arquivo)
            parsed = parsing.parsear(d.arquivo, d.pasta, limpo, paginas=d.paginas, leitor=d.leitor,
                                     achados=ach + ach_texto, erros=d.erros)
            docs.append(parsed)
            hashes.append((f"{d.pasta}/{d.arquivo}", d.sha256))
            achados += ach + ach_texto
            d.reader = None
        subs = subsidios_por_arquivos(d.arquivo for d in docs if d.pasta == "subsidios")
        uf = cnj.uf_do_numero(numero_norm)
        brief = parsing.montar_brief(numero_norm, uf, docs, subs.presentes(), subs.ausentes())
        return Preparacao(numero=numero_norm, uf=uf, docs=docs, brief=brief, hashes=hashes, achados=achados,
                          presentes=subs.presentes(), ausentes=subs.ausentes())

    def chave_de(self, prep: Preparacao) -> str:
        return chave_cache(prep.hashes, f"{prompts.VERSAO_PROMPT}+{parsing.VERSAO_PARSING}", self.modelo, hash_esquema())

    def processar(self, processo_dir: Path, numero: str | None = None, forcar: bool = False) -> Resultado:
        prep = self.preparar(processo_dir, numero)
        if not prep.docs or not any(d.trechos or d.fatos for d in prep.docs):
            raise ErroLLM(f"nenhum documento legível em {processo_dir}")
        chave = self.chave_de(prep)
        if not forcar and (entrada := self.cache.ler(chave)) and (res := _do_cache(entrada, prep, chave)):
            log.info("extractor %s: cache hit (%s…)", prep.numero, chave[:12])
            self._memoria[prep.numero] = res
            return res
        if self.cliente is None:
            raise ErroConfiguracao(f"OPENAI_API_KEY ausente e sem cache para o processo {prep.numero}")
        resp = self.cliente.completar(prompts.INSTRUCOES, prompts.montar_entrada(prep.brief), SaidaLLM)
        dados, analise = mapear(prep, resp.saida, resp.modelo)
        res = Resultado(numero=prep.numero, dados=dados, analise=analise, saida_llm=resp.saida, chave=chave,
                        modelo=resp.modelo, cache_hit=False, tokens_entrada=resp.tokens_entrada,
                        tokens_saida=resp.tokens_saida, brief=prep.brief, docs=prep.docs, achados=prep.achados,
                        tokens_cache=resp.tokens_cache, tokens_raciocinio=resp.tokens_raciocinio, segundos=resp.segundos)
        self.cache.gravar(chave, _payload(res, prep), prep.numero)
        self._memoria[prep.numero] = res
        log.info("extractor %s: LLM %s em %.1fs, %d+%d tokens (%d em cache, %d de raciocínio), %d docs, brief %d chars",
                 prep.numero, res.modelo, res.segundos, res.tokens_entrada, res.tokens_saida, res.tokens_cache,
                 res.tokens_raciocinio, len(prep.docs), len(prep.brief))
        return res

    # ---------------------------------------------------------------- contrato ExtratorDocs

    def extrair(self, processo_dir: Path, numero: str) -> DadosExtraidos:
        return self.processar(processo_dir, numero).dados

    def analisar(self, caso: CasoFeatures, dados: DadosExtraidos, scores: Scores) -> Analise:
        if res := self._memoria.get(caso.numero):
            return res.analise
        if (entrada := self.cache.ler_por_numero(caso.numero)) and "analise" in entrada:
            try:
                return Analise.model_validate(entrada["analise"])
            except ValueError:
                pass
        return self._analisar_de_dados(caso, dados)

    def redigir(self, caso: CasoFeatures, dados: DadosExtraidos, rec: Recomendacao) -> Minutas:
        return minutas_mod.redigir(caso, dados, rec)

    # ---------------------------------------------------------------- caminho raro: só os dados, sem brief

    def _analisar_de_dados(self, caso: CasoFeatures, dados: DadosExtraidos) -> Analise:
        """Quando `dados_extraidos` veio de data/derived/ e não há cache: analisa a partir do JSON."""
        corpo = dados.model_dump_json(indent=1)
        chave = hashlib.sha256(f"analise-de-dados|{prompts.VERSAO_PROMPT}|{self.modelo}|{corpo}".encode()).hexdigest()
        if entrada := self.cache.ler(chave):
            try:
                return Analise.model_validate(entrada["analise"])
            except (KeyError, ValueError):
                pass
        if self.cliente is None:
            raise ErroConfiguracao("OPENAI_API_KEY ausente e sem cache para analisar o processo")
        brief = (f"PROCESSO {caso.numero} · UF {caso.uf} · valor da causa {caso.valor_causa:.2f}\n"
                 f"Subsídios presentes: {', '.join(caso.subsidios.presentes()) or 'nenhum'}; "
                 f"ausentes: {', '.join(caso.subsidios.ausentes()) or 'nenhum'}\n"
                 "DADOS JÁ EXTRAÍDOS DOS AUTOS (JSON):\n" + corpo)
        resp = self.cliente.completar(prompts.INSTRUCOES + "\nATENÇÃO: só há dados já extraídos, sem trechos; "
                                      "preencha `dados` copiando-os e concentre-se em `analise`.",
                                      prompts.montar_entrada(brief), SaidaLLM)
        analise = _analise_de(caso.numero, resp.saida.analise, resp.modelo)
        self.cache.gravar(chave, {"numero": caso.numero, "chave": chave, "modelo": resp.modelo,
                                  "gerado_em": _agora().isoformat(), "analise": analise.model_dump(mode="json")})
        return analise


# ---------------------------------------------------------------- mapeamento LLM → contratos de core

def _agora() -> datetime:
    return datetime.now(UTC)


def _numero_da_pasta(pasta: Path) -> str:
    """data/exemplos/<numero>/ ou docs/Caso_01_0801234-56-2024-8-10-0001: pega os 20 dígitos do nome."""
    if m := re.search(r"\d{7}[-.]?\d{2}[-.]?\d{4}[-.]?\d[-.]?\d{2}[-.]?\d{4}", pasta.name):
        return m.group(0)
    return pasta.name


def _ou[T](valor_llm: T | None, valor_regra: T | None) -> T | None:
    return valor_llm if valor_llm is not None else valor_regra


def _data(iso: str | None, br: str | None) -> date | None:
    if iso:
        try:
            return date.fromisoformat(iso[:10])
        except ValueError:
            pass
    if br:
        return parsing._data_br(br)
    return None


def _cpf(valor: str | None) -> str | None:
    if valor and re.fullmatch(r"\d{3}\.\d{3}\.\d{3}-\d{2}", valor):
        return parsing._mascarar_cpf(valor)  # o LLM não deve devolver CPF inteiro; mascara por segurança
    return valor


def _fonte(valor: str | None, prep: Preparacao) -> str | None:
    """'AUTOS'/'[SUBSIDIOS]' não são arquivos: autos vira o nome da petição; subsídios genérico vira None."""
    if not valor:
        return None
    limpo = valor.strip("[] ").upper()
    if limpo == "AUTOS":
        return next((d.arquivo for d in prep.docs if d.pasta == "autos"), None)
    if limpo == "SUBSIDIOS":
        return None
    return valor


def mapear(prep: Preparacao, saida: SaidaLLM, modelo: str) -> tuple[DadosExtraidos, Analise]:
    f = prep.fatos_peticao
    d = saida.dados
    # "Canal de contratação" escrito num subsídio vence o LLM; sem isso, vale o que o LLM leu
    canal = parsing.canal_dos_subsidios(prep.docs) or d.contrato.canal
    autor = Pessoa(nome=_ou(d.autor.nome, f.get("autor_nome")), cpf_mascarado=_cpf(_ou(d.autor.cpf_mascarado, f.get("autor_cpf_mascarado"))),
                   idade=_ou(d.autor.idade, f.get("autor_idade")), email=_ou(d.autor.email, f.get("autor_email")),
                   telefone=d.autor.telefone)
    adv = Advogado(nome=_ou(d.advogado_autor.nome, f.get("advogado_nome")), oab=_ou(d.advogado_autor.oab, f.get("advogado_oab")),
                   email=_ou(d.advogado_autor.email, f.get("advogado_email")), telefone=d.advogado_autor.telefone,
                   cpf_mascarado=_cpf(d.advogado_autor.cpf_mascarado), idade=d.advogado_autor.idade)
    sinais_llm = [SinalAlerta(codigo=s.codigo, descricao=s.descricao, severidade=s.severidade, fonte=_fonte(s.fonte, prep))
                  for s in d.sinais_alerta]
    sinais, conta_terceiro = _reconciliar_sinais(prep, sinais_llm, canal, d.contrato.liveness, d.contrato.credito_conta_terceiro)
    contrato = ContratoInfo(
        canal=canal, assinatura=d.contrato.assinatura, credito_conta_terceiro=conta_terceiro,
        valor=_ou(d.contrato.valor, f.get("contrato_valor_alegado")),
        parcelas=_ou(d.contrato.parcelas, f.get("contrato_parcelas_alegadas")),
        data=_data(d.contrato.data, f.get("contrato_data_alegada")),
    )
    for doc in prep.docs:
        if motivo := seguranca.resumo_sinal(doc.achados):
            sinais.append(SinalAlerta(codigo=seguranca.CODIGO_SUSPEITO, descricao=motivo, severidade="alta",
                                      fonte=doc.arquivo))
    dados = DadosExtraidos(
        numero=prep.numero, origem=ORIGEM, modelo=modelo, autor=autor, advogado_autor=adv,
        comarca=_ou(d.comarca, f.get("comarca")), uf=prep.uf or d.uf or f.get("uf"),
        valor_causa=f.get("valor_causa") or d.valor_causa, pedidos=list(d.pedidos), contrato=contrato,
        sinais_alerta=sinais, resumo_fatos=d.resumo_fatos.strip(),
        confianca=min(1.0, max(0.0, float(d.confianca))), gerado_em=_agora(),
    )
    houve_injecao = any(a.codigo == "INJECAO_PROMPT" for a in prep.achados)
    return dados, _analise_de(prep.numero, saida.analise, modelo, houve_injecao, prep.ausentes)


def _reconciliar_sinais(prep: Preparacao, sinais_llm: list[SinalAlerta], canal: str, liveness: str,
                        conta_llm: bool | None) -> tuple[list[SinalAlerta], bool | None]:
    """Os sinais que a regra consegue decidir vencem o LLM: entram se faltam, saem se o LLM inventou.

    Vale para IDOSO (idade), BOLETIM_OCORRENCIA e RECLAMACAO_BACEN (petição), SEM_CONTRATO (subsídios),
    CREDITO_CONTA_TERCEIRO (banco depositário × petição) e LIVENESS_AUSENTE_CANAL_DIGITAL (canal × laudo).
    CREDITO_CONTA_TERCEIRO força acordo na política: um falso positivo custa dinheiro.
    """
    pet = next((d for d in prep.docs if d.tipo == "peticao"), None)
    f = pet.fatos if pet else {}
    ind = set(f.get("indicios", []))
    pet_arq = pet.arquivo if pet else None
    decididos: dict[str, tuple[bool, str, str | None, str]] = {}
    if (idade := f.get("autor_idade")) is not None:
        decididos["IDOSO"] = (idade >= 60, f"Autor com {idade} anos na data da petição", pet_arq, "media")
    if f.get("boletim_ocorrencia") or "boletim_ocorrencia" in ind:
        bo = f.get("boletim_ocorrencia")
        decididos["BOLETIM_OCORRENCIA"] = (True, "Há boletim de ocorrência" + (f" nº {bo}" if bo else ""), pet_arq, "media")
    if f.get("reclamacao_bacen_rdr") or "reclamacao_bacen" in ind:
        rdr = f.get("reclamacao_bacen_rdr")
        decididos["RECLAMACAO_BACEN"] = (True, "Há reclamação no BACEN" + (f" (RDR nº {rdr})" if rdr else ""), pet_arq, "media")
    decididos["SEM_CONTRATO"] = ("contrato" in prep.ausentes, "Banco não apresentou o contrato", None, "alta")
    conta: bool | None = None
    if pet and (dep := parsing.banco_depositario(prep.docs)):
        banco, arq = dep
        nega = parsing.nega_conta_deposito(pet, banco)
        if nega and parsing.BANCO_PROPRIO not in banco.lower():
            conta = True
            decididos["CREDITO_CONTA_TERCEIRO"] = (True, f"Crédito caiu em conta ({banco}) que o autor nega ter", arq, "alta")
        elif parsing.BANCO_PROPRIO in banco.lower() and not nega:
            conta = False
            decididos["CREDITO_CONTA_TERCEIRO"] = (False, "", arq, "alta")
    sem_liveness = liveness == "nao_localizado" or any(
        "liveness_nao_localizado" in d.fatos.get("indicios", []) for d in prep.docs if d.pasta != "autos")
    if canal in ("app", "internet_banking"):
        laudo = next((d.arquivo for d in prep.docs if "liveness_nao_localizado" in d.fatos.get("indicios", [])), None)
        decididos["LIVENESS_AUSENTE_CANAL_DIGITAL"] = (sem_liveness, "Contratação digital sem vídeo de liveness localizado",
                                                       laudo, "alta")
    elif canal != "desconhecido":  # canal não digital: o sinal não se aplica; se o LLM o emitiu, sai (força acordo)
        decididos["LIVENESS_AUSENTE_CANAL_DIGITAL"] = (False, "", None, "alta")
    finais = [s for s in sinais_llm if not (s.codigo in decididos and decididos[s.codigo][0] is False)]
    presentes = {s.codigo for s in finais}
    for codigo, (presente, descricao, fonte, severidade) in decididos.items():
        if presente and codigo not in presentes:
            finais.append(SinalAlerta(codigo=codigo, descricao=descricao, severidade=severidade, fonte=fonte))
    if conta is None:
        conta = True if "CREDITO_CONTA_TERCEIRO" in {s.codigo for s in finais} else conta_llm
    return finais, conta


_TAG_SUBSIDIO = {"contrato": r"\[contrato\]", "extrato": r"\[extrato\]", "comprovante_credito": r"\[comprovante\]",
                 "dossie": r"\[dossi[êe]\]", "demonstrativo_divida": r"\[demonstrativo\]", "laudo_referenciado": r"\[laudo\]"}
_DIZ_AUSENTE = re.compile(r"ausente|n[ãa]o\s+(foi\s+)?(apresentad|juntad|entregu|const)", re.IGNORECASE)


def _cita_ausente(item: str, ausentes: list[str]) -> bool:
    """Item de análise que atribui um fato a subsídio que o banco não entregou: o LLM inventou a fonte."""
    tags = [_TAG_SUBSIDIO[t] for t in ausentes if t in _TAG_SUBSIDIO]
    return any(re.search(tag, item, re.IGNORECASE) for tag in tags) and not _DIZ_AUSENTE.search(item)


def _analise_de(numero: str, a: AnaliseLLM, modelo: str, houve_injecao: bool = True,
                ausentes: list[str] | None = None) -> Analise:
    ausentes = list(ausentes or [])
    fortes = [p for p in a.pontos_fortes_banco if not _cita_ausente(p, ausentes)]
    riscos = [r for r in a.riscos if (houve_injecao or not re.search(r"instru[cç][ãa]o\s+embutida", r, re.IGNORECASE))
              and not _cita_ausente(r, ausentes)]
    contradicoes = [c for c in a.contradicoes if not _cita_ausente(c, ausentes)]
    descartados = len(a.pontos_fortes_banco) + len(a.riscos) + len(a.contradicoes) - len(fortes) - len(riscos) - len(contradicoes)
    if descartados:
        log.info("extractor %s: %d item(ns) de análise citavam subsídio ausente e saíram", numero, descartados)
    for c in contradicoes:  # contradição da petição favorece o banco; inconsistência entre subsídios é risco
        (fortes if re.match(r"\s*peti[cç][ãa]o", c, re.IGNORECASE) else riscos).append(f"Contradição: {c}")
    texto_final = a.texto.strip()
    if contradicoes:
        texto_final += "\n\nContradições identificadas: " + " ".join(contradicoes)
    return Analise(numero=numero, origem=f"{ORIGEM}:{modelo}", pontos_fortes_banco=fortes,
                   pontos_fracos_banco=list(a.pontos_fracos_banco), tese_provavel_autor=a.tese_provavel_autor.strip(),
                   riscos=riscos, texto=texto_final)


# ---------------------------------------------------------------- cache

def _payload(res: Resultado, prep: Preparacao) -> dict[str, Any]:
    return {
        "numero": res.numero, "chave": res.chave, "modelo": res.modelo, "versao_prompt": prompts.VERSAO_PROMPT,
        "hash_esquema": hash_esquema(), "gerado_em": _agora().isoformat(),
        "tokens": {"entrada": res.tokens_entrada, "saida": res.tokens_saida, "cache": res.tokens_cache,
                   "raciocinio": res.tokens_raciocinio, "segundos": res.segundos},
        "documentos": [{"arquivo": d.arquivo, "pasta": d.pasta, "tipo": d.tipo, "paginas": d.paginas,
                        "chars": d.chars, "chars_brief": d.chars_brief, "leitor": d.leitor,
                        "sha256": dict(prep.hashes).get(f"{d.pasta}/{d.arquivo}")} for d in prep.docs],
        "achados": [{"codigo": a.codigo, "descricao": a.descricao, "severidade": a.severidade,
                     "arquivo": a.arquivo, "trecho": a.trecho} for a in prep.achados],
        "brief": prep.brief,
        "saida_llm": res.saida_llm.model_dump(),
        "dados": res.dados.model_dump(mode="json"),
        "analise": res.analise.model_dump(mode="json"),
    }


def _do_cache(entrada: dict[str, Any], prep: Preparacao, chave: str) -> Resultado | None:
    """Reaplica `mapear` (regras atuais) sobre a saída gravada do LLM: correção de regra vale sem nova chamada."""
    try:
        gerado_em = DadosExtraidos.model_validate(entrada["dados"]).gerado_em
        saida = SaidaLLM.model_validate(entrada["saida_llm"])
    except (KeyError, ValueError) as exc:
        log.warning("cache %s… incompatível (%s); recomputando", chave[:12], exc)
        return None
    modelo = str(entrada.get("modelo") or "")
    dados, analise = mapear(prep, saida, modelo)
    dados = dados.model_copy(update={"gerado_em": gerado_em})
    tokens = entrada.get("tokens") or {}
    return Resultado(numero=prep.numero, dados=dados, analise=analise, saida_llm=saida, chave=chave,
                     modelo=modelo, cache_hit=True,
                     tokens_entrada=int(tokens.get("entrada", 0)), tokens_saida=int(tokens.get("saida", 0)),
                     brief=prep.brief, docs=prep.docs, achados=prep.achados,
                     tokens_cache=int(tokens.get("cache", 0)), tokens_raciocinio=int(tokens.get("raciocinio", 0)),
                     segundos=float(tokens.get("segundos", 0.0)))
