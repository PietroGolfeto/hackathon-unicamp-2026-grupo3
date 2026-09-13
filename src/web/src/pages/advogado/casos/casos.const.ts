import type { Situacao } from "./casos.types";

export const OPCOES_SITUACAO: { value: Situacao; label: string }[] = [
  { value: "todos", label: "Todos" },
  { value: "pendente", label: "Pendentes" },
  { value: "decidido", label: "Decididos" },
];

/** Processo, valor da causa, subsídios, recomendação e situação. Autor e escritório são condicionais. */
export const COLUNAS_BASE = 5;

/** Contrato, extrato, comprovante de crédito, dossiê, demonstrativo e laudo. */
export const TOTAL_SUBSIDIOS = 6;

/** Larguras da tabela de casos: a soma das visíveis é a largura mínima; sobra é dividida na proporção. */
export const LARGURA_COLUNA = {
  processo: 230, autor: 170, valor: 150, subsidios: 180, recomendacao: 190, situacao: 150, escritorio: 170,
} as const;
