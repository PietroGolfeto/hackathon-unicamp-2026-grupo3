import { Paper, Text } from "@mantine/core";
import type { ReactNode } from "react";

export function Stat({ rotulo, valor, detalhe, cor }: { rotulo: string; valor: ReactNode; detalhe?: ReactNode; cor?: string }) {
  return (
    <Paper withBorder p="sm" radius="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>{rotulo}</Text>
      <Text size="xl" fw={700} c={cor}>{valor}</Text>
      {detalhe && <Text size="xs" c="dimmed">{detalhe}</Text>}
    </Paper>
  );
}
