import { Anchor, Badge, Button, Group, Paper, Text, Title } from "@mantine/core";
import { Link } from "react-router";

import { OrigemBadge, SinalChip, StatusBadge } from "../../../../components/Badges";
import { IcoCopiar, IcoVoltar } from "../../../../components/Icones";
import { brl } from "../../../../lib/format";
import type { ProcessoProps } from "../caso.types";
import { useCopiarResumo } from "../hooks/useCopiarResumo";

export function CabecalhoCaso({ p }: ProcessoProps) {
  const autor = p.dados_extraidos?.autor;
  const copiar = useCopiarResumo(p.id);
  return (
    <Paper withBorder p="lg">
      <Group justify="space-between" align="start" wrap="wrap" gap="md">
        <div>
          <Anchor component={Link} to="/casos" size="xs" c="dimmed" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <IcoVoltar size={12} /> Casos
          </Anchor>
          <Title order={2} className="numero" mt={4} style={{ wordBreak: "break-all" }}>{p.numero}</Title>
          <Group gap={6} mt="xs" wrap="wrap">
            <Badge variant="default">{p.uf}</Badge>
            {p.sub_assunto && <Badge variant="default">{p.sub_assunto}</Badge>}
            <StatusBadge status={p.status} />
            {p.origem === "exemplo" && <Badge color="tinta" variant="light">autos reais</Badge>}
            <OrigemBadge origem={p.dados_extraidos?.origem} rotulo="extração stub" />
          </Group>
          {autor?.nome && (
            <Text mt="sm" size="sm">
              <b>{autor.nome}</b>
              {autor.idade ? ` · ${autor.idade} anos` : ""}{autor.cpf_mascarado ? ` · CPF ${autor.cpf_mascarado}` : ""}
              {p.dados_extraidos?.comarca ? ` · ${p.dados_extraidos.comarca}` : ""}
            </Text>
          )}
          <Group gap="lg" mt={autor?.nome ? 4 : "sm"}>
            <div>
              <Text size="xs" c="dimmed" tt="uppercase" lts=".06em" fw={500}>Valor da causa</Text>
              <Text className="numero" fz="lg">{brl(p.valor_causa, true)}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed" tt="uppercase" lts=".06em" fw={500}>Escritório</Text>
              <Text fz="sm" mt={2}>{p.escritorio}</Text>
            </div>
          </Group>
          {p.sinais.length > 0 && (
            <Group gap={4} mt="sm" wrap="wrap">{p.sinais.map((s) => <SinalChip key={s.codigo} sinal={s} />)}</Group>
          )}
        </div>
        <Button variant="default" size="sm" leftSection={<IcoCopiar size={15} />} onClick={() => copiar.mutate()} loading={copiar.isPending}>
          Copiar resumo
        </Button>
      </Group>
    </Paper>
  );
}
