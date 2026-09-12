import { Alert, Anchor, Button, Group, Loader, Modal, Stack, Table, Text, Textarea, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";

import { api, type Aprovacao } from "../../api/client";
import { TipoBadge } from "../../components/Badges";
import { brl, dataHora } from "../../lib/format";

export default function Aprovacoes() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["aprovacoes"], queryFn: api.aprovacoes, refetchInterval: 5000 });
  const [alvo, setAlvo] = useState<{ a: Aprovacao; acao: "aprovar" | "rejeitar" } | null>(null);
  const [comentario, setComentario] = useState("");
  const [aberto, { open, close }] = useDisclosure(false);
  const m = useMutation({
    mutationFn: () => api.aprovar(alvo!.a.decisao.id, alvo!.acao, comentario),
    onSuccess: () => {
      close(); setComentario("");
      qc.invalidateQueries({ queryKey: ["aprovacoes"] }); qc.invalidateQueries({ queryKey: ["aderencia"] });
      notifications.show({ message: alvo?.acao === "aprovar" ? "Acordo aprovado." : "Acordo rejeitado.", color: "teal" });
    },
    onError: (e) => notifications.show({ message: (e as Error).message, color: "red" }),
  });
  const abrir = (a: Aprovacao, acao: "aprovar" | "rejeitar") => { setAlvo({ a, acao }); open(); };

  if (isLoading) return <Loader />;
  if (error) return <Alert color="red">{(error as Error).message}</Alert>;
  return (
    <Stack gap="sm">
      <div>
        <Title order={3}>Aprovações</Title>
        <Text c="dimmed" size="sm">Acordos fora da banda ou com valor da causa acima do teto. {data?.length ?? 0} pendente(s).</Text>
      </div>
      <Table.ScrollContainer minWidth={800}>
        <Table striped withTableBorder verticalSpacing="xs" fz="sm">
          <Table.Thead>
            <Table.Tr><Table.Th>Quando</Table.Th><Table.Th>Processo</Table.Th><Table.Th>Advogado</Table.Th><Table.Th>Recomendado</Table.Th><Table.Th>Proposto</Table.Th><Table.Th>Justificativa</Table.Th><Table.Th /></Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(data ?? []).map((a) => (
              <Table.Tr key={a.decisao.id}>
                <Table.Td>{dataHora(a.decisao.created_at)}</Table.Td>
                <Table.Td>
                  <Anchor component={Link} to={`/casos/${a.processo_id}`} size="sm">{a.numero}</Anchor>
                  <Text size="xs" c="dimmed">{a.autor ?? "—"} · causa {brl(a.valor_causa)}</Text>
                </Table.Td>
                <Table.Td>{a.decisao.usuario_nome} <Text span size="xs" c="dimmed">{a.escritorio}</Text></Table.Td>
                <Table.Td>
                  <TipoBadge tipo={a.recomendacao.tipo} size="xs" />
                  {a.recomendacao.tipo === "acordo" && <Text size="xs">{brl(a.recomendacao.valor_min)} – {brl(a.recomendacao.valor_max)}</Text>}
                </Table.Td>
                <Table.Td><Text fw={600}>{brl(a.decisao.valor_proposto)}</Text></Table.Td>
                <Table.Td><Text size="xs" lineClamp={3} maw={280}>{a.decisao.justificativa ?? "—"}</Text></Table.Td>
                <Table.Td>
                  <Group gap={4} wrap="nowrap">
                    <Button size="compact-xs" color="teal" onClick={() => abrir(a, "aprovar")}>Aprovar</Button>
                    <Button size="compact-xs" color="red" variant="light" onClick={() => abrir(a, "rejeitar")}>Rejeitar</Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {(data ?? []).length === 0 && <Table.Tr><Table.Td colSpan={7}><Text c="dimmed" ta="center">Nada pendente.</Text></Table.Td></Table.Tr>}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      <Modal opened={aberto} onClose={close} title={alvo ? `${alvo.acao === "aprovar" ? "Aprovar" : "Rejeitar"} acordo de ${brl(alvo.a.decisao.valor_proposto)} · ${alvo.a.numero}` : ""}>
        <Stack>
          <Textarea label="Comentário para o advogado (opcional)" value={comentario} onChange={(e) => setComentario(e.currentTarget.value)} autosize minRows={2} />
          <Group justify="end">
            <Button variant="default" onClick={close}>Cancelar</Button>
            <Button color={alvo?.acao === "aprovar" ? "teal" : "red"} onClick={() => m.mutate()} loading={m.isPending}>Confirmar</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
