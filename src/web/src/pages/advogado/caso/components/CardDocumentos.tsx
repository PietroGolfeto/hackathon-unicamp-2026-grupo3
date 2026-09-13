import { Box, Card, Group, SimpleGrid, Stack, Text, ThemeIcon, UnstyledButton } from "@mantine/core";

import { IcoCheck, IcoDoc, IcoExterno } from "../../../../components/Icones";
import { COR_RELEVANCIA, GRUPOS_DOCUMENTOS } from "../caso.const";
import type { DocumentosAbertos, ProcessoProps } from "../caso.types";
import { ListaSubsidios } from "./ListaSubsidios";

export function CardDocumentos({ p, abertos, onAbrir }: ProcessoProps & {
  abertos: DocumentosAbertos; onAbrir: (arquivo: string) => void;
}) {
  if (p.documentos.length === 0) {
    return (
      <Card>
        <Text fw={500}>Documentos</Text>
        <Text size="sm" c="dimmed" mt={4}>Processo sem PDFs anexados (caso sintético).</Text>
        <ListaSubsidios subsidios={p.subsidios} />
      </Card>
    );
  }
  return (
    <Card>
      <Text fw={500}>Documentos</Text>
      <Text size="xs" c="dimmed" mb="sm">
        Abrem em nova aba. Os que você abriu ficam marcados. O comentário abaixo de cada um é da leitura da IA.
      </Text>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        {GRUPOS_DOCUMENTOS.map(([tipo, rotulo]) => {
          const docs = p.documentos.filter((d) => d.tipo === tipo);
          return (
            <div key={tipo}>
              <Text size="xs" fw={500} c="dimmed" tt="uppercase" lts=".06em" mb={4}>{rotulo}</Text>
              <Stack gap={2}>
                {docs.map((d) => {
                  const aberto = abertos.has(d.arquivo);
                  return (
                    <UnstyledButton key={d.arquivo} component="a" href={d.url} target="_blank" rel="noopener" className="linha-link"
                      onClick={() => onAbrir(d.arquivo)} p={6} style={{ borderRadius: 8, display: "flex", alignItems: "flex-start", gap: 10 }}>
                      <ThemeIcon size={26} radius="sm" variant="light" color={aberto ? "verde" : "tinta"}>
                        {aberto ? <IcoCheck size={14} /> : <IcoDoc size={14} />}
                      </ThemeIcon>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <Group gap={6} wrap="nowrap">
                          {d.relevancia && (
                            <Box w={6} h={6} bg={`${COR_RELEVANCIA[d.relevancia] ?? "gray"}.6`}
                              style={{ borderRadius: 999, flex: "0 0 auto" }} />
                          )}
                          <Text size="sm" c={aberto ? "dimmed" : undefined} truncate>{d.arquivo}</Text>
                        </Group>
                        {d.comentario && <Text size="xs" c="dimmed" lh={1.35} mt={2}>{d.comentario}</Text>}
                      </div>
                      <IcoExterno size={13} style={{ color: "var(--mantine-color-dimmed)", marginTop: 6 }} />
                    </UnstyledButton>
                  );
                })}
                {docs.length === 0 && <Text size="xs" c="dimmed">nenhum</Text>}
              </Stack>
            </div>
          );
        })}
      </SimpleGrid>
      <ListaSubsidios subsidios={p.subsidios} />
    </Card>
  );
}
