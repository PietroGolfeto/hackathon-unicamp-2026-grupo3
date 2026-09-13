import { Box } from "@mantine/core";

import { useMontado } from "../../../../lib/animacao";

export function MedidorProbabilidade({ valor }: { valor: number }) {
  const pronto = useMontado();
  return (
    <Box h={10} bg="gray.1" style={{ borderRadius: 5, overflow: "hidden" }}>
      <Box h="100%" bg="tinta.6" className="preencher" style={{ width: pronto ? `${valor * 100}%` : 0, borderRadius: 5 }} />
    </Box>
  );
}
