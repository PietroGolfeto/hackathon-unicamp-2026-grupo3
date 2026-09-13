export const NOMES_SUBSIDIOS: Record<string, string> = {
  contrato: "Contrato", extrato: "Extrato", comprovante_credito: "Comprovante de crédito", dossie: "Dossiê",
  demonstrativo_divida: "Demonstrativo da dívida", laudo_referenciado: "Laudo referenciado",
};

export const GRUPOS_DOCUMENTOS = [["autos", "Autos"], ["subsidios", "Subsídios do banco"]] as const;

/** Cor do ponto de relevância do comentário da IA em cada documento. */
export const COR_RELEVANCIA: Record<string, string> = {
  alta: "vermelho", media: "laranja", baixa: "gray",
};
