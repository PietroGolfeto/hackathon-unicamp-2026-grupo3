import { Card, Group, List, Text } from "@mantine/core";

import { OrigemBadge } from "../../../../components/Badges";
import type { ProcessoProps } from "../caso.types";

/** Só o que o advogado lê em 30 segundos: resumo em bullets e, se houver, as contradições da petição. */
export function CardAnalise({ p }: ProcessoProps) {
  const a = p.analise;
  const d = p.dados_extraidos;
  const resumo = (d?.resumo_fatos ?? "").split("\n").map((s) => s.trim()).filter(Boolean);
  const contradicoes = a?.contradicoes ?? [];
  if (resumo.length === 0 && contradicoes.length === 0) return null;
  return (
    <Card>
      <Group justify="space-between">
        <Text fw={600}>Resumo do caso</Text>
        <OrigemBadge origem={a?.origem ?? d?.origem} rotulo="análise stub" />
      </Group>
      <List size="sm" mt="xs" spacing={4}>
        {resumo.map((x, i) => <List.Item key={i}>{x}</List.Item>)}
      </List>
      {contradicoes.length > 0 && (
        <>
          <Text size="xs" fw={500} c="laranja.8" tt="uppercase" lts=".06em" mt="md">Contradições da petição</Text>
          <List size="sm" mt={4} spacing={4}>
            {contradicoes.map((x, i) => <List.Item key={i}>{x}</List.Item>)}
          </List>
        </>
      )}
    </Card>
  );
}
