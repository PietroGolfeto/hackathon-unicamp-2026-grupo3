import { Loader, Paper, Progress, Stack, Text } from "@mantine/core";

import type { Preparacao } from "../../../../api/client";

/** Ocupa o lugar da tabela enquanto o backend lê os PDFs e roda os dois modelos. */
export function PreparandoCasos({ preparacao }: { preparacao: Preparacao | undefined }) {
  const total = preparacao?.total ?? 0;
  const prontos = preparacao?.prontos ?? 0;
  return (
    <Paper withBorder radius={12} p="xl">
      <Stack align="center" gap="sm">
        <Loader color="laranja" />
        <Text className="serif" fz="lg">Lendo os autos e os subsídios</Text>
        <Text size="sm" c="dimmed">
          {total ? `${prontos} de ${total} casos prontos` : "Preparando os casos"}
          {preparacao?.atual ? ` · ${preparacao.atual}` : ""}
        </Text>
        <Progress value={total ? (prontos / total) * 100 : 0} w={320} color="laranja" animated />
        <Text size="xs" c="dimmed">
          Na primeira vez a extração leva cerca de um minuto por caso; depois fica em cache.
        </Text>
      </Stack>
    </Paper>
  );
}
