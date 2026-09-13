import { Group, Text } from "@mantine/core";
import { Link } from "react-router";

/** Marca do produto: monograma "U" (Unicamp) em laranja sobre tinta, "Acordos" em serifa e "Banco Unicamp" em caixa alta. */
export function Marca({ invertida = false, tamanho = "sm", to = "/" }: { invertida?: boolean; tamanho?: "sm" | "lg"; to?: string | null }) {
  const lado = tamanho === "lg" ? 44 : 30;
  const conteudo = (
    <Group gap={tamanho === "lg" ? 12 : 10} wrap="nowrap">
      <span
        style={{
          width: lado, height: lado, borderRadius: Math.round(lado * 0.24), flex: "none",
          background: invertida ? "#ffffff" : "#171717", color: invertida ? "#171717" : "#ffae35",
          display: "grid", placeItems: "center",
        }}
      >
        <span className="serif" style={{ fontSize: Math.round(lado * 0.6), fontWeight: 600, lineHeight: 1 }}>U</span>
      </span>
      <span style={{ display: "grid", lineHeight: 1.05 }}>
        <Text component="span" className="serif" fz={tamanho === "lg" ? 24 : 18} c={invertida ? "white" : "tinta.6"}>
          Acordos
        </Text>
        <Text component="span" fz={tamanho === "lg" ? 11 : 10} fw={500} tt="uppercase" lts=".1em"
          c={invertida ? "rgba(255,255,255,.64)" : "dimmed"}>
          Banco Unicamp
        </Text>
      </span>
    </Group>
  );
  if (!to) return conteudo;
  return <Link to={to} style={{ textDecoration: "none", color: "inherit" }} aria-label="Início">{conteudo}</Link>;
}
