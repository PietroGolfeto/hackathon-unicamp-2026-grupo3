from pathlib import Path

from extractor import parsing


def _texto(pasta: Path, nome: str) -> str:
    return next(pasta.rglob(nome)).read_text(encoding="utf-8")


def test_classificacao_por_nome_e_conteudo():
    assert parsing.classificar("01_Autos_Processo_x.pdf", "autos", "") == "peticao"
    assert parsing.classificar("05_Dossie_Veritas.pdf", "subsidios", "") == "dossie"
    assert parsing.classificar("doc.pdf", "subsidios", "CÉDULA DE CRÉDITO BANCÁRIO nº 1") == "contrato"
    assert parsing.classificar("doc.pdf", "autos", "EXCELENTÍSSIMO SENHOR") == "peticao"
    assert parsing.classificar("doc.pdf", "subsidios", "qualquer coisa") == "outro"


def test_fatos_da_peticao(pasta_exemplo: Path):
    f = parsing.fatos_peticao(_texto(pasta_exemplo, "peticao_inicial.txt"))
    assert f["cnj"] == "0001234-56.2024.8.13.0001"
    assert (f["comarca"], f["uf"], f["vara"]) == ("Belo Horizonte", "MG", "2ª Vara Cível")
    assert f["autor_nome"] == "Ana Lúcia Ferreira Mota" and f["autor_cpf_mascarado"] == "***.***.987-00"
    assert f["autor_email"] == "ana.mota@email.com.br"
    assert f["autor_nascimento"] == "1955-01-10" and f["autor_idade"] == 69  # na data da petição
    assert f["advogado_nome"] == "Dra. Paula Reis Andrade" and f["advogado_oab"] == "MG 45.678"
    assert f["advogado_email"] == "paula.andrade@adv.com.br"
    assert f["valor_causa"] == 18000.0 and f["dano_moral_pedido"] == 12000.0
    assert f["contrato_valor_alegado"] == 4000.0 and f["contrato_parcelas_alegadas"] == 60
    assert f["valor_parcela_alegado"] == 110.0 and f["contrato_data_alegada"] == "03/03/2023"
    assert f["boletim_ocorrencia"] == "2024.001122" and f["reclamacao_bacen_rdr"] == "555555-1"
    assert f["conta_deposito_citada"].startswith("Caixa Econômica Federal ag 1111 cc 22222-3")
    assert {"autor_idoso", "boletim_ocorrencia", "reclamacao_bacen", "nega_conta_deposito", "canal_app"} <= set(f["indicios"])


def test_trechos_da_peticao_mantem_fatos_e_pedidos_e_cortam_direito(pasta_exemplo: Path):
    trechos = "\n".join(parsing.trechos_peticao(_texto(pasta_exemplo, "peticao_inicial.txt"), 7000))
    assert "jamais contratou" in trechos and "Dá-se à causa o valor de R$ 18.000,00" in trechos
    assert "Súmula 297" not in trechos and "responsabilidade objetiva" not in trechos
    assert "Da relação de consumo; Dos danos morais" in trechos  # só títulos do direito
    assert "Página 1" not in trechos  # rodapé removido
    assert "paula.andrade@adv.com.br" in trechos and "data de nascimento 10/01/1955" in trechos


def test_fatos_dos_subsidios(pasta_exemplo: Path):
    dem = parsing.fatos_subsidio("demonstrativo_divida", _texto(pasta_exemplo, "demonstrativo_evolucao_divida.txt"))
    assert (dem["parcelas_pagas"], dem["parcelas_em_aberto"], dem["parcelas_total"]) == (3, 2, 5)
    assert dem["saldo_devedor"] == 3100.0
    comp = parsing.fatos_subsidio("comprovante_credito", _texto(pasta_exemplo, "comprovante_credito.txt"))
    assert comp["campos"]["Canal de contratação"].startswith("Digital - Aplicativo Mobile")
    assert comp["campos"]["Instituição depositária"].startswith("Caixa Econômica Federal")
    assert "canal_app" in comp["indicios"]
    laudo = parsing.fatos_subsidio("laudo_referenciado", _texto(pasta_exemplo, "laudo_referenciado.txt"))
    assert {"liveness_nao_localizado", "contestacao_judicial", "assinatura_eletronica"} <= set(laudo["indicios"])


