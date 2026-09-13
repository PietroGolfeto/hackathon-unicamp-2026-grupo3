import { Box, Group, Text } from "@mantine/core";

import { useMontado } from "../../../../lib/animacao";
import { brl } from "../../../../lib/format";

/** Faixa de oferta em relação ao valor da causa, no cartão escuro: banda âmbar e marcador circular no valor sugerido. */
export function BandaOferta({ min, sugerido, max, causa }: { min: number; sugerido: number; max: number; causa: number }) {
  const pronto = useMontado();
  const pos = (v: number) => Math.min(100, Math.max(0, (v / causa) * 100));
  return (
    <div>
      <Box pos="relative" h={10} style={{ borderRadius: 5, background: "rgba(255,255,255,.12)" }}>
        <Box pos="absolute" top={0} bottom={0} className="preencher"
          style={{ left: `${pos(min)}%`, width: pronto ? `${pos(max) - pos(min)}%` : 0, borderRadius: 5, background: "rgba(255,174,53,.38)" }} />
        {pronto && (
          <Box pos="absolute" top={-3} w={16} h={16} bg="laranja.6" className="pingar"
            style={{ left: `${pos(sugerido)}%`, borderRadius: 999, border: "3px solid var(--enter-tinta)" }} />
        )}
      </Box>
      <Group justify="space-between" mt={8}>
        <Text size="xs" c="rgba(255,255,255,.55)" className="numero">banda {brl(min)} a {brl(max)}</Text>
        <Text size="xs" c="rgba(255,255,255,.55)" className="numero">causa {brl(causa)}</Text>
      </Group>
    </div>
  );
}
