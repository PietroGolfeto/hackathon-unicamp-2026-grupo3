import { Paper, Text } from "@mantine/core";

export function MiniMetrica({ rotulo, valor, cor }: { rotulo: string; valor: string; cor?: string }) {
  return (
    <Paper p="sm" radius={8} bg="gray.0">
      <Text size="xs" c="dimmed">{rotulo}</Text>
      <Text fw={500} className="numero" c={cor}>{valor}</Text>
    </Paper>
  );
}