def test_trechos_dos_subsidios_sem_repetir_campos_nem_boilerplate(pasta_exemplo: Path):
    texto = _texto(pasta_exemplo, "comprovante_credito.txt")
    fatos = parsing.fatos_subsidio("comprovante_credito", texto)
    trechos = "\n".join(parsing.trechos_subsidio("comprovante_credito", texto, fatos, 1600))
    assert "Resolução CMN" not in trechos and "Documento gerado" not in trechos
    assert "Nº do contrato" not in trechos  # já está em campos
    assert "conta de sua titularidade junto à Caixa" in trechos  # parágrafo inteiro, não fragmento
    dem = _texto(pasta_exemplo, "demonstrativo_evolucao_divida.txt")
    fd = parsing.fatos_subsidio("demonstrativo_divida", dem)
    td = "\n".join(parsing.trechos_subsidio("demonstrativo_divida", dem, fd, 1200))
    assert "3 pagas, 2 em aberto" in td and "03/05/2023" not in td  # linhas da tabela saem


def test_brief_respeita_orcamento_e_lista_ausentes(pasta_exemplo: Path):
    docs = []
    for arq in sorted(pasta_exemplo.rglob("*.txt")):
        docs.append(parsing.parsear(arq.name, arq.parent.name, arq.read_text(encoding="utf-8"), paginas=None, leitor="txt"))
    brief = parsing.montar_brief("0001234-56.2024.8.13.0001", "MG", docs, ["comprovante_credito"], ["contrato", "extrato"])
    assert brief.startswith("PROCESSO 0001234-56.2024.8.13.0001 · UF MG")
    assert "ausentes: contrato, extrato" in brief and "## [AUTOS] peticao_inicial.txt" in brief
    assert "_linhas_usadas" not in brief and len(brief) <= parsing.LIMITE_BRIEF


def test_brief_gigante_e_cortado():
    linha = "Valor da parcela R$ 100,00 em 10/10/2020 TED conta 123\n"
    doc = parsing.parsear("extrato.txt", "subsidios", linha * 3000, paginas=None, leitor="txt")
    peticao = parsing.parsear("peticao.txt", "autos", ("I – DOS FATOS\n" + "A autora afirma que nunca contratou o empréstimo. " * 800
                                                     + "\nIV – DOS PEDIDOS\nDá-se à causa o valor de R$ 1.000,00."),
                              paginas=None, leitor="txt")
    brief = parsing.montar_brief("x", None, [peticao, doc], [], [])
    assert len(brief) <= parsing.LIMITE_BRIEF + 200
    assert peticao.chars_brief >= parsing.PISO_PETICAO * 0.8


def test_movimentos_do_extrato_e_pista_de_uso_dos_valores():
    extrato = ("Cliente:  MARIA\n\n Data           Histórico                 Documento              Valor (R$)      Saldo (R$)\n\n"
               " 12/05/2022     CRÉDITO - EMPRÉSTIMO      Contr. 1               +5.000,00       5.000,00\n\n"
               " 13/05/2022     TED ENVIADA - CTA TITULARIDADE     Bradesco / Ag 1 CC 2      -3.000,00       2.000,00\n\n"
               " 17/05/2022     SAQUE ATM                 NSU 1                    -485,00         1.515,00\n")
    f = parsing.fatos_subsidio("extrato", extrato)
    assert len(f["movimentos"]) == 3 and f["movimentos"][1].startswith("13/05/2022 TED ENVIADA")
    pet = parsing.parsear("peticao.txt", "autos", "I – DOS FATOS\nA autora jamais utilizou os valores creditados.\nIV – DOS PEDIDOS\n",
                          paginas=None, leitor="txt")
    ext = parsing.parsear("extrato.txt", "subsidios", extrato, paginas=None, leitor="txt")
    pistas = parsing.pistas_cruzadas([pet, ext])
    assert any(p.startswith("Contradição candidata") and "2 saída(s)" in p for p in pistas)


def test_liveness_nao_localizado_atravessa_quebra_de_linha_do_pdftotext():
    # trecho literal do laudo do caso 02 como o `pdftotext -layout` o entrega: a frase quebra antes de "vídeo"
    laudo = ("    preservados nos sistemas do Banco UFMG S.A. No entanto, não foi localizado nos arquivos digitais o\n"
             "    vídeo de liveness (biometria facial) tradicionalmente capturado ao final do fluxo, fato reportado\n"
             "    internamente para apuração pela área de Segurança da Informação. Não foi providenciada, até o\n"
             "    momento, verificação grafotécnica complementar por empresa terceira.\n")
    assert "liveness_nao_localizado" in parsing.fatos_subsidio("laudo_referenciado", laudo)["indicios"]
    # não atravessa ponto final nem linha em branco (outro parágrafo ou outro item de lista)
    padrao = parsing.INDICIOS["liveness_nao_localizado"]
    assert not padrao.search("Não foi localizado o contrato físico. O vídeo de liveness foi capturado com sucesso.")
    assert not padrao.search("    • Vídeo de liveness: capturado com sucesso\n\n    • Documento de identidade: não foi localizado\n")
