"""Extrator de P3: implementa `core.docs.ExtratorDocs` (EXTRACTOR_IMPL=extractor.pipeline:Extrator).

Fluxo por processo: ler PDFs/TXT → validar segurança → parsing → brief → cache? → LLM (uma chamada
devolve `resumo` em bullets e `contradicoes`) → montar os contratos de core → gravar cache. Em
`DadosExtraidos` só `resumo_fatos` e `comentarios_documentos` vêm do LLM; autor, advogado, contrato e
sinais vêm de regra (petição por regex, subsídios por rótulo e indício, UF pelo CNJ). `extrair` e
`analisar` servem do mesmo resultado; `redigir` é template, sem LLM. Instanciável sem argumentos: lê
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
from core.caso import NOMES_SUBSIDIOS, CasoFeatures
from core.docs import (
    Advogado,
    Analise,
    ComentarioDocumento,
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
from extractor.schema import SaidaLLM, hash_esquema
from extractor.seguranca import Achado

log = logging.getLogger(__name__)
ORIGEM = "llm"
MAX_BULLETS = 5


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

    @property
    def subsidios(self) -> list[parsing.DocParseado]:
        return [d for d in self.docs if d.pasta != "autos"]


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
                                      "resuma o que eles dizem e aponte contradição só se estiver explícita neles.",
                                      prompts.montar_entrada(brief), SaidaLLM)
        ausentes = caso.subsidios.ausentes()
        analise = _analise_de(caso.numero, resp.modelo, _itens(resp.saida.contradicoes, ausentes), ausentes,
                              dados.sinais_alerta)
        self.cache.gravar(chave, {"numero": caso.numero, "chave": chave, "modelo": resp.modelo,
                                  "gerado_em": _agora().isoformat(), "analise": analise.model_dump(mode="json")})
        return analise


# ---------------------------------------------------------------- mapeamento regras + LLM → contratos de core

def _agora() -> datetime:
    return datetime.now(UTC)


def _numero_da_pasta(pasta: Path) -> str:
    """data/exemplos/<numero>/ ou docs/Caso_01_0801234-56-2024-8-10-0001: pega os 20 dígitos do nome."""
    if m := re.search(r"\d{7}[-.]?\d{2}[-.]?\d{4}[-.]?\d[-.]?\d{2}[-.]?\d{4}", pasta.name):
        return m.group(0)
    return pasta.name


def _ou[T](primeiro: T | None, segundo: T | None) -> T | None:
    return primeiro if primeiro is not None else segundo


def _data(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return parsing._data_br(s)


def _arquivo_com_indicio(docs: list[parsing.DocParseado], indicio: str) -> str | None:
    return next((d.arquivo for d in docs if indicio in d.fatos.get("indicios", [])), None)


def _campo(docs: list[parsing.DocParseado], padrao_rotulo: str) -> str | None:
    """Primeiro valor dos pares rótulo/valor dos subsídios cujo rótulo casa com o padrão."""
    for d in docs:
        for rotulo, valor in d.fatos.get("campos", {}).items():
            if re.search(padrao_rotulo, rotulo, re.IGNORECASE):
                return valor
    return None


def _valor_brl(s: str | None) -> float | None:
    if s and (m := re.search(r"\d[\d.]*(?:,\d{1,2})?", s)):
        return parsing._brl(m.group(0))
    return None


def _inteiro(s: str | None) -> int | None:
    if s and (m := re.search(r"\d+", s)):
        return int(m.group(0))
    return None


def _assinatura(subs: list[parsing.DocParseado], ausentes: list[str]) -> str:
    ind = {i for d in subs for i in d.fatos.get("indicios", [])}
    if "assinatura_manuscrita" in ind:
        return "fisica"
    if "biometria_ou_liveness" in ind:
        return "biometria"
    if "assinatura_eletronica" in ind:
        return "digital"
    return "ausente" if "contrato" in ausentes else "desconhecida"


def _confianca(prep: Preparacao) -> float:
    """Completude do material: petição legível + fração dos seis subsídios entregues."""
    peticao = 1 if any(d.tipo == "peticao" and (d.trechos or d.fatos) for d in prep.docs) else 0
    return round((peticao + len(prep.presentes)) / (1 + len(NOMES_SUBSIDIOS)), 2)


def mapear(prep: Preparacao, saida: SaidaLLM, modelo: str) -> tuple[DadosExtraidos, Analise]:
    """Dados, contrato e sinais vêm das regras; do LLM entram só o resumo em bullets e as contradições."""
    f = prep.fatos_peticao
    subs = prep.subsidios
    canal = parsing.canal_dos_subsidios(prep.docs) or "desconhecido"
    liveness = "nao_localizado" if _arquivo_com_indicio(subs, "liveness_nao_localizado") else "desconhecido"
    sinais, conta_terceiro = _sinais_por_regra(prep, canal, liveness)
    for doc in prep.docs:
        if motivo := seguranca.resumo_sinal(doc.achados):
            sinais.append(SinalAlerta(codigo=seguranca.CODIGO_SUSPEITO, descricao=motivo, severidade="alta",
                                      fonte=doc.arquivo))
    contrato = ContratoInfo(
        canal=canal, assinatura=_assinatura(subs, prep.ausentes), credito_conta_terceiro=conta_terceiro,
        valor=_ou(f.get("contrato_valor_alegado"), _valor_brl(_campo(subs, r"valor (da opera|l[íi]quido|liberado|financiado)"))),
        parcelas=_ou(f.get("contrato_parcelas_alegadas"), _inteiro(_campo(subs, r"(n[úu]mero|n[ºo°]) de parcelas|^prazo"))),
        data=_data(_ou(f.get("contrato_data_alegada"), _campo(subs, r"data da contrata"))),
    )
    resumo = _itens(saida.resumo, prep.ausentes)[:MAX_BULLETS]
    contradicoes = _itens(saida.contradicoes, prep.ausentes)
    dados = DadosExtraidos(
        numero=prep.numero, origem=ORIGEM, modelo=modelo,
        autor=Pessoa(nome=f.get("autor_nome"), cpf_mascarado=f.get("autor_cpf_mascarado"), idade=f.get("autor_idade"),
                     email=f.get("autor_email"), telefone=None),
        advogado_autor=Advogado(nome=f.get("advogado_nome"), oab=f.get("advogado_oab"), email=f.get("advogado_email"),
                                telefone=None, cpf_mascarado=None, idade=None),
        comarca=f.get("comarca"), uf=prep.uf or f.get("uf"), valor_causa=f.get("valor_causa"), pedidos=[],
        contrato=contrato, sinais_alerta=sinais, comentarios_documentos=_comentarios(resumo, contradicoes, prep.docs),
        resumo_fatos="\n".join(resumo), confianca=_confianca(prep), gerado_em=_agora(),
    )
    return dados, _analise_de(prep.numero, modelo, contradicoes, prep.ausentes, sinais)


def _sinais_por_regra(prep: Preparacao, canal: str, liveness: str) -> tuple[list[SinalAlerta], bool | None]:
    """Sinais decididos por regra (decisão 42): o LLM não emite sinal, então não há o que reconciliar.

    IDOSO (idade pelo RG e data da petição), BOLETIM_OCORRENCIA e RECLAMACAO_BACEN (petição), SEM_CONTRATO
    (subsídios entregues), CREDITO_CONTA_TERCEIRO (banco depositário × petição negando a conta),
    LIVENESS_AUSENTE_CANAL_DIGITAL (canal digital × laudo) e ASSINATURA_DIVERGENTE (perícia).
    """
    pet = next((d for d in prep.docs if d.tipo == "peticao"), None)
    f = pet.fatos if pet else {}
    ind = set(f.get("indicios", []))
    pet_arq = pet.arquivo if pet else None
    sinais: list[SinalAlerta] = []
    if (idade := f.get("autor_idade")) is not None and idade >= 60:
        sinais.append(SinalAlerta(codigo="IDOSO", descricao=f"Autor com {idade} anos na data da petição",
                                  severidade="media", fonte=pet_arq))
    if f.get("boletim_ocorrencia") or "boletim_ocorrencia" in ind:
        bo = f.get("boletim_ocorrencia")
        sinais.append(SinalAlerta(codigo="BOLETIM_OCORRENCIA", descricao="Há boletim de ocorrência" + (f" nº {bo}" if bo else ""),
                                  severidade="media", fonte=pet_arq))
    if f.get("reclamacao_bacen_rdr") or "reclamacao_bacen" in ind:
        rdr = f.get("reclamacao_bacen_rdr")
        sinais.append(SinalAlerta(codigo="RECLAMACAO_BACEN", descricao="Há reclamação no BACEN" + (f" (RDR nº {rdr})" if rdr else ""),
                                  severidade="media", fonte=pet_arq))
    if "contrato" in prep.ausentes:
        sinais.append(SinalAlerta(codigo="SEM_CONTRATO", descricao="Banco não apresentou o contrato", severidade="alta", fonte=None))
    conta: bool | None = None
    if pet and (dep := parsing.banco_depositario(prep.docs)):
        banco, arq = dep
        nega = parsing.nega_conta_deposito(pet, banco)
        if nega and parsing.BANCO_PROPRIO not in banco.lower():
            conta = True
            sinais.append(SinalAlerta(codigo="CREDITO_CONTA_TERCEIRO", descricao=f"Crédito caiu em conta ({banco}) que o autor nega ter",
                                      severidade="alta", fonte=arq))
        elif parsing.BANCO_PROPRIO in banco.lower() and not nega:
            conta = False
    if canal in ("app", "internet_banking") and liveness == "nao_localizado":
        sinais.append(SinalAlerta(codigo="LIVENESS_AUSENTE_CANAL_DIGITAL", descricao="Contratação digital sem vídeo de liveness localizado",
                                  severidade="alta", fonte=_arquivo_com_indicio(prep.subsidios, "liveness_nao_localizado")))
    if arq := _arquivo_com_indicio(prep.subsidios, "assinatura_divergente"):
        sinais.append(SinalAlerta(codigo="ASSINATURA_DIVERGENTE", descricao="Perícia aponta assinatura divergente",
                                  severidade="alta", fonte=arq))
    return sinais, conta


# tags aceitam sufixo ("[Laudo_Referenciado]", "[Comprovante BACEN]"): o modelo nem sempre usa a forma curta
_TAG_SUBSIDIO = {"contrato": r"\[contrato[^\]]*\]", "extrato": r"\[extrato[^\]]*\]", "comprovante_credito": r"\[comprovante[^\]]*\]",
                 "dossie": r"\[dossi[êe][^\]]*\]", "demonstrativo_divida": r"\[demonstrativo[^\]]*\]",
                 "laudo_referenciado": r"\[laudo[^\]]*\]"}
_TAG_TIPO = {"peticao": r"\[peti[cç][ãa]o[^\]]*\]"} | _TAG_SUBSIDIO
_DIZ_AUSENTE = re.compile(r"ausente|n[ãa]o\s+(foi\s+)?(apresentad|juntad|entregu|const)", re.IGNORECASE)
_MARCADOR = re.compile(r"^[-•*·]+\s*")


def _cita_ausente(item: str, ausentes: list[str]) -> bool:
    """Item que atribui um fato a subsídio que o banco não entregou: o LLM inventou a fonte."""
    tags = [_TAG_SUBSIDIO[t] for t in ausentes if t in _TAG_SUBSIDIO]
    return any(re.search(tag, item, re.IGNORECASE) for tag in tags) and not _DIZ_AUSENTE.search(item)


def _itens(brutos: list[str], ausentes: list[str]) -> list[str]:
    """Uma linha por item, sem marcador, sem repetição e sem citar subsídio que o banco não entregou."""
    itens: list[str] = []
    for bruto in brutos:
        item = _MARCADOR.sub("", " ".join(bruto.split()))
        if item and item not in itens and not _cita_ausente(item, ausentes):
            itens.append(item)
    if descartados := len(brutos) - len(itens):
        log.info("extractor: %d item(ns) do LLM saíram (vazios, repetidos ou citando subsídio ausente)", descartados)
    return itens


def _comentarios(resumo: list[str], contradicoes: list[str], docs: list[parsing.DocParseado]) -> list[ComentarioDocumento]:
    """O comentário de cada documento é o bullet do resumo que o cita; alta relevância se entra numa contradição."""
    lista: list[ComentarioDocumento] = []
    for d in docs:
        if not (padrao := _TAG_TIPO.get(d.tipo)):
            continue
        tag = re.compile(padrao, re.IGNORECASE)
        bullets = [tag.sub("", b).strip(" :;-") for b in resumo if tag.search(b)]
        if not bullets:
            continue
        em_contradicao = any(tag.search(c) for c in contradicoes) or (d.tipo == "peticao" and bool(contradicoes))
        lista.append(ComentarioDocumento(arquivo=d.arquivo, relevancia="alta" if em_contradicao else "media",
                                         comentario=" ".join(bullets)))
    return lista


def _analise_de(numero: str, modelo: str, contradicoes: list[str], ausentes: list[str],
                sinais: list[SinalAlerta]) -> Analise:
    """Contradições do LLM em campo próprio; o que falta e os sinais de regra em pontos fracos. Sem tese nem parecer."""
    fracos = [f"{NOMES_SUBSIDIOS.get(k, k)} não apresentado pelo banco" for k in ausentes]
    fracos += [s.descricao for s in sinais if s.severidade == "alta" and s.codigo != "SEM_CONTRATO"]
    return Analise(numero=numero, origem=f"{ORIGEM}:{modelo}", contradicoes=contradicoes, pontos_fortes_banco=[],
                   pontos_fracos_banco=fracos, tese_provavel_autor="", riscos=[s.descricao for s in sinais], texto="")


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
