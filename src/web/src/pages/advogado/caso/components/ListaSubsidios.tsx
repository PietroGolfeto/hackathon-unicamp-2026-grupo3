import { Badge, Group, Text } from "@mantine/core";

import { IcoCheck } from "../../../../components/Icones";
import { NOMES_SUBSIDIOS } from "../caso.const";

/** Subsídios entregues pelo banco em cheio; os que faltam aparecem riscados. */
export function ListaSubsidios({ subsidios }: { subsidios: Record<string, boolean> }) {
  const nome = (k: string) => NOMES_SUBSIDIOS[k] ?? k;
  const presentes = Object.entries(subsidios).filter(([, v]) => v).map(([k]) => nome(k));
  const ausentes = Object.entries(subsidios).filter(([, v]) => !v).map(([k]) => nome(k));
  return (
    <Group gap={6} mt="md" wrap="wrap">
      <Text size="xs" c="dimmed" mr={4}>Subsídios</Text>
      {presentes.map((n) => (
        <Badge key={n} color="tinta" variant="light" size="sm" leftSection={<IcoCheck size={11} />}>{n}</Badge>
      ))}
      {ausentes.map((n) => <Badge key={n} color="gray" variant="outline" size="sm" td="line-through">{n}</Badge>)}
    </Group>
  );
}
