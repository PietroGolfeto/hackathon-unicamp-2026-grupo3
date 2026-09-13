import { Box, Text } from "@mantine/core";

import { useMontado } from "../../../../lib/animacao";
import { pct } from "../../../../lib/format";

const TAMANHO = 124;
const ESPESSURA = 9;
const RAIO = (TAMANHO - ESPESSURA) / 2;
const VOLTA = 2 * Math.PI * RAIO;

/** Anel de êxito na defesa: arco laranja sobre trilho translúcido, para o cartão escuro de recomendação. */
export function AnelProbabilidade({ valor }: { valor: number }) {
  const pronto = useMontado();
  return (
    <Box pos="relative" w={TAMANHO} h={TAMANHO}>
      <svg width={TAMANHO} height={TAMANHO} style={{ transform: "rotate(-90deg)" }} aria-hidden>
        <circle cx={TAMANHO / 2} cy={TAMANHO / 2} r={RAIO} fill="none" stroke="rgba(255,255,255,.12)" strokeWidth={ESPESSURA} />
        <circle
          cx={TAMANHO / 2} cy={TAMANHO / 2} r={RAIO} fill="none"
          stroke="var(--enter-laranja)" strokeWidth={ESPESSURA} strokeLinecap="round"
          strokeDasharray={VOLTA} strokeDashoffset={VOLTA * (1 - (pronto ? valor : 0))}
          className="preencher-anel"
        />
      </svg>
      <Box pos="absolute" inset={0} style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Text className="serif numero" fz={34} lh={1}>{pct(valor)}</Text>
      </Box>
    </Box>
  );
}
