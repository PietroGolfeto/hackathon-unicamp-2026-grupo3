import { Paper, Text } from "@mantine/core";
import type { ReactNode } from "react";

import { useContagem } from "../lib/animacao";

type Props = {
  rotulo: string;
  /** Texto já formatado. Ignorado quando `numero` e `formatar` são dados. */
  valor?: ReactNode;
  /** Valor bruto: anima do valor anterior ao novo e formata a cada quadro. */
  numero?: number | null;
  formatar?: (n: number) => string;
  detalhe?: ReactNode;
  cor?: string;
  /** Cartão em tinta com texto branco, para o número principal de um bloco. */
  destaque?: boolean;
  className?: string;
};

export function Stat({ rotulo, valor, numero, formatar, detalhe, cor, destaque, className }: Props) {
  const animado = useContagem(numero);
  const mostrado = numero != null && formatar ? formatar(animado) : valor ?? "—";
  const secundario = destaque ? "rgba(255,255,255,.64)" : "dimmed";
  const vazio = mostrado === "—";
  return (
    <Paper withBorder={!destaque} p="md" bg={destaque ? "tinta.6" : "white"} className={className} miw={0}>
      <Text size="xs" fw={500} tt="uppercase" lts=".06em" c={secundario}>{rotulo}</Text>
      <Text className={vazio ? "numero" : "serif numero"} fz={{ base: 24, sm: 28 }} lh={1.15} mt={4}
        c={vazio ? (destaque ? "rgba(255,255,255,.4)" : "gray.4") : cor ?? (destaque ? "white" : "tinta.6")}>
        {mostrado}
      </Text>
      {detalhe && <Text size="xs" mt={4} c={secundario}>{detalhe}</Text>}
    </Paper>
  );
}
