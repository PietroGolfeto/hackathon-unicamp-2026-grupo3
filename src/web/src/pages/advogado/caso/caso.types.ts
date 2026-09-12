import type { ProcessoDetalhe } from "../../../api/client";

/** Nomes de arquivo que o advogado já abriu; vira prova de leitura ao registrar a decisão. */
export type DocumentosAbertos = Set<string>;

export type ProcessoProps = { p: ProcessoDetalhe };
