/** Cliente HTTP da API (mesma origem, cookie de sessão). Tipos espelham src/api/app/schemas.py. */

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function detalhe(data: unknown, status: number): string {
  if (data && typeof data === "object" && "detail" in data) {
    const d = (data as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((e) => (e as { msg?: string }).msg ?? JSON.stringify(e)).join("; ");
  }
  return status === 401 ? "Faça login para continuar." : `Erro ${status}`;
}

async function req<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, ...resto } = init;
  const headers: Record<string, string> = { ...(resto.headers as Record<string, string> | undefined) };
  let body: BodyInit | undefined = resto.body ?? undefined;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }
  const r = await fetch(path, { ...resto, headers, body, credentials: "same-origin" });
  if (r.status === 204) return undefined as T;
  const texto = await r.text();
  let data: unknown = null;
  try {
    data = texto ? JSON.parse(texto) : null;
  } catch {
    data = texto;
  }
  if (!r.ok) throw new ApiError(r.status, detalhe(data, r.status));
  return data as T;
}

// ---------------------------------------------------------------- tipos

export type Papel = "advogado" | "gestor";
export type TipoDecisao = "acordo" | "defesa";
/** A recomendação tem uma saída a mais que a decisão: instruir = pedir subsídios antes de acordar. */
export type TipoRecomendacao = TipoDecisao | "instruir";

export interface Usuario {
  id: number; nome: string; email: string; papel: Papel;
  escritorio_id: number | null; escritorio_nome: string | null;
}

export interface RecomendacaoResumo {
  id: number; politica_id: number; tipo: TipoRecomendacao;
  valor_sugerido: number | null; valor_min: number | null; valor_max: number | null; created_at: string;
}

export interface ProcessoResumo {
  id: number; numero: string; uf: string; sub_assunto: string | null; valor_causa: number;
  autor: string | null; status: string; origem: string; escritorio_id: number; escritorio: string;
  n_subsidios: number; sinais: string[]; scores_origem: string | null; extracao_origem: string | null;
  recomendacao: RecomendacaoResumo | null; decisao_tipo: string | null; decisao_status: string | null;
  reservado_ate: string | null;
  /** A leitura dos documentos desse caso ainda está na fila da preparação. */
  extracao_pendente: boolean;
}

export type Relevancia = "alta" | "media" | "baixa";
export interface Documento {
  tipo: string; arquivo: string; url: string;
  comentario?: string | null; relevancia?: Relevancia | null;  // da extração; null sem P3
}
export interface Sinal { codigo: string; descricao: string; severidade: "baixa" | "media" | "alta"; fonte?: string | null }
export interface Pessoa { nome?: string | null; cpf_mascarado?: string | null; idade?: number | null; email?: string | null; telefone?: string | null; oab?: string | null }

export interface DadosExtraidos {
  origem: string; autor: Pessoa; advogado_autor: Pessoa; comarca?: string | null; uf?: string | null;
  valor_causa?: number | null; pedidos: string[]; sinais_alerta: Sinal[]; resumo_fatos: string; confianca: number;
  contrato?: { canal: string; assinatura: string; credito_conta_terceiro?: boolean | null };
}

export interface Analise {
  origem: string; pontos_fortes_banco: string[]; pontos_fracos_banco: string[];
  tese_provavel_autor: string; riscos: string[]; texto: string;
  contradicoes?: string[];  // petição × subsídios; ausente em linhas gravadas antes do campo
}

export interface Contribuicao { feature: string; valor: unknown; contribuicao: number; descricao?: string | null }
export interface Scores {
  modelo_versao: string; origem: "modelo" | "stub"; p_exito_defesa: number;
  condenacao_p20: number; condenacao_p50: number; condenacao_p80: number; contribuicoes: Contribuicao[];
}

export interface Decisao {
  id: number; processo_id: number; recomendacao_id: number; usuario_id: number; usuario_nome: string | null;
  tipo: TipoDecisao; valor_proposto: number | null; justificativa: string | null; aderente: boolean;
  tipo_desvio: string; status: string; tempo_analise_s: number | null; documentos_abertos: string[];
  resultado: string | null; valor_final: number | null; resultado_em: string | null; observacao: string | null;
  comentario_aprovacao: string | null; created_at: string;
}

export interface ProcessoDetalhe {
  id: number; numero: string; uf: string; sub_assunto: string | null; valor_causa: number; status: string;
  origem: string; escritorio_id: number; escritorio: string; subsidios: Record<string, boolean>;
  documentos: Documento[]; dados_extraidos: DadosExtraidos | null; analise: Analise | null; sinais: Sinal[];
  scores: Scores | null; decisao_atual: Decisao | null; reservado_ate: string | null;
  /** Enquanto for true, `dados_extraidos`, `analise` e a recomendação ainda vão mudar. */
  extracao_pendente: boolean;
  created_at: string;
}

