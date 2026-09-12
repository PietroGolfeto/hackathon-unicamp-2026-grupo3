import { Box, Group, Text } from "@mantine/core";

import { useMontado } from "../../../../lib/animacao";
import { brl } from "../../../../lib/format";

/** Faixa de oferta em relação ao valor da causa: banda em laranja claro, marcador no valor sugerido. */
export function BandaOferta({ min, sugerido, max, causa }: { min: number; sugerido: number; max: number; causa: number }) {
  const pronto = useMontado();
  const pos = (v: number) => Math.min(100, Math.max(0, (v / causa) * 100));
  return (
    <div>
      <Box pos="relative" h={10} bg="gray.1" style={{ borderRadius: 5 }}>
        <Box pos="absolute" top={0} bottom={0} bg="laranja.3" className="preencher"
          style={{ left: `${pos(min)}%`, width: pronto ? `${pos(max) - pos(min)}%` : 0, borderRadius: 5 }} />
        {pronto && (
          <Box pos="absolute" top={-5} w={4} h={20} bg="laranja.7" className="pingar" style={{ left: `${pos(sugerido)}%`, borderRadius: 2 }} />
        )}
      </Box>
      <Group justify="space-between" mt={6}>
        <Text size="xs" c="dimmed" className="numero">banda {brl(min)} a {brl(max)}</Text>
        <Text size="xs" c="dimmed" className="numero">causa {brl(causa)}</Text>
      </Group>
    </div>
  );
}
