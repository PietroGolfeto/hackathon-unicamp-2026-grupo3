import { Anchor, Group, Paper, Text } from "@mantine/core";

import type { Pessoa } from "../../../../api/client";

export function ContatoAdverso({ c }: { c: Pessoa }) {
  const partes = [c.nome, c.oab ? `OAB ${c.oab}` : null, c.email, c.telefone].filter(Boolean);
  if (partes.length === 0) return null;
  return (
    <Paper p="sm" mt="sm" radius={8} bg="gray.0">
      <Text size="xs" c="dimmed" fw={500} tt="uppercase" lts=".06em">Advogado(a) da parte autora</Text>
      <Group gap="xs" wrap="wrap" mt={2}>
        <Text size="sm">{partes.join(" · ")}</Text>
        {c.email && <Anchor href={`mailto:${c.email}`} size="sm">e-mail</Anchor>}
        {c.telefone && <Anchor href={`https://wa.me/55${c.telefone.replace(/\D/g, "")}`} target="_blank" size="sm">WhatsApp</Anchor>}
      </Group>
    </Paper>
  );
}
