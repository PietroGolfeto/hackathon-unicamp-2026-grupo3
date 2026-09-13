import { Badge, Tooltip } from "@mantine/core";

import type { Sinal } from "../api/client";
import { ROTULO_STATUS, ROTULO_TIPO } from "../lib/format";

/** Acordo é laranja (o acento da marca), defesa é tinta. Sem recomendação fica neutro. */
export function TipoBadge({ tipo, size = "md" }: { tipo: string | null | undefined; size?: string }) {
  if (!tipo) return <Badge color="gray" variant="light" size={size}>sem recomendação</Badge>;
  return (
    <Badge
      color={tipo === "defesa" ? "tinta" : "laranja"}
      size={size}
      variant="filled"
    >
      {ROTULO_TIPO[tipo] ?? tipo}
    </Badge>
  );
}

export function StatusBadge({ status, size }: { status: string | null | undefined; size?: string }) {
  if (!status) return null;
  const cor: Record<string, string> = {
    pendente: "gray", decidido: "tinta", encerrado: "verde",
    registrada: "tinta", pendente_aprovacao: "laranja", aprovada: "verde", rejeitada: "vermelho",
  };
  const variante = status === "pendente" ? "outline" : "light";
  return <Badge color={cor[status] ?? "gray"} variant={variante} size={size}>{ROTULO_STATUS[status] ?? status}</Badge>;
}

export function AderenciaBadge({ aderente, tipoDesvio, size }: { aderente: boolean; tipoDesvio?: string | null; size?: string }) {
  if (aderente) return <Badge color="verde" variant="light" size={size}>aderente à política</Badge>;
  return <Badge color="laranja" variant="light" size={size}>{tipoDesvio ? `desvio de ${tipoDesvio}` : "desvio"}</Badge>;
}

/** Marca dados que vieram do stub (sem P1/P3 plugados). Some quando `origem` for "modelo" ou "llm[:modelo]". */
export function OrigemBadge({ origem, rotulo }: { origem: string | null | undefined; rotulo?: string }) {
  if (!origem || origem === "modelo" || origem.startsWith("llm")) return null;
  return (
    <Tooltip label="Valor de demonstração: modelo ou extração ainda não plugados">
      <Badge color="laranja" variant="outline" size="xs">{rotulo ?? "stub"}</Badge>
    </Tooltip>
  );
}

export function SinalChip({ sinal }: { sinal: Sinal }) {
  const cor = sinal.severidade === "alta" ? "vermelho" : sinal.severidade === "media" ? "laranja" : "gray";
  return (
    <Tooltip label={`${sinal.descricao}${sinal.fonte ? ` (${sinal.fonte})` : ""}`}>
      <Badge color={cor} variant="light" size="sm">{sinal.codigo.replaceAll("_", " ").toLowerCase()}</Badge>
    </Tooltip>
  );
}
