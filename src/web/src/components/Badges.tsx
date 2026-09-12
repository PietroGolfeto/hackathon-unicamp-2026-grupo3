import { Badge, Tooltip } from "@mantine/core";

import type { Sinal } from "../api/client";
import { ROTULO_STATUS, ROTULO_TIPO } from "../lib/format";

export function TipoBadge({ tipo, size = "md" }: { tipo: string | null | undefined; size?: string }) {
  if (!tipo) return <Badge color="gray" variant="light" size={size}>sem recomendação</Badge>;
  return (
    <Badge color={tipo === "acordo" ? "teal" : "indigo"} size={size} variant="filled">
      {ROTULO_TIPO[tipo] ?? tipo}
    </Badge>
  );
}

export function StatusBadge({ status }: { status: string | null | undefined }) {
  if (!status) return null;
  const cor: Record<string, string> = {
    pendente: "gray", decidido: "blue", encerrado: "green",
    registrada: "blue", pendente_aprovacao: "orange", aprovada: "green", rejeitada: "red",
  };
  return <Badge color={cor[status] ?? "gray"} variant="light">{ROTULO_STATUS[status] ?? status}</Badge>;
}

/** Marca dados que vieram do stub (sem P1/P3 plugados). Some quando `origem` for "modelo" ou "llm". */
export function OrigemBadge({ origem, rotulo }: { origem: string | null | undefined; rotulo?: string }) {
  if (!origem || origem === "modelo" || origem === "llm") return null;
  return (
    <Tooltip label="Valor de demonstração: modelo ou extração ainda não plugados">
      <Badge color="yellow" variant="outline" size="xs">{rotulo ?? "stub"}</Badge>
    </Tooltip>
  );
}

export function SinalChip({ sinal }: { sinal: Sinal }) {
  const cor = sinal.severidade === "alta" ? "red" : sinal.severidade === "media" ? "orange" : "gray";
  return (
    <Tooltip label={`${sinal.descricao}${sinal.fonte ? ` (${sinal.fonte})` : ""}`}>
      <Badge color={cor} variant="light" size="sm">{sinal.codigo.replaceAll("_", " ").toLowerCase()}</Badge>
    </Tooltip>
  );
}
