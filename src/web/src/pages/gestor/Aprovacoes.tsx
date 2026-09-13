import {
  Alert, Anchor, Badge, Button, Center, Group, Modal, Paper, Skeleton, Stack, Table, Text, Textarea, ThemeIcon, Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";

import { api, type Aprovacao } from "../../api/client";
import { TipoBadge } from "../../components/Badges";
import { IcoCheck } from "../../components/Icones";
import { brl, dataHora, num } from "../../lib/format";

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
      notifications.show({ message: alvo?.acao === "aprovar" ? "Acordo aprovado." : "Acordo rejeitado.", color: "verde" });
    },
    onError: (e) => notifications.show({ message: (e as Error).message, color: "vermelho" }),
  });
  const abrir = (a: Aprovacao, acao: "aprovar" | "rejeitar") => { setAlvo({ a, acao }); open(); };
  const lista = data ?? [];

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end" wrap="wrap">
        <div>
          <Title order={2}>Aprovações</Title>
          <Text c="dimmed" size="sm" mt={4}>Acordos fora da banda ou com valor da causa acima do teto.</Text>
        </div>
        {lista.length > 0 && <Badge size="lg" color="laranja" variant="filled" className="pulsar">{num(lista.length)} pendente(s)</Badge>}
      </Group>

      {error && <Alert color="vermelho" variant="light">{(error as Error).message}</Alert>}
      {isLoading && <Skeleton height={160} radius={12} />}

      {!isLoading && lista.length === 0 && (
        <Paper withBorder p="xl">
          <Center>
            <Stack align="center" gap="xs" py="lg">
              <ThemeIcon size={48} radius="xl" color="verde" variant="light"><IcoCheck size={24} /></ThemeIcon>
              <Text className="serif" fz="xl">Nada pendente.</Text>
              <Text size="sm" c="dimmed" ta="center" maw={420}>
                Quando um advogado propuser acordo fora da banda ou acima do teto de valor da causa, o pedido aparece aqui.
              </Text>
            </Stack>
          </Center>
        </Paper>
      )}

      {lista.length > 0 && (
        <Paper withBorder style={{ overflow: "hidden" }}>
          <Table.ScrollContainer minWidth={840}>
            <Table verticalSpacing="sm" horizontalSpacing="md" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  {["Quando", "Processo", "Advogado", "Recomendado", "Proposto", "Justificativa", ""].map((t, i) => (
                    <Table.Th key={i}><Text size="xs" fw={500} tt="uppercase" lts=".06em" c="dimmed">{t}</Text></Table.Th>
                  ))}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody className="escalonado">
                {lista.map((a) => (
                  <Table.Tr key={a.decisao.id}>
                    <Table.Td><Text size="sm" c="dimmed" className="numero">{dataHora(a.decisao.created_at)}</Text></Table.Td>
                    <Table.Td>
                      <Anchor component={Link} to={`/casos/${a.processo_id}`} size="sm" fw={500} c="tinta.6" className="numero">{a.numero}</Anchor>
                      <Text size="xs" c="dimmed">{a.autor ? `${a.autor} · ` : ""}causa {brl(a.valor_causa)}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{a.decisao.usuario_nome}</Text>
                      <Text size="xs" c="dimmed">{a.escritorio}</Text>
                    </Table.Td>
                    <Table.Td>
                      <TipoBadge tipo={a.recomendacao.tipo} size="sm" />
                      {a.recomendacao.valor_min != null && (
                        <Text size="xs" c="dimmed" mt={2} className="numero">{brl(a.recomendacao.valor_min)} – {brl(a.recomendacao.valor_max)}</Text>
                      )}
                    </Table.Td>
                    <Table.Td><Text className="serif numero" fz="lg">{brl(a.decisao.valor_proposto)}</Text></Table.Td>
                    <Table.Td><Text size="sm" lineClamp={3} maw={300}>{a.decisao.justificativa ?? "—"}</Text></Table.Td>
                    <Table.Td>
                      <Group gap={6} wrap="nowrap" justify="end">
                        <Button size="compact-sm" color="verde" onClick={() => abrir(a, "aprovar")}>Aprovar</Button>
                        <Button size="compact-sm" color="vermelho" variant="light" onClick={() => abrir(a, "rejeitar")}>Rejeitar</Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </Paper>
      )}

      <Modal opened={aberto} onClose={close}
        title={alvo ? `${alvo.acao === "aprovar" ? "Aprovar" : "Rejeitar"} acordo de ${brl(alvo.a.decisao.valor_proposto)}` : ""}>
        <Stack>
          {alvo && <Text size="sm" c="dimmed" className="numero">{alvo.a.numero} · {alvo.a.decisao.usuario_nome} · {alvo.a.escritorio}</Text>}
          <Textarea label="Comentário para o advogado (opcional)" value={comentario} onChange={(e) => setComentario(e.currentTarget.value)} autosize minRows={2} />
          <Group justify="end">
            <Button variant="default" onClick={close}>Cancelar</Button>
            <Button color={alvo?.acao === "aprovar" ? "verde" : "vermelho"} onClick={() => m.mutate()} loading={m.isPending}>Confirmar</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
