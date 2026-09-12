import { Button, CopyButton, Group, Stack, Text, Textarea } from "@mantine/core";

import type { Minutas } from "../../../../api/client";
import { OrigemBadge } from "../../../../components/Badges";
import { IcoCheck, IcoCopiar } from "../../../../components/Icones";

export function MinutasView({ m }: { m: Minutas }) {
  const itens = [
    ["Proposta de acordo", m.proposta_acordo], ["Mensagem de contato", m.mensagem_contato], ["Roteiro de defesa", m.roteiro_defesa],
  ].filter(([, t]) => t);
  return (
    <Stack gap="xs" mt="md">
      <Group gap="xs"><Text fw={500} size="sm">Minutas</Text><OrigemBadge origem={m.origem} rotulo="minuta stub" /></Group>
      {itens.map(([titulo, texto]) => (
        <div key={titulo}>
          <Group justify="space-between" mb={2}>
            <Text size="xs" c="dimmed">{titulo}</Text>
            <CopyButton value={texto}>
              {({ copied, copy }) => (
                <Button size="compact-xs" variant="light" color={copied ? "verde" : "tinta"} onClick={copy} leftSection={copied ? <IcoCheck size={12} /> : <IcoCopiar size={12} />}>
                  {copied ? "Copiado" : "Copiar"}
                </Button>
              )}
            </CopyButton>
          </Group>
          <Textarea value={texto} readOnly autosize minRows={3} maxRows={10} styles={{ input: { fontSize: 13 } }} />
        </div>
      ))}
    </Stack>
  );
}
