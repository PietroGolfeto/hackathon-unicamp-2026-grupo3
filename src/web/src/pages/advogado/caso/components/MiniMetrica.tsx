import { Paper, Text } from "@mantine/core";

export function MiniMetrica({ rotulo, valor, cor }: { rotulo: string; valor: string; cor?: string }) {
  return (
    <Paper p="sm" radius={8} bg="gray.0">
      <Text size="xs" c="dimmed">{rotulo}</Text>
      <Text className="serif numero" fz="lg" fw={500} c={cor}>{valor}</Text>
    </Paper>
  );
}
