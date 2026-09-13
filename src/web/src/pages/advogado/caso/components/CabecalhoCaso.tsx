import { Anchor, Badge, Group, Text } from "@mantine/core";
import { Link } from "react-router";

import { IcoVoltar } from "../../../../components/Icones";
import type { ProcessoProps } from "../caso.types";

export function CabecalhoCaso({ p }: ProcessoProps) {
  return (
    <Group gap="xs" align="center" wrap="wrap">
      <Anchor component={Link} to="/casos" size="xs" c="dimmed" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
        <IcoVoltar size={12} /> Casos
      </Anchor>
      <Text size="xs" c="dimmed">·</Text>
      <Text size="xs" c="dimmed" className="numero" style={{ wordBreak: "break-all" }}>{p.numero}</Text>
      <Badge size="xs" variant="default">{p.uf}</Badge>
    </Group>
  );
}
