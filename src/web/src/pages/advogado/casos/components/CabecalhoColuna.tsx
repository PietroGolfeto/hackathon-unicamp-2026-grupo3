import { Table, Text } from "@mantine/core";

export function CabecalhoColuna({ children, largura }: { children: string; largura: number }) {
  return (
    <Table.Th w={largura} style={{ whiteSpace: "nowrap" }}>
      <Text size="xs" fw={600} tt="uppercase" lts=".06em" c="dimmed">{children}</Text>
    </Table.Th>
  );
}
