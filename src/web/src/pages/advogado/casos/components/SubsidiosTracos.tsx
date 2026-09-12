import { Box, Group, Text } from "@mantine/core";

import type { ProcessoResumo } from "../../../../api/client";
import { TOTAL_SUBSIDIOS } from "../casos.const";

/** Seis traços, um por subsídio: cheio quando o banco entregou o documento. */
export function SubsidiosTracos({ p }: { p: ProcessoResumo }) {
  return (
    <Group gap={8} wrap="nowrap">
      <Group gap={2} wrap="nowrap">
        {Array.from({ length: TOTAL_SUBSIDIOS }).map((_, i) => (
          <Box key={i} w={6} h={14} bg={i < p.n_subsidios ? "tinta.6" : "gray.2"} style={{ borderRadius: 2 }} />
        ))}
      </Group>
      <Text size="sm" className="numero">{p.n_subsidios}/{TOTAL_SUBSIDIOS}</Text>
      {p.sinais.length > 0 && <Text size="xs" c="laranja.8">{p.sinais.length} sinal(is)</Text>}
    </Group>
  );
}
