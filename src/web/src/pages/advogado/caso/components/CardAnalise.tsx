import { Card, Group, List, SimpleGrid, Text } from "@mantine/core";

import { OrigemBadge } from "../../../../components/Badges";
import type { ProcessoProps } from "../caso.types";

export function CardAnalise({ p }: ProcessoProps) {
  const a = p.analise;
  const d = p.dados_extraidos;
  if (!a && !d) return null;
  return (
    <Card>
      <Group justify="space-between">
        <Text fw={500}>Análise do caso</Text>
        <OrigemBadge origem={a?.origem} rotulo="análise stub" />
      </Group>
      {d?.resumo_fatos && <Text size="sm" mt="xs" c="dimmed" lineClamp={4}>{d.resumo_fatos}</Text>}
      {a?.texto && <Text size="sm" mt="xs">{a.texto}</Text>}
      <SimpleGrid cols={{ base: 1, sm: 2 }} mt="sm" spacing="md">
        {a && a.pontos_fortes_banco.length > 0 && (
          <div><Text size="xs" fw={500} c="verde.7" tt="uppercase" lts=".06em">Pontos fortes do banco</Text>
            <List size="sm" mt={4}>{a.pontos_fortes_banco.map((x, i) => <List.Item key={i}>{x}</List.Item>)}</List></div>
        )}
        {a && a.pontos_fracos_banco.length > 0 && (
          <div><Text size="xs" fw={500} c="vermelho.6" tt="uppercase" lts=".06em">Pontos fracos do banco</Text>
            <List size="sm" mt={4}>{a.pontos_fracos_banco.map((x, i) => <List.Item key={i}>{x}</List.Item>)}</List></div>
        )}
      </SimpleGrid>
      {d && d.pedidos.length > 0 && <Text size="xs" mt="sm" c="dimmed">Pedidos: {d.pedidos.join("; ")}</Text>}
    </Card>
  );
}
