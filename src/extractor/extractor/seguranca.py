"""Validação de segurança antes de qualquer coisa chegar ao LLM.

Duas camadas: a estrutura do PDF (scripts, ações automáticas, anexos embutidos, cifra) e o texto
(caracteres invisíveis ou de controle, blobs codificados e instruções embutidas — prompt injection).
Política: sanitizar e sinalizar. O trecho suspeito sai do texto; o documento continua no brief;
o achado vira um sinal DOCUMENTO_SUSPEITO com o arquivo em `fonte`.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from pypdf import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject

Severidade = Literal["baixa", "media", "alta"]
CODIGO_SUSPEITO = "DOCUMENTO_SUSPEITO"


@dataclass(frozen=True)
class Achado:
    codigo: str  # PDF_JAVASCRIPT, PDF_ACAO_AUTOMATICA, PDF_ANEXO_EMBUTIDO, TEXTO_INVISIVEL, INJECAO_PROMPT, …
    descricao: str
    severidade: Severidade
    arquivo: str
    trecho: str | None = None

    @property
    def grave(self) -> bool:
        return self.severidade == "alta"


# ---------------------------------------------------------------- estrutura do PDF

_ACOES_PERIGOSAS = {"/JavaScript", "/Launch", "/SubmitForm", "/ImportData", "/GoToR"}


def _resolver(obj):
    return obj.get_object() if isinstance(obj, IndirectObject) else obj


def _acoes_de(obj, vistos: set[int], profundidade: int = 0) -> set[str]:
    """Tipos /S de ações encontrados num objeto (recursivo em /Next e dicionários filhos)."""
    tipos: set[str] = set()
    if profundidade > 6:
        return tipos
    obj = _resolver(obj)
    if isinstance(obj, DictionaryObject):
        if id(obj) in vistos:
            return tipos
        vistos.add(id(obj))
        s = obj.get("/S")
        if isinstance(s, NameObject):
            tipos.add(str(s))
        if "/JS" in obj:
            tipos.add("/JavaScript")
        for chave in ("/Next", "/A", "/AA", "/O", "/C", "/D", "/E", "/U", "/Fo", "/Bl", "/PO", "/PC"):
            if chave in obj:
                tipos |= _acoes_de(obj[chave], vistos, profundidade + 1)
    elif isinstance(obj, ArrayObject):
        for item in obj:
            tipos |= _acoes_de(item, vistos, profundidade + 1)
    return tipos


def inspecionar_pdf(reader: PdfReader, arquivo: str) -> list[Achado]:
    """Scripts, ações automáticas, anexos embutidos e formulários XFA no catálogo e nas páginas."""
    achados: list[Achado] = []
    try:
        raiz = reader.root_object
        vistos: set[int] = set()
        nomes = _resolver(raiz.get("/Names")) if "/Names" in raiz else None
        if isinstance(nomes, DictionaryObject):
            if "/JavaScript" in nomes:
                achados.append(Achado("PDF_JAVASCRIPT", "PDF contém JavaScript no catálogo", "alta", arquivo))
            if "/EmbeddedFiles" in nomes:
                achados.append(Achado("PDF_ANEXO_EMBUTIDO", "PDF contém arquivos embutidos", "media", arquivo))
        for chave in ("/OpenAction", "/AA"):
            if chave in raiz:
                tipos = _acoes_de(raiz[chave], vistos)
                perigosas = sorted(tipos & _ACOES_PERIGOSAS)
                achados.append(Achado(
                    "PDF_ACAO_AUTOMATICA",
                    f"PDF executa ação ao abrir ({chave}{': ' + ', '.join(perigosas) if perigosas else ''})",
                    "alta" if perigosas else "media", arquivo))
        acro = _resolver(raiz.get("/AcroForm")) if "/AcroForm" in raiz else None
        if isinstance(acro, DictionaryObject) and "/XFA" in acro:
            achados.append(Achado("PDF_XFA", "PDF com formulário XFA", "baixa", arquivo))
        for i, pagina in enumerate(reader.pages):
            if i >= 200:
                break
            anots = _resolver(pagina.get("/Annots")) if "/Annots" in pagina else None
            if not isinstance(anots, ArrayObject):
                continue
            tipos: set[str] = set()
            for anot in anots:
                anot = _resolver(anot)
                if isinstance(anot, DictionaryObject):
                    for chave in ("/A", "/AA"):
                        if chave in anot:
                            tipos |= _acoes_de(anot[chave], vistos)
                    if anot.get("/Subtype") == "/FileAttachment":
                        tipos.add("/FileAttachment")
            perigosas = sorted(tipos & _ACOES_PERIGOSAS)
            if perigosas:
                achados.append(Achado("PDF_ACAO_ANOTACAO", f"página {i + 1} com ação {', '.join(perigosas)}",
                                      "alta", arquivo))
            if "/FileAttachment" in tipos:
                achados.append(Achado("PDF_ANEXO_EMBUTIDO", f"página {i + 1} com anexo embutido", "media",
                                      arquivo))
    except Exception as exc:  # noqa: BLE001 - inspeção nunca derruba a leitura
        achados.append(Achado("PDF_INSPECAO_FALHOU", f"não foi possível inspecionar a estrutura ({exc})",
                              "baixa", arquivo))
    return achados


# ---------------------------------------------------------------- texto

_INVISIVEIS = re.compile(r"[\u200b-\u200f\u2028-\u202e\u2060-\u2064\u2066-\u2069\ufeff\u00ad\u180e]")
_CONTROLE = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f-\x9f]")
_BASE64 = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{160,}={0,2}(?![A-Za-z0-9+/])")
_RUIDO = re.compile(r"([_\-=*#.·•]){12,}")

# Frases-chave de instrução ao sistema, em português e inglês. Cada casamento remove a linha em que
# aparece e gera um achado INJECAO_PROMPT (alta). Petições e laudos não falam com modelos de linguagem.
_PADROES_INJECAO: list[tuple[str, str]] = [
    ("ignorar instruções", (
        r"\b(ignor\w*|desconsider\w*|esque[cç]\w*)\s+(todas?\s+)?(as\s+|os\s+)?(suas\s+)?"
        r"(instru[cç][õo]es|regras|orienta[cç][õo]es|diretrizes|prompts?)\s*"
        r"(anteriores|acima|pr[ée]vi\w+|do\s+sistema|iniciais|originais)?")),
    ("ignore instructions", (
        r"\b(ignore|disregard|forget|override)\s+(all\s+|any\s+)?(the\s+|your\s+)?"
        r"(previous|prior|above|earlier|system|initial|original)?\s*"
        r"(instructions?|prompts?|rules|guidelines|directives)\b")),
    ("prompt do sistema", r"\b(system\s+prompt|prompt\s+d[oe]\s+sistema|mensagem\s+d[oe]\s+sistema)\b"),
    ("papel do modelo", (
        r"\b(voc[êe]\s+(é|e|est[áa]|ser[áa]|deve\s+agir\s+como|passa\s+a\s+ser)"
        r"|you\s+(are|will\s+be|must\s+act\s+as|should\s+act\s+as))\s+(agora\s+|now\s+)?"
        r"(um|uma|o|a|an?|the)\s+(assistente|assistant|modelo|model|ia|ai|intelig[êe]ncia\s+artificial"
        r"|chatbot|advogad[oa]\s+d[oa]\s+autor\w*)\b")),
    ("menção a modelo de linguagem", (
        r"\b(chatgpt|gpt-?[0-9o]\w*|openai|claude|anthropic|gemini|copilot|llm|large\s+language\s+model"
        r"|modelo\s+de\s+linguagem|assistente\s+virtual|intelig[êe]ncia\s+artificial\s+que\s+l[êe])\b")),
    ("saída forçada", (
        r"\b(responda|respond|reply|answer|retorne|return|devolva|output|imprima|print)\s+"
        r"(apenas|somente|s[óo]|only|exclusivamente|exactly|exatamente)\b")),
    ("decisão forçada", (
        r"\b(recomende|recomendar|classifique|classificar|marque|defina|conclua|considere|set|classify"
        r"|recommend|mark)\s+(este|esse|o|a|this|the)?\s*(caso|processo|case|decis[ãa]o|decision"
        r"|p_?[eê]xito|probabilidade|probability|confian[cç]a|confidence)\s*(como|com|=|as|to)\s*"
        r"[\"“']?(acordo|defesa|settlement|defen[cs]e|alta|baixa|high|low|1|0|100%)")),
    ("recomendação forçada", (
        r"\b(recomende|recommend|sugira|suggest|conclua\s+pel[oa])\s+(o\s+|a\s+|the\s+|um\s+|a\s+)?"
        r"(acordo|defesa|settlement|defen[cs]e)\b")),
    ("ocultar instruções", (
        r"\b(n[ãa]o|nunca|do\s+not|don'?t|never)\s+(mencione|revele|informe|cite|mention|reveal"
        r"|disclose|tell)\b[^.\n]{0,60}\b(instru[cç]|prompt|system|sistema|regra|rule)")),
    ("marcadores de chat", (
        r"(<\|?\s*(im_start|im_end|system|assistant|endoftext)\s*\|?>|\[/?(INST|SYS|SYSTEM)\]"
        r"|^\s*(system|assistant|developer)\s*:\s"
        r"|^\s*#{1,6}\s*(system|instruction|instru[cç][ãa]o|assistant)s?\b)")),
    ("jailbreak", (
        r"\b(jailbreak|dan\s+mode|developer\s+mode|modo\s+desenvolvedor"
        r"|sem\s+restri[cç][õo]es\s+de\s+seguran[cç]a)\b")),
    ("nova diretriz", (
        r"\b(a\s+partir\s+de\s+agora|de\s+agora\s+em\s+diante|from\s+now\s+on|nova\s+instru[cç][ãa]o"
        r"|new\s+instructions?)\b[^.\n]{0,80}\b(voc[êe]|you|responda|respond|ignor\w*|recomend\w*|classifi\w*)")),
    ("execução", (
        r"\b(tool_call|function_call|<function|execute\s+(the\s+)?(code|command|script)"
        r"|execute\s+o\s+(c[óo]digo|comando|script)|rode\s+o\s+(c[óo]digo|comando))\b")),
]
_INJECAO = [(rotulo, re.compile(padrao, re.IGNORECASE | re.MULTILINE)) for rotulo, padrao in _PADROES_INJECAO]


def sanitizar(texto: str, arquivo: str) -> tuple[str, list[Achado]]:
    """Remove controle, invisíveis e ruído de layout; normaliza NFC. Devolve o texto limpo e os achados."""
    achados: list[Achado] = []
    texto = unicodedata.normalize("NFC", texto)
    n_inv = len(_INVISIVEIS.findall(texto))
    n_ctl = len(_CONTROLE.findall(texto))
    if n_inv:
        achados.append(Achado("TEXTO_INVISIVEL", f"{n_inv} caracteres invisíveis ou de direção removidos",
                              "media" if n_inv >= 5 else "baixa", arquivo))
    if n_ctl >= 5:
        achados.append(Achado("TEXTO_CONTROLE", f"{n_ctl} caracteres de controle removidos", "baixa", arquivo))
    texto = _INVISIVEIS.sub("", texto)
    texto = _CONTROLE.sub("", texto)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = _RUIDO.sub(lambda m: m.group(1) * 3, texto)
    texto = re.sub(r"[ \t]+\n", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto, achados


def _linha_de(texto: str, inicio: int, fim: int) -> tuple[int, int]:
    a = texto.rfind("\n", 0, inicio) + 1
    b = texto.find("\n", fim)
    return a, (len(texto) if b == -1 else b)


def detectar_injecao(texto: str, arquivo: str) -> tuple[str, list[Achado]]:
    """Remove as linhas com instrução embutida ou blob codificado e devolve um achado por ocorrência."""
    achados: list[Achado] = []
    remover: list[tuple[int, int]] = []
    linhas_vistas: set[tuple[int, int]] = set()
    for rotulo, padrao in _INJECAO:
        for m in padrao.finditer(texto):
            a, b = _linha_de(texto, m.start(), m.end())
            if (a, b) in linhas_vistas:  # uma linha, um achado, mesmo casando vários padrões
                continue
            linhas_vistas.add((a, b))
            trecho = " ".join(texto[a:b].split())[:160]
            remover.append((a, b))
            achados.append(Achado("INJECAO_PROMPT", f"instrução embutida ({rotulo}) em {arquivo}", "alta",
                                  arquivo, trecho))
    for m in _BASE64.finditer(texto):
        remover.append((m.start(), m.end()))
        achados.append(Achado("TEXTO_CODIFICADO", f"blob codificado de {m.end() - m.start()} caracteres removido",
                              "media", arquivo, texto[m.start():m.start() + 40] + "…"))
    if not remover:
        return texto, achados
    remover.sort()
    partes: list[str] = []
    cursor = 0
    for a, b in remover:
        if a < cursor:
            cursor = max(cursor, b)
            continue
        partes.append(texto[cursor:a])
        cursor = b
    partes.append(texto[cursor:])
    limpo = re.sub(r"\n{3,}", "\n\n", "".join(partes))
    return limpo, achados


def validar_texto(texto: str, arquivo: str) -> tuple[str, list[Achado]]:
    """sanitizar + detectar_injecao. O texto devolvido é o único que pode seguir para o parsing."""
    limpo, achados = sanitizar(texto, arquivo)
    limpo, mais = detectar_injecao(limpo, arquivo)
    return limpo, achados + mais


def resumo_sinal(achados: list[Achado]) -> str | None:
    """Descrição única para o sinal DOCUMENTO_SUSPEITO de um arquivo, ou None se não há motivo grave."""
    graves = [a for a in achados if a.severidade in ("alta", "media") and a.codigo != "PDF_INSPECAO_FALHOU"]
    if not graves:
        return None
    partes = []
    for a in graves[:3]:
        partes.append(f"{a.descricao}" + (f": “{a.trecho}”" if a.trecho else ""))
    extra = f" (+{len(graves) - 3})" if len(graves) > 3 else ""
    return "; ".join(partes) + extra
