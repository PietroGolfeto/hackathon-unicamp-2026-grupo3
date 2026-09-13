import { Paper, Text } from "@mantine/core";

/** Métrica do cartão escuro de recomendação: rótulo translúcido e valor na serifada. */
export function MiniMetrica({ rotulo, valor, cor }: { rotulo: string; valor: string; cor?: string }) {
  return (
    <Paper p="md" radius={12} bg="rgba(255,255,255,.06)" style={{ border: "1px solid rgba(255,255,255,.09)" }}>
      <Text size="sm" c="rgba(255,255,255,.55)">{rotulo}</Text>
      <Text className="serif numero" fz={26} lh={1.2} mt={4} c={cor ?? "white"}>{valor}</Text>
    </Paper>
  );
}
