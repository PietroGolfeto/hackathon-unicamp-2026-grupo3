import { Table, Text } from "@mantine/core";

export function CabecalhoColuna({ children, alinhar }: { children: string; alinhar?: "left" | "right" }) {
  return (
    <Table.Th style={{ textAlign: alinhar ?? "left" }}>
      <Text size="xs" fw={600} tt="uppercase" lts=".06em" c="dimmed">{children}</Text>
    </Table.Th>
  );
}
