"""Ficha do caso: fatos extraídos dos PDFs pela LLM; números e decisão pelo engine de política."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal

from core.caso import Subsidios
from core.cnj import normalizar, uf_do_numero
from core.docs import subsidios_por_arquivos
from core.politica import brl
from enteros import config as cfg
from enteros.schemas import CaseFeatures, DocsStatus, Recomendacao
from pydantic import BaseModel, Field, ValidationError

from extractor.leitura import ErroLeitura, ler_pdf
from extractor.resumo import LIMITE_CARACTERES, MODELO_PADRAO, ErroResumo, _cliente

INSTRUCOES_CASO = """\
Você é analista jurídico de um banco réu em ação de empréstimo consignado não reconhecido.
Recebe os autos (petição inicial e anexos) e os subsídios do banco, cada arquivo num bloco
"=== arquivo (autos|subsídio) ===", com as páginas marcadas "[página N]".
Preencha os campos só com o que está escrito nos documentos. Não invente; use null ou lista vazia
quando não constar. Nunca liste como item algo ausente ("não mencionado", "não consta").
Itens de lista em estilo telegráfico (até ~20 palavras), sem repetir o que está em outro campo.

- numero_processo: formato CNJ com pontos (0000000-00.0000.0.00.0000).
- comarca: só a cidade, sem a UF.
- Valores em reais como número (15000.0).
- autor_idade: pela data de nascimento do documento de identidade, na data da petição.
- canal_contratacao e assinatura: como os subsídios do banco documentam (contrato, comprovante,
  laudo, dossiê). Curto: "Correspondente bancário por telemarketing", "App mobile self-service";
  assinatura "manuscrita", "biometria facial" (autenticação por biometria ou liveness, mesmo que o
  vídeo falte) ou "eletrônica" (só senha ou aceite).
- sub_assunto: "Golpe" se o autor atribui a contratação a fraude de terceiro (uso indevido de
  dados, crédito em conta que não é dele, boletim de ocorrência); "Genérico" se só nega ter
  contratado.
