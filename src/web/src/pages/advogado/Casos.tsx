import { Alert, Anchor, Badge, Group, Loader, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router";

import { api } from "../../api/client";
import { useSession } from "../../auth/useSession";
import { OrigemBadge, StatusBadge, TipoBadge } from "../../components/Badges";
import { brl } from "../../lib/format";

export default function Casos() {
  const [busca, setBusca] = useState("");
  const { data: usuario } = useSession();
  const { data, isLoading, error } = useQuery({ queryKey: ["processos"], queryFn: () => api.processos() });

  const filtrados = useMemo(() => {
    const termo = busca.replace(/\D/g, "");
    const lista = data ?? [];
    if (!termo && !busca.trim()) return lista;
    return lista.filter((p) =>
      (termo && p.numero.replace(/\D/g, "").includes(termo)) ||
      (p.autor ?? "").toLowerCase().includes(busca.trim().toLowerCase()),
    );
  }, [data, busca]);

  const pendentes = (data ?? []).filter((p) => p.status === "pendente").length;
  const temAutor = (data ?? []).some((p) => p.autor); // só com P3 plugado

  return (
    <Stack gap="sm">
      <Group justify="space-between" align="end" wrap="wrap">
        <div>
          <Title order={3}>Casos</Title>
          <Text c="dimmed" size="sm">
            {usuario?.papel === "gestor" ? "Todos os escritórios" : usuario?.escritorio_nome}
            {data ? ` · ${data.length} processos · ${pendentes} pendentes` : ""}
          </Text>
        </div>
        <TextInput placeholder={temAutor ? "Buscar por número ou autor" : "Buscar por número"} value={busca}
          onChange={(e) => setBusca(e.currentTarget.value)} w={{ base: "100%", sm: 300 }} />
      </Group>
      {isLoading && <Loader />}
      {error && <Alert color="red">{(error as Error).message}</Alert>}
      {data && (
        <Table.ScrollContainer minWidth={720}>
          <Table striped highlightOnHover withTableBorder verticalSpacing="xs">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Processo</Table.Th>
                {temAutor && <Table.Th>Autor</Table.Th>}
                <Table.Th>Valor da causa</Table.Th>
                <Table.Th>Subsídios</Table.Th>
                <Table.Th>Recomendação</Table.Th>
                <Table.Th>Situação</Table.Th>
                {usuario?.papel === "gestor" && <Table.Th>Escritório</Table.Th>}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {filtrados.map((p) => (
                <Table.Tr key={p.id}>
                  <Table.Td>
                    <Anchor component={Link} to={`/casos/${p.id}`} fw={600} size="sm">{p.numero}</Anchor>
                    <Group gap={4} mt={2}>
                      <Badge size="xs" variant="default">{p.uf}</Badge>
                      {p.sub_assunto && <Badge size="xs" variant="default">{p.sub_assunto}</Badge>}
                      {p.origem === "exemplo" && <Badge size="xs" color="grape" variant="light">autos reais</Badge>}
                      <OrigemBadge origem={p.scores_origem} rotulo="score stub" />
                    </Group>
                  </Table.Td>
                  {temAutor && <Table.Td><Text size="sm">{p.autor ?? "—"}</Text></Table.Td>}
                  <Table.Td><Text size="sm">{brl(p.valor_causa)}</Text></Table.Td>
                  <Table.Td>
                    <Text size="sm">{p.n_subsidios}/6</Text>
                    {p.sinais.length > 0 && <Text size="xs" c="orange">{p.sinais.length} sinal(is)</Text>}
                  </Table.Td>
                  <Table.Td>
                    <TipoBadge tipo={p.recomendacao?.tipo} size="sm" />
                    {p.recomendacao?.valor_sugerido != null && (
                      <Text size="xs" c="dimmed">{brl(p.recomendacao.valor_sugerido)}</Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <StatusBadge status={p.status} />
                    {p.decisao_tipo && <Text size="xs" c="dimmed">decidiu {p.decisao_tipo}</Text>}
                  </Table.Td>
                  {usuario?.papel === "gestor" && <Table.Td><Text size="sm">{p.escritorio}</Text></Table.Td>}
                </Table.Tr>
              ))}
              {filtrados.length === 0 && (
                <Table.Tr><Table.Td colSpan={7}><Text c="dimmed" ta="center">Nenhum processo encontrado.</Text></Table.Td></Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Stack>
  );
}
