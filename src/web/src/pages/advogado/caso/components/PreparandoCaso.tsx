import { Card, Group, Loader, Stack, Text } from "@mantine/core";

/**
 * Ocupa o lugar da recomendação e do resumo enquanto a IA ainda não leu os autos deste caso.
 *
 * O resto da tela continua utilizável: cabeçalho, documentos e subsídios já estão abaixo. Abrir o
 * caso também o coloca na frente da fila de leitura no servidor.
 */
export function PreparandoCaso() {
  return (
    <Card>
      <Group gap="md" wrap="nowrap" align="flex-start">
        <Loader color="laranja" size="sm" mt={4} />
        <Stack gap={2}>
          <Text fw={600}>Lendo os autos e os subsídios deste caso</Text>
          <Text size="sm" c="dimmed">
            O resumo e a recomendação da política aparecem aqui assim que a leitura terminar.
            Os documentos já estão abaixo e podem ser abertos agora.
          </Text>
        </Stack>
      </Group>
    </Card>
  );
}