export interface Recomendacao {
  id: number; processo_id: number; politica_id: number; politica_versao: number; politica_nome: string;
  tipo: TipoRecomendacao; valor_sugerido: number | null; valor_min: number | null; valor_max: number | null;
  custo_esperado_defesa: number; custo_esperado_acordo: number; economia_esperada: number; regra: string;
  sinais_acionados: string[]; docs_a_solicitar: string[]; motivos: string[]; scores_snapshot: Scores;
  exige_aprovacao_valor_causa: boolean;
  created_at: string;
}

/** Progresso da fase 2 (leitura dos PDFs). A fase 1 já terminou quando esta resposta chega. */
export interface Preparacao {
  status: "ocioso" | "rodando" | "pronto" | "erro";
  total: number; prontos: number; atual: string | null; erro: string | null; atualizado_em: string | null;
}

export interface DecisaoIn {
  tipo: TipoDecisao; valor_proposto?: number | null; justificativa?: string | null;
  tempo_analise_s?: number | null; documentos_abertos?: string[];
}

export interface Minutas { proposta_acordo: string; roteiro_defesa: string; mensagem_contato: string; origem: string }

export interface DecisaoRegistrada {
  decisao: Decisao; recomendacao: Recomendacao; minutas: Minutas | null; contato_adverso: Pessoa | null; mensagem: string;
}

export type Resultado = "aceito" | "recusado" | "contraproposta_aceita" | "sem_resposta" | "seguiu_defesa";
export interface ResultadoIn { resultado: Resultado; valor_final?: number | null; observacao?: string | null }

export interface PoliticaParams {
  custas_fixas_defesa: number; honorarios_defesa_pct: number; sucumbencia_pct: number;
  custo_operacional_acordo: number; taxa_aceite_esperada: number; fator_oferta: number;
  piso_oferta_pct_causa: number; teto_oferta_pct_causa: number; margem_banda_pct: number; arredondamento: number;
  limiar_defesa_forte: number; limiar_acordo_forte: number; sinais_forcam_acordo: string[];
  valor_causa_max_sem_aprovacao: number | null; incluir_extincao_no_backtest: boolean;
}

export interface Grupo { [k: string]: unknown; n: number; pct_acordo: number; politica: number; defender_tudo: number; acordar_tudo: number; economia_vs_defender: number }

export interface Backtest {
  n: number; totais: { politica: number; defender_tudo: number; acordar_tudo: number };
  economia_vs_defender: { valor: number; pct: number }; economia_vs_acordar: { valor: number; pct: number };
  pct_acordo: number; n_acordo: number; oferta_media: number | null; custo_medio_por_processo: number;
  por_regra: Record<string, number>; por_uf: Grupo[]; por_n_docs: Grupo[];
  hipoteses: { taxa_aceite_esperada: number }; incluir_extincao: boolean; scores_origem: string | null; tempo_ms: number;
}

export interface Politica {
  id: number; versao: number; nome: string; params: PoliticaParams; ativa: boolean; criado_por: number | null;
  created_at: string; publicada_em: string | null; resumo_backtest: Backtest | null;
}

export interface LinhaAderencia { [k: string]: unknown; semana?: string; total: number; aderentes: number; pct_aderente: number; tempo_medio_s: number | null; pct_acordo: number }
export interface Justificativa {
  decisao_id: number; created_at: string; numero: string; processo_id: number; advogado: string; escritorio: string;
  tipo: string; rec_tipo: string; valor_proposto: number | null; valor_sugerido: number | null; tipo_desvio: string;
  status: string; justificativa: string | null; parecer_ia: ParecerIA | null;
}
export interface ParecerIA {
  decisao_id: number; classificacao: "fundamentada" | "generica" | "contradiz_evidencias";
  resumo: string; pontos: string[]; confianca: number; modelo: string; gerado_em: string;
}
export interface Aderencia {
  total: number; aderentes: number; pct_aderente: number | null; pct_desvio_tipo: number | null;
  pct_desvio_valor: number | null; tempo_medio_s: number | null; pendentes_aprovacao: number;
  pct_sem_ver_recomendacao: number | null; pct_sem_abrir_documento: number | null; pct_acordo: number | null;
  por_escritorio: LinhaAderencia[]; por_advogado: LinhaAderencia[]; por_semana: LinhaAderencia[]; justificativas: Justificativa[];
}

