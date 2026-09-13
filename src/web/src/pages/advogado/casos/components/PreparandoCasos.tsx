import { Group, Loader, Paper, Progress, Text } from "@mantine/core";

import type { Preparacao } from "../../../../api/client";

/**
 * Faixa acima da tabela enquanto a leitura dos PDFs ainda roda no servidor.
 *
 * Não substitui a lista: os casos já estão ali com número, valor, subsídios e documentos. Só o
 * que depende da leitura (resumo e recomendação) aparece depois, caso a caso.
 */
export function PreparandoCasos({ preparacao }: { preparacao: Preparacao | undefined }) {
  const total = preparacao?.total ?? 0;
  const prontos = preparacao?.prontos ?? 0;
  return (
    <Paper withBorder radius={12} px="md" py="sm">
      <Group gap="sm" wrap="nowrap" align="center">
        <Loader color="laranja" size="sm" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text size="sm" fw={500}>
            Lendo os autos e os subsídios em segundo plano
            {total ? ` · ${prontos} de ${total} casos prontos` : ""}
          </Text>
          <Text size="xs" c="dimmed">
            Pode abrir qualquer caso agora: o resumo e a recomendação chegam quando a leitura dele terminar.
          </Text>
        </div>
        <Progress value={total ? (prontos / total) * 100 : 0} w={{ base: 90, sm: 180 }} color="laranja" animated />
      </Group>
    </Paper>
  );
}