- destaques_subsidios: um item por arquivo de subsídio, começando pelo tipo do documento como está
  no nome do arquivo ("Contrato:", "Extrato:", "Dossiê:", "Laudo:"), só com o dado decisivo que
  prova ou enfraquece a contratação (ex.: "Dossiê: assinatura 91%, liveness 97,3%"; "Laudo:
  vídeo de liveness não localizado"). Atribua cada dado ao arquivo em que ele aparece. Não cite
  documento que não está entre os blocos.
- prova_de_proveito: quem recebeu e usou o crédito, um fato por item: a conta em que caiu e de
  quem é (ex.: "crédito R$ 5.000 na conta da autora"; "crédito em conta Caixa que o autor diz não
  ter") e cada movimentação posterior (ex.: "TED R$ 3.000 p/ conta própria Bradesco", "PIX
  R$ 1.500 p/ familiar", "saque ATM R$ 485 em São Luís"). Sem movimentação, não escreva item
  dizendo que falta. Parcelas descontadas do benefício não são proveito.
- conta_credito_titular_autor: true se o crédito caiu em conta do autor e ele não nega essa conta;
  false se o autor diz que a conta não é dele; null se não dá para saber.
- liveness_presente: true se selfie ou liveness foi confirmado; false se um documento diz que
  falta ou não foi localizado; null se não se aplica.
- indicios: fatos presentes nos autos que favorecem o autor, curtos: "BO nº ...", "RDR BACEN
  nº ...", "reclamação Procon", "conta de crédito que o autor nega ter". Não repita a idade nem o
  que já está em destaques ou prova de proveito.
- contradicoes: confronte cada afirmação de fato da petição (não usou os valores, não há
  movimentação no extrato, não tem conta no banco X, nunca usou aplicativo, nunca assinou) com o
  que os subsídios mostram. Registre só quando uma prova objetiva desmente o fato: extrato com
  movimentação, perícia ou dossiê de terceiro, gravação, selfie confirmada. Registro interno do
  banco que só afirma a contratação (laudo, comprovante, "artefatos preservados") não basta, e
  documento que repete a alegação do autor não é contradição. No máximo 3, a mais forte
  primeiro, no formato 'Petição (p. N): "<trecho literal curto>" × <documento> (p. N): <o que
  ele mostra>'. Lista vazia se não houver.
Escreva em português.
"""

_IDADE = re.compile(r"\bidos[oa]s?\b|\d+\s*anos", re.IGNORECASE)

# nome do arquivo ou pasta que indica os autos (petição); o resto é subsídio do banco
_AUTOS = re.compile(r"autos|peti[cç][aã]o|inicial")

# flag de subsídio no core → nome no engine e rótulo curto na ficha
_DOCS: dict[str, tuple[str, str]] = {
    "contrato": ("contrato", "contrato"),
    "extrato": ("extrato", "extrato"),
    "comprovante_credito": ("comprovante", "comprovante BACEN"),
    "dossie": ("dossie", "dossiê"),
    "demonstrativo_divida": ("demonstrativo", "demonstrativo"),
    "laudo_referenciado": ("laudo", "laudo"),
}


class Documento(BaseModel):
    nome: str
    tipo: Literal["autos", "subsidio"]
    texto: str


class ExtracaoCaso(BaseModel):
    """Saída estruturada da LLM. Sem defaults: o schema estrito da OpenAI exige todos os campos."""

    numero_processo: str | None = Field(description="número CNJ do processo")
    comarca: str | None
    uf: str | None = Field(description="sigla da UF")
    autor_nome: str | None
    autor_idade: int | None
    valor_causa: float | None
    dano_moral_pedido: float | None
    contrato_valor: float | None = Field(description="valor liberado do empréstimo")
    contrato_parcelas: int | None
    valor_parcela: float | None
    parcelas_pagas: int | None
    saldo_devedor: float | None
    canal_contratacao: str | None
    assinatura: str | None
    sub_assunto: Literal["Golpe", "Genérico"]
    destaques_subsidios: list[str]
    prova_de_proveito: list[str]
    conta_credito_titular_autor: bool | None
    liveness_presente: bool | None
    indicios: list[str]
    contradicoes: list[str]


class FichaCaso(BaseModel):
    pasta: str
    documentos: list[str]
    modelo: str
    extracao: ExtracaoCaso
    subsidios: Subsidios
    recomendacao: Recomendacao

    def texto(self) -> str:
        ex, rec = self.extracao, self.recomendacao
        vc = ex.valor_causa or 0.0
        numero = normalizar(ex.numero_processo) or ex.numero_processo or self.pasta
        comarca = ex.comarca.split("/")[0].strip() if ex.comarca else None  # "São Luís/MA" → cidade
        local = "/".join(x for x in (comarca, ex.uf) if x)
        linhas = [
            f"CASO {numero} - {(ex.autor_nome or '').upper()} ({local.upper()})",
            "",
            f"Canal: {_canal(ex)}",
            f"Subsídios: {_subsidios(self.subsidios)}",
        ]
        destaques = [d for d in ex.destaques_subsidios if _doc_do_destaque_presente(d, self.subsidios)]
        if destaques:
            linhas.append(f"Destaques: {'; '.join(destaques)}")
        linhas += [
            f"Prova de proveito: {' + '.join(ex.prova_de_proveito) or 'nenhuma nos documentos'}",
            f"Autor: {_autor(ex)}",
            f"Segmento na base: {_segmento(ex, self.subsidios, rec, vc)}",
            f"Decisão: {_decisao(rec, vc)}",
        ]
        if ex.contradicoes:
            linhas.append(f"Contradições: {'; '.join(ex.contradicoes)}")
        # o engine repete as contradições nos motivos; na ficha elas já têm linha própria
        motivos = [m for m in rec.motivos if not m.startswith("Contradições petição")]
        linhas.append(f"Motivos do engine: {' '.join(motivos)}")
        return "\n".join(linhas)


def _pct(valor: float) -> str:
    """0,6% / 82%: uma casa decimal abaixo de 10%, como o time lê os segmentos."""
    texto = f"{valor * 100:.1f}" if valor < 0.1 else f"{valor * 100:.0f}"
    return texto.replace(".", ",") + "%"


def _doc_do_destaque_presente(destaque: str, s: Subsidios) -> bool:
    """Descarta destaque rotulado com subsídio que não veio na pasta (a LLM às vezes troca o rótulo)."""
    citados = subsidios_por_arquivos([destaque.split(":", 1)[0]]).presentes()
    return not citados or any(getattr(s, flag) for flag in citados)


def _canal(ex: ExtracaoCaso) -> str:
    canal = ex.canal_contratacao or "não informado"
    return f"{canal}, assinatura {ex.assinatura.lower()}" if ex.assinatura else canal


def _subsidios(s: Subsidios) -> str:
    presentes = [rotulo for flag, (_, rotulo) in _DOCS.items() if getattr(s, flag)]
    ausentes = [rotulo for flag, (_, rotulo) in _DOCS.items() if not getattr(s, flag)]
    texto = f"{len(presentes)}/6 ({', '.join(presentes)})" if presentes else "0/6"
    return texto + (f" - sem {', sem '.join(ausentes)}" if ausentes else "")


def _autor(ex: ExtracaoCaso) -> str:
    partes = []
    indicios = ex.indicios
    if ex.autor_idade is not None:
        partes.append(f"{'idoso(a), ' if ex.autor_idade >= 60 else ''}{ex.autor_idade} anos")
        indicios = [i for i in indicios if not _IDADE.search(i)]  # a idade já abre a linha
    partes += indicios
    if ex.dano_moral_pedido:
        partes.append(f"pede {brl(ex.dano_moral_pedido)} de dano moral")
    if ex.valor_causa:
        partes.append(f"VC {brl(ex.valor_causa)}")
    return ", ".join(partes) or "sem dados na petição"


def _segmento(ex: ExtracaoCaso, s: Subsidios, rec: Recomendacao, vc: float) -> str:
    chave = [rotulo for flag, (doc, rotulo) in _DOCS.items()
             if doc in cfg.DOCS_PREDITIVOS and getattr(s, flag)]
    return (
        f"{ex.uf}, {ex.sub_assunto}, {len(chave)}/{len(cfg.DOCS_PREDITIVOS)} docs-chave "
        f"({' + '.join(chave) or 'nenhum'}): p_perda {_pct(rec.p_perda)}, custo esperado "
        f"{_pct(rec.condenacao_esperada / vc)} do VC ({brl(rec.condenacao_esperada)})"
    )


def _decisao(rec: Recomendacao, vc: float) -> str:
    if rec.decisao == cfg.DECISAO_DEFESA:
        return "DEFENDER"
    esc, dec = rec.escada, rec.decomposicao
    oferta = ""
    if esc:
        oferta = (f"abrir em {brl(esc.abertura)} ({_pct(esc.abertura / vc)} do VC), "
                  f"alvo {brl(esc.alvo)}, teto {brl(esc.teto)}")
    if dec and dec.devolucao_parcelas:
        oferta += f"; devolver parcelas ({brl(dec.devolucao_parcelas)}) + cancelar contrato"
    else:
        oferta += "; devolver parcelas pagas + cancelar contrato"
    if rec.decisao == cfg.DECISAO_INSTRUIR:
        docs = ", ".join(cfg.NOME_DOC[d] for d in rec.docs_a_solicitar)
        return f"INSTRUIR: solicitar {docs} antes; se não vier, ACORDO: {oferta}"
    return f"ACORDO: {oferta}"


def _tipo(pdf: Path, pasta: Path) -> Literal["autos", "subsidio"]:
    primeira_pasta = pdf.relative_to(pasta).parts[0].lower()
    return "autos" if primeira_pasta == "autos" or _AUTOS.search(pdf.stem.lower()) else "subsidio"


def ler_caso(pasta: Path | str) -> list[Documento]:
    """PDFs da pasta do processo (plana ou autos/ + subsidios/), autos primeiro."""
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise ErroLeitura(f"pasta não encontrada: {pasta}")
    pdfs = sorted(p for p in pasta.rglob("*") if p.suffix.lower() == ".pdf")
    if not pdfs:
        raise ErroLeitura(f"nenhum PDF em {pasta}")
    docs = [Documento(nome=p.name, tipo=_tipo(p, pasta), texto=ler_pdf(p).markdown) for p in pdfs]
    if not any(d.tipo == "autos" for d in docs):
        raise ErroLeitura(f"nenhuma petição em {pasta} (arquivo com 'autos' ou 'peticao' no nome)")
    return sorted(docs, key=lambda d: (d.tipo != "autos", d.nome))


def montar_entrada(documentos: Iterable[Documento]) -> str:
    rotulo = {"autos": "autos", "subsidio": "subsídio"}
    return "\n\n".join(f"=== {d.nome} ({rotulo[d.tipo]}) ===\n{d.texto}" for d in documentos)


def _pedir_extracao(documentos: list[Documento], client: Any, modelo: str) -> Any:
    """Resposta completa da OpenAI (com `usage`); o benchmark mede tokens e latência por aqui."""
    return client.responses.parse(
        model=modelo,
        instructions=INSTRUCOES_CASO,
        input=montar_entrada(documentos)[:LIMITE_CARACTERES],
        text_format=ExtracaoCaso,
    )


def extrair_caso(documentos: list[Documento], client: Any = None, modelo: str = MODELO_PADRAO) -> ExtracaoCaso:
    resposta = _pedir_extracao(documentos, client or _cliente(), modelo)
    if resposta.output_parsed is None:
        raise ErroResumo("o modelo não devolveu a extração do caso; tente de novo")
    return resposta.output_parsed


def para_case_features(ex: ExtracaoCaso, subsidios: Subsidios) -> CaseFeatures:
    """Entrada do engine: subsídios pelos nomes dos arquivos, o resto pela extração."""
    if not ex.valor_causa:
        raise ErroResumo("valor da causa não encontrado na petição")
    docs = DocsStatus(**{
        doc: cfg.STATUS_PRESENTE if getattr(subsidios, flag) else cfg.STATUS_AUSENTE
        for flag, (doc, _) in _DOCS.items()
    })
    try:
        return CaseFeatures(
            numero=normalizar(ex.numero_processo) or ex.numero_processo,
            uf=ex.uf or uf_do_numero(ex.numero_processo) or "",
            sub_assunto=ex.sub_assunto,
            valor_causa=ex.valor_causa,
            docs=docs,
            conta_deposito_titular_autor=ex.conta_credito_titular_autor,
            liveness_presente=ex.liveness_presente,
            parcelas_pagas=ex.parcelas_pagas,
            valor_parcela=ex.valor_parcela,
            saldo_devedor=ex.saldo_devedor,
            dano_moral_pedido=ex.dano_moral_pedido,
            contradicoes=ex.contradicoes,
        )
    except ValidationError as exc:
        raise ErroResumo(f"dados extraídos não servem ao engine: {exc.errors()[0]['msg']}") from exc


def resumir_caso(pasta: Path | str, client: Any = None, modelo: str | None = None) -> FichaCaso:
    """Pasta do processo → extração pela LLM → recomendação do engine → ficha."""
    from enteros.policy.engine import engine_padrao  # carrega os modelos só quando precisa

    documentos = ler_caso(pasta)
    modelo = modelo or os.environ.get("OPENAI_MODEL") or MODELO_PADRAO
    extracao = extrair_caso(documentos, client=client, modelo=modelo)
    subsidios = subsidios_por_arquivos(d.nome for d in documentos if d.tipo == "subsidio")
    recomendacao = engine_padrao().recomendar(para_case_features(extracao, subsidios))
    return FichaCaso(
        pasta=Path(pasta).name,
        documentos=[d.nome for d in documentos],
        modelo=modelo,
        extracao=extracao,
        subsidios=subsidios,
        recomendacao=recomendacao,
    )