export interface LinhaEfetividade { [k: string]: unknown; n: number; taxa_aceite: number; economia_realizada: number; valor_final_medio: number | null }
export interface Efetividade {
  n_decisoes: number; n_acordos: number; n_defesas: number; n_com_resultado: number;
  n_sem_resultado: number; cobertura_resultados: number | null; taxa_aceite_preliminar: boolean;
  taxa_aceite_real: number | null; taxa_aceite_esperada: number | null; desconto_real: number | null;
  ticket_medio_final: number | null; economia_esperada: number; economia_realizada: number;
  por_resultado: Record<string, number>; por_uf: LinhaEfetividade[]; por_escritorio: LinhaEfetividade[]; por_semana: LinhaEfetividade[];
  backtest_potencial: {
    n_casos: number; defender_tudo: number; acordar_tudo: number; politica: number;
    economia_vs_defender: number; economia_pct: number; pct_acordo: number;
    politica_versao: string; modelo_versao: string;
  } | null;
  politica: { id: number; versao: number; nome: string; publicada_em: string | null; resumo_backtest: Backtest | null } | null;
  modelo: { versao: string; treinado_em: string; n_treino: number; metricas: Record<string, number>; importancias: Record<string, number> };
}

export interface Aprovacao {
  decisao: Decisao; processo_id: number; numero: string; valor_causa: number; escritorio: string;
  autor: string | null; recomendacao: RecomendacaoResumo;
}

// ---------------------------------------------------------------- chamadas

export const api = {
  login: (email: string, senha: string) => req<Usuario>("/api/auth/login", { method: "POST", json: { email, senha } }),
  me: async (): Promise<Usuario | null> => {
    try {
      return await req<Usuario>("/api/auth/me");
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return null;
      throw e;
    }
  },
  logout: () => req<void>("/api/auth/logout", { method: "POST" }),

  prepararCasos: () => req<Preparacao>("/api/preparacao", { method: "POST" }),
  preparacao: () => req<Preparacao>("/api/preparacao"),

  processos: (busca?: string) =>
    req<ProcessoResumo[]>(`/api/processos${busca ? `?busca=${encodeURIComponent(busca)}` : ""}`),
  processo: (id: number) => req<ProcessoDetalhe>(`/api/processos/${id}`),
  recomendacao: (id: number) => req<Recomendacao>(`/api/processos/${id}/recomendacao`),
  decidir: (id: number, dados: DecisaoIn) =>
    req<DecisaoRegistrada>(`/api/processos/${id}/decisoes`, { method: "POST", json: dados }),
  resultado: (decisaoId: number, dados: ResultadoIn) =>
    req<Decisao>(`/api/decisoes/${decisaoId}/resultado`, { method: "POST", json: dados }),
  evento: (processo_id: number, tipo: string, payload: Record<string, unknown> = {}) =>
    req<void>("/api/eventos", { method: "POST", json: { processo_id, tipo, payload } }).catch(() => undefined),
  resumoTxt: async (id: number) => {
    const r = await fetch(`/api/processos/${id}/resumo.txt`, { credentials: "same-origin" });
    if (!r.ok) throw new ApiError(r.status, "Não consegui gerar o resumo.");
    return r.text();
  },

  politicaAtiva: () => req<Politica>("/api/politicas/ativa"),
  politicas: () => req<Politica[]>("/api/politicas"),
  criarPolitica: (nome: string, params: PoliticaParams) =>
    req<Politica>("/api/politicas", { method: "POST", json: { nome, params } }),
  simular: (params: PoliticaParams) => req<Backtest>("/api/politicas/simular", { method: "POST", json: { params } }),
  ativarPolitica: (id: number) => req<Politica>(`/api/politicas/${id}/ativar`, { method: "POST" }),

  aderencia: (escritorioId?: number) =>
    req<Aderencia>(`/api/dashboard/aderencia${escritorioId ? `?escritorio_id=${escritorioId}` : ""}`),
  efetividade: () => req<Efetividade>("/api/dashboard/efetividade"),
  gerarParecer: (decisaoId: number) =>
    req<ParecerIA>(`/api/dashboard/desvios/${decisaoId}/parecer`, { method: "POST" }),

  aprovacoes: () => req<Aprovacao[]>("/api/aprovacoes"),
  aprovar: (decisaoId: number, acao: "aprovar" | "rejeitar", comentario?: string) =>
    req<Decisao>(`/api/aprovacoes/${decisaoId}`, { method: "POST", json: { acao, comentario: comentario || null } }),
};
