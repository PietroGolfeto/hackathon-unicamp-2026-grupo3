/** Único lugar do front que formata dinheiro, percentual, data e duração (pt-BR). */

const brlFmt = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const brlCentavos = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

export function brl(valor: number | null | undefined, centavos = false): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "—";
  return (centavos ? brlCentavos : brlFmt).format(valor);
}

export function brlCompacto(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  const abs = Math.abs(valor);
  if (abs >= 1e9) return `R$ ${(valor / 1e9).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} bi`;
  if (abs >= 1e6) return `R$ ${(valor / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
  if (abs >= 1e3) return `R$ ${(valor / 1e3).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mil`;
  return brl(valor);
}

export function pct(valor: number | null | undefined, casas = 0): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "—";
  return `${(valor * 100).toLocaleString("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: casas })}%`;
}

export function num(valor: number | null | undefined): string {
  return valor === null || valor === undefined ? "—" : inteiro.format(valor);
}

export function data(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

export function dataHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function duracao(segundos: number | null | undefined): string {
  if (segundos === null || segundos === undefined) return "—";
  const m = Math.floor(segundos / 60);
  const s = Math.floor(segundos % 60);
  return m ? `${m}min ${s.toString().padStart(2, "0")}s` : `${s}s`;
}

export const ROTULO_TIPO: Record<string, string> = {
  acordo: "Propor acordo", defesa: "Defender",
};
export const ROTULO_STATUS: Record<string, string> = {
  pendente: "Pendente", decidido: "Decidido", encerrado: "Encerrado",
  registrada: "Registrada", pendente_aprovacao: "Aguardando aprovação", aprovada: "Aprovada", rejeitada: "Rejeitada",
};
export const ROTULO_RESULTADO: Record<string, string> = {
  aceito: "Acordo aceito", recusado: "Acordo recusado", contraproposta_aceita: "Contraproposta aceita",
  sem_resposta: "Sem resposta", seguiu_defesa: "Seguiu para defesa",
};
export const ROTULO_REGRA: Record<string, string> = {
  defesa_forte: "êxito acima do limiar de defesa forte", acordo_forte: "êxito abaixo do limiar de acordo forte",
  custo: "comparação de custo esperado", sinal: "sinal nos autos força acordo",
};
