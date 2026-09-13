import { Card, Group, List, Text } from "@mantine/core";

import { OrigemBadge } from "../../../../components/Badges";
import type { ProcessoProps } from "../caso.types";

/** O que o advogado lê em 30 segundos: resumo do caso, pontos fracos do banco e, se houver, contradições da petição. */
export function CardAnalise({ p }: ProcessoProps) {
  const a = p.analise;
  const d = p.dados_extraidos;
  const resumo = d?.resumo_fatos ?? "";
  const fracos = a?.pontos_fracos_banco ?? [];
  const contradicoes = a?.contradicoes ?? [];
  if (!resumo && fracos.length === 0 && contradicoes.length === 0) return null;
  return (
    <Card>
      <Group justify="space-between">
        <Text fw={600}>Análise do caso</Text>
        <OrigemBadge origem={a?.origem ?? d?.origem} rotulo="análise stub" />
      </Group>
      {resumo && <Text size="sm" mt="xs" c="dimmed" lineClamp={4}>{resumo}</Text>}
      {fracos.length > 0 && (
        <>
          <Text size="xs" fw={600} c="vermelho.7" tt="uppercase" lts=".06em" mt="md">Pontos fracos do banco</Text>
          <List size="sm" mt={4} spacing={4}>
            {fracos.map((x, i) => <List.Item key={i}>{x}</List.Item>)}
          </List>
        </>
      )}
      {contradicoes.length > 0 && (
        <>
          <Text size="xs" fw={500} c="verde.7" tt="uppercase" lts=".06em" mt="md">Contradições da petição</Text>
          <List size="sm" mt={4} spacing={4}>
            {contradicoes.map((x, i) => <List.Item key={i}>{x}</List.Item>)}
          </List>
        </>
      )}
    </Card>
  );
}
