import { Alert, Anchor, Badge, Card, Group, Loader, SimpleGrid, Stack, Table, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { api } from "../../api/client";
import { StatusBadge, TipoBadge } from "../../components/Badges";
import { Stat } from "../../components/Stat";
import { brl, brlCompacto, dataHora, duracao, num, pct } from "../../lib/format";

const POLL = 5000;

export default function Painel() {
  const ader = useQuery({ queryKey: ["aderencia"], queryFn: () => api.aderencia(), refetchInterval: POLL });
  const efet = useQuery({ queryKey: ["efetividade"], queryFn: () => api.efetividade(), refetchInterval: POLL });
  if (ader.isLoading || efet.isLoading) return <Loader />;
  if (ader.error || efet.error) return <Alert color="red">{((ader.error ?? efet.error) as Error).message}</Alert>;
  const a = ader.data!;
  const e = efet.data!;
  const bt = e.politica?.resumo_backtest;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="end" wrap="wrap">
        <div>
          <Title order={3}>Painel do gestor</Title>
          <Text c="dimmed" size="sm">
            Política ativa: v{e.politica?.versao} · {e.politica?.nome} · modelo {e.modelo.versao} · atualiza a cada 5 s
          </Text>
        </div>
        {a.pendentes_aprovacao > 0 && (
          <Anchor component={Link} to="/gestor/aprovacoes">
            <Badge color="orange" size="lg">{a.pendentes_aprovacao} acordo(s) aguardando aprovação</Badge>
          </Anchor>
        )}
      </Group>

      <Text fw={600}>Aderência dos advogados</Text>
      <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} spacing="xs">
        <Stat rotulo="Decisões" valor={num(a.total)} detalhe={`${pct(a.pct_acordo)} acordos`} />
        <Stat rotulo="Aderência" valor={pct(a.pct_aderente)} cor={(a.pct_aderente ?? 0) >= 0.8 ? "teal" : "orange"} detalhe={`${num(a.aderentes)} aderentes`} />
        <Stat rotulo="Desvio de tipo" valor={pct(a.pct_desvio_tipo)} detalhe="acordo↔defesa" />
        <Stat rotulo="Desvio de valor" valor={pct(a.pct_desvio_valor)} detalhe="fora da banda" />
        <Stat rotulo="Tempo médio" valor={duracao(a.tempo_medio_s)} detalhe="por caso" />
        <Stat rotulo="Decidiu sem ver" valor={pct(a.pct_sem_ver_recomendacao)} detalhe="a recomendação" cor="red" />
      </SimpleGrid>

      <Text fw={600}>Efetividade da política</Text>
      <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} spacing="xs">
        <Stat rotulo="Aceite real" valor={pct(e.taxa_aceite_real)} detalhe={`hipótese ${pct(e.taxa_aceite_esperada)}`}
          cor={e.taxa_aceite_real != null && e.taxa_aceite_esperada != null && e.taxa_aceite_real >= e.taxa_aceite_esperada ? "teal" : "orange"} />
        <Stat rotulo="Desconto real" valor={pct(e.desconto_real)} detalhe="valor final / sugerido" />
        <Stat rotulo="Ticket médio" valor={brl(e.ticket_medio_final)} detalhe={`${num(e.n_com_resultado)} negociações`} />
        <Stat rotulo="Economia realizada" valor={brlCompacto(e.economia_realizada)} detalhe={`esperada ${brlCompacto(e.economia_esperada)}`} cor="teal" />
        <Stat rotulo="Backtest (60k)" valor={bt ? pct(bt.economia_vs_defender.pct) : "—"} detalhe={bt ? `vs defender tudo · ${pct(bt.pct_acordo)} acordo` : "sem histórico"} />
        <Stat rotulo="Modelo" valor={e.modelo.versao} detalhe={`${num(e.modelo.n_treino)} casos`} />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Card withBorder radius="md">
          <Text fw={600} mb="xs">Por escritório</Text>
          <Table striped verticalSpacing={4} fz="sm">
            <Table.Thead><Table.Tr><Table.Th>Escritório</Table.Th><Table.Th>Decisões</Table.Th><Table.Th>Aderência</Table.Th><Table.Th>Acordo</Table.Th><Table.Th>Tempo</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {a.por_escritorio.map((l) => (
                <Table.Tr key={String(l.escritorio)}>
                  <Table.Td>{String(l.escritorio)}</Table.Td><Table.Td>{num(l.total)}</Table.Td>
                  <Table.Td>{pct(l.pct_aderente)}</Table.Td><Table.Td>{pct(l.pct_acordo)}</Table.Td><Table.Td>{duracao(l.tempo_medio_s)}</Table.Td>
                </Table.Tr>
              ))}
              {a.por_escritorio.length === 0 && <Table.Tr><Table.Td colSpan={5}><Text c="dimmed" size="sm">Sem decisões ainda.</Text></Table.Td></Table.Tr>}
            </Table.Tbody>
          </Table>
        </Card>
        <Card withBorder radius="md">
          <Text fw={600} mb="xs">Por advogado</Text>
          <Table striped verticalSpacing={4} fz="sm">
            <Table.Thead><Table.Tr><Table.Th>Advogado</Table.Th><Table.Th>Decisões</Table.Th><Table.Th>Aderência</Table.Th><Table.Th>Tempo</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {a.por_advogado.map((l) => (
                <Table.Tr key={`${l.advogado}-${l.escritorio}`}>
                  <Table.Td>{String(l.advogado)} <Text span size="xs" c="dimmed">{String(l.escritorio)}</Text></Table.Td>
                  <Table.Td>{num(l.total)}</Table.Td><Table.Td>{pct(l.pct_aderente)}</Table.Td><Table.Td>{duracao(l.tempo_medio_s)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      </SimpleGrid>

      <Card withBorder radius="md">
        <Text fw={600} mb="xs">Últimos desvios justificados</Text>
        <Table.ScrollContainer minWidth={700}>
          <Table striped verticalSpacing={4} fz="sm">
            <Table.Thead><Table.Tr><Table.Th>Quando</Table.Th><Table.Th>Processo</Table.Th><Table.Th>Advogado</Table.Th><Table.Th>Recomendado</Table.Th><Table.Th>Decidiu</Table.Th><Table.Th>Justificativa</Table.Th><Table.Th>Situação</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {a.justificativas.map((j) => (
                <Table.Tr key={j.decisao_id}>
                  <Table.Td>{dataHora(j.created_at)}</Table.Td>
                  <Table.Td><Anchor component={Link} to={`/casos/${j.processo_id}`} size="sm">{j.numero}</Anchor></Table.Td>
                  <Table.Td>{j.advogado} <Text span size="xs" c="dimmed">{j.escritorio}</Text></Table.Td>
                  <Table.Td><TipoBadge tipo={j.rec_tipo} size="xs" /> {j.valor_sugerido != null && <Text span size="xs">{brl(j.valor_sugerido)}</Text>}</Table.Td>
                  <Table.Td><TipoBadge tipo={j.tipo} size="xs" /> {j.valor_proposto != null && <Text span size="xs">{brl(j.valor_proposto)}</Text>}</Table.Td>
                  <Table.Td><Text size="xs" lineClamp={2}>{j.justificativa}</Text></Table.Td>
                  <Table.Td><StatusBadge status={j.status} /></Table.Td>
                </Table.Tr>
              ))}
              {a.justificativas.length === 0 && <Table.Tr><Table.Td colSpan={7}><Text c="dimmed" size="sm">Nenhum desvio registrado.</Text></Table.Td></Table.Tr>}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Card withBorder radius="md">
          <Text fw={600} mb="xs">Aderência por semana</Text>
          <Table verticalSpacing={2} fz="sm">
            <Table.Tbody>
              {a.por_semana.map((l) => (
                <Table.Tr key={String(l.semana)}><Table.Td>{String(l.semana)}</Table.Td><Table.Td>{num(l.total)} decisões</Table.Td><Table.Td>{pct(l.pct_aderente)}</Table.Td></Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
        <Card withBorder radius="md">
          <Text fw={600} mb="xs">Resultados das negociações</Text>
          <Table verticalSpacing={2} fz="sm">
            <Table.Tbody>
              {Object.entries(e.por_resultado).map(([k, v]) => (
                <Table.Tr key={k}><Table.Td>{k.replaceAll("_", " ")}</Table.Td><Table.Td>{num(v)}</Table.Td></Table.Tr>
              ))}
              <Table.Tr><Table.Td><Text size="xs" c="dimmed">sem resultado ainda</Text></Table.Td><Table.Td>{num(e.n_decisoes - Object.values(e.por_resultado).reduce((s, v) => s + v, 0))}</Table.Td></Table.Tr>
            </Table.Tbody>
          </Table>
          <Text size="xs" c="dimmed" mt="xs">Gráficos ficam a cargo de P5; aqui só os números do endpoint.</Text>
        </Card>
      </SimpleGrid>
    </Stack>
  );
}
