import {
  Alert, Anchor, Badge, Box, Group, Paper, SegmentedControl, Skeleton, Stack, Table, Text, TextInput, Title,
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";

import { api, type ProcessoResumo } from "../../api/client";
import { useSession } from "../../auth/useSession";
import { OrigemBadge, StatusBadge, TipoBadge } from "../../components/Badges";
import { IcoBusca } from "../../components/Icones";
import { brl, num } from "../../lib/format";

type Situacao = "todos" | "pendente" | "decidido";

export default function Casos() {
  const [busca, setBusca] = useState("");
  const [situacao, setSituacao] = useState<Situacao>("todos");
  const { data: usuario } = useSession();
  const navigate = useNavigate();
  const { data, isLoading, error } = useQuery({ queryKey: ["processos"], queryFn: () => api.processos() });
  const gestor = usuario?.papel === "gestor";

  const filtrados = useMemo(() => {
    const termo = busca.replace(/\D/g, "");
    const texto = busca.trim().toLowerCase();
    return (data ?? []).filter((p) => {
      if (situacao === "pendente" && p.status !== "pendente") return false;
      if (situacao === "decidido" && p.status === "pendente") return false;
      if (!texto) return true;
      return (termo !== "" && p.numero.replace(/\D/g, "").includes(termo)) || (p.autor ?? "").toLowerCase().includes(texto);
    });
  }, [data, busca, situacao]);

  const pendentes = (data ?? []).filter((p) => p.status === "pendente").length;
  const temAutor = (data ?? []).some((p) => p.autor); // só com P3 plugado
  const colunas = 5 + (temAutor ? 1 : 0) + (gestor ? 1 : 0);

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end" wrap="wrap" gap="md">
        <div>
          <Title order={2}>Casos</Title>
          <Text c="dimmed" size="sm" mt={4}>
            {gestor ? "Todos os escritórios" : usuario?.escritorio_nome}
            {data ? ` · ${num(data.length)} processos · ${num(pendentes)} pendentes` : ""}
          </Text>
        </div>
        <Group gap="sm" wrap="wrap">
          <SegmentedControl size="sm" radius={8} value={situacao} onChange={(v) => setSituacao(v as Situacao)}
            data={[{ value: "todos", label: "Todos" }, { value: "pendente", label: "Pendentes" }, { value: "decidido", label: "Decididos" }]} />
          <TextInput placeholder={temAutor ? "Buscar por número ou autor" : "Buscar por número"} value={busca}
            onChange={(e) => setBusca(e.currentTarget.value)} w={{ base: "100%", sm: 300 }} leftSection={<IcoBusca size={16} />} />
        </Group>
      </Group>

      {error && <Alert color="vermelho" variant="light">{(error as Error).message}</Alert>}

      <Paper withBorder style={{ overflow: "hidden" }}>
        <Table.ScrollContainer minWidth={760}>
          <Table verticalSpacing="sm" horizontalSpacing="md" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Cabecalho>Processo</Cabecalho>
                {temAutor && <Cabecalho>Autor</Cabecalho>}
                <Cabecalho alinhar="right">Valor da causa</Cabecalho>
                <Cabecalho>Subsídios</Cabecalho>
                <Cabecalho>Recomendação</Cabecalho>
                <Cabecalho>Situação</Cabecalho>
                {gestor && <Cabecalho>Escritório</Cabecalho>}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody className={isLoading ? undefined : "escalonado"}>
              {isLoading && Array.from({ length: 8 }).map((_, i) => (
                <Table.Tr key={i}>
                  <Table.Td colSpan={colunas}><Skeleton height={34} radius="sm" /></Table.Td>
                </Table.Tr>
              ))}
              {filtrados.map((p) => (
                <Table.Tr key={p.id} className="linha-link" onClick={() => navigate(`/casos/${p.id}`)}>
                  <Table.Td>
                    <Anchor component={Link} to={`/casos/${p.id}`} fw={500} size="sm" c="tinta.6" className="numero"
                      onClick={(e) => e.stopPropagation()}>
                      {p.numero}
                    </Anchor>
                    <Group gap={4} mt={4}>
                      <Badge size="xs" variant="default">{p.uf}</Badge>
                      {p.sub_assunto && <Badge size="xs" variant="default">{p.sub_assunto}</Badge>}
                      {p.origem === "exemplo" && <Badge size="xs" color="tinta" variant="light">autos reais</Badge>}
                      <OrigemBadge origem={p.scores_origem} rotulo="score stub" />
                    </Group>
                  </Table.Td>
                  {temAutor && <Table.Td><Text size="sm">{p.autor ?? "—"}</Text></Table.Td>}
                  <Table.Td align="right"><Text size="sm" className="numero">{brl(p.valor_causa)}</Text></Table.Td>
                  <Table.Td><Subsidios p={p} /></Table.Td>
                  <Table.Td>
                    <TipoBadge tipo={p.recomendacao?.tipo} size="sm" />
                    {p.recomendacao?.valor_sugerido != null && (
                      <Text size="xs" c="dimmed" mt={2} className="numero">{brl(p.recomendacao.valor_sugerido)}</Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <StatusBadge status={p.status} size="sm" />
                    {p.decisao_tipo && <Text size="xs" c="dimmed" mt={2}>decidiu {p.decisao_tipo}</Text>}
                  </Table.Td>
                  {gestor && <Table.Td><Text size="sm">{p.escritorio}</Text></Table.Td>}
                </Table.Tr>
              ))}
              {!isLoading && filtrados.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={colunas}>
                    <Text className="serif" c="dimmed" ta="center" py="xl" fz="lg">Nenhum processo encontrado.</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Paper>
    </Stack>
  );
}

function Cabecalho({ children, alinhar }: { children: string; alinhar?: "left" | "right" }) {
  return (
    <Table.Th style={{ textAlign: alinhar ?? "left" }}>
      <Text size="xs" fw={500} tt="uppercase" lts=".06em" c="dimmed">{children}</Text>
    </Table.Th>
  );
}

/** Seis traços, um por subsídio: cheio quando o banco entregou o documento. */
function Subsidios({ p }: { p: ProcessoResumo }) {
  return (
    <Group gap={8} wrap="nowrap">
      <Group gap={2} wrap="nowrap">
        {Array.from({ length: 6 }).map((_, i) => (
          <Box key={i} w={6} h={14} bg={i < p.n_subsidios ? "tinta.6" : "gray.2"} style={{ borderRadius: 2 }} />
        ))}
      </Group>
      <Text size="sm" className="numero">{p.n_subsidios}/6</Text>
      {p.sinais.length > 0 && <Text size="xs" c="laranja.8">{p.sinais.length} sinal(is)</Text>}
    </Group>
  );
}
