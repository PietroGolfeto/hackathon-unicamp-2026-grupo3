import { Alert, Anchor, Box, Button, Card, Group, Progress, SimpleGrid, Skeleton, Stack, Table, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Link } from "react-router";

import { api } from "../../api/client";
import { StatusBadge, TipoBadge } from "../../components/Badges";
import { Stat } from "../../components/Stat";
import { ROTULO_RESULTADO, brl, brlCompacto, dataHora, duracao, num, pct } from "../../lib/format";

const POLL = 5000;

export default function Painel() {
  const ader = useQuery({ queryKey: ["aderencia"], queryFn: () => api.aderencia(), refetchInterval: POLL });
  const efet = useQuery({ queryKey: ["efetividade"], queryFn: () => api.efetividade(), refetchInterval: POLL });
  if (ader.isLoading || efet.isLoading) return <Carregando />;
  if (ader.error || efet.error) return <Alert color="vermelho" variant="light">{((ader.error ?? efet.error) as Error).message}</Alert>;
  const a = ader.data!;
  const e = efet.data!;
  const bt = e.politica?.resumo_backtest;
  const semResultado = e.n_decisoes - Object.values(e.por_resultado).reduce((s, v) => s + v, 0);

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="end" wrap="wrap" gap="md">
        <div>
          <Title order={2}>Painel do gestor</Title>
          <Text c="dimmed" size="sm" mt={4}>
            Política ativa v{e.politica?.versao} · {e.politica?.nome} · modelo <Text span ff="monospace" size="xs">{e.modelo.versao}</Text>
          </Text>
        </div>
        <Group gap="md" wrap="wrap">
          <Group gap={6}>
            <Box w={8} h={8} bg="verde.6" style={{ borderRadius: 999 }} className="pulsar" />
            <Text size="xs" c="dimmed">ao vivo · a cada 5 s</Text>
          </Group>
          {a.pendentes_aprovacao > 0 && (
            <Button component={Link} to="/gestor/aprovacoes" color="laranja" size="sm">
              {num(a.pendentes_aprovacao)} acordo(s) aguardando aprovação
            </Button>
          )}
        </Group>
      </Group>

      <Secao titulo="Aderência dos advogados" descricao="Cada decisão é comparada com a recomendação que o advogado viu ao abrir o caso.">
        <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} spacing="sm" className="escalonado">
          <Stat rotulo="Decisões" numero={a.total} formatar={num} detalhe={a.pct_acordo != null ? `${pct(a.pct_acordo)} acordos` : "nenhuma ainda"} />
          <Stat rotulo="Aderência" numero={a.pct_aderente} formatar={(n) => pct(n)} detalhe={`${num(a.aderentes)} aderentes`}
            cor={(a.pct_aderente ?? 0) >= 0.8 ? "verde.7" : "laranja.8"} />
          <Stat rotulo="Desvio de tipo" numero={a.pct_desvio_tipo} formatar={(n) => pct(n)} detalhe="acordo ↔ defesa" />
          <Stat rotulo="Desvio de valor" numero={a.pct_desvio_valor} formatar={(n) => pct(n)} detalhe="fora da banda" />
          <Stat rotulo="Tempo médio" numero={a.tempo_medio_s} formatar={duracao} detalhe="por caso" />
          <Stat rotulo="Decidiu sem ver" numero={a.pct_sem_ver_recomendacao} formatar={(n) => pct(n)} detalhe="a recomendação"
            cor={(a.pct_sem_ver_recomendacao ?? 0) > 0 ? "vermelho.6" : "verde.7"} />
        </SimpleGrid>
      </Secao>

      <Secao titulo="Efetividade da política" descricao="Resultado real das negociações registradas e o backtest da política ativa sobre os 60 mil casos.">
        <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} spacing="sm" className="escalonado">
          <Stat rotulo="Backtest (60k)" destaque numero={bt ? bt.economia_vs_defender.pct : null} formatar={(n) => pct(n)}
            detalhe={bt ? `economia vs defender tudo · ${pct(bt.pct_acordo)} acordo` : "sem histórico carregado"} />
          <Stat rotulo="Aceite real" numero={e.taxa_aceite_real} formatar={(n) => pct(n)} detalhe={`hipótese ${pct(e.taxa_aceite_esperada)}`}
            cor={e.taxa_aceite_real != null && e.taxa_aceite_esperada != null && e.taxa_aceite_real >= e.taxa_aceite_esperada ? "verde.7" : "laranja.8"} />
          <Stat rotulo="Desconto real" numero={e.desconto_real} formatar={(n) => pct(n)} detalhe="valor final / sugerido" />
          <Stat rotulo="Ticket médio" numero={e.ticket_medio_final} formatar={brl} detalhe={`${num(e.n_com_resultado)} negociações`} />
          <Stat rotulo="Economia realizada" numero={e.economia_realizada} formatar={brlCompacto} detalhe={`esperada ${brlCompacto(e.economia_esperada)}`} cor="verde.7" />
          <Stat rotulo="Modelo" valor={<Text ff="monospace" fz="sm" fw={500} style={{ wordBreak: "break-all" }}>{e.modelo.versao}</Text>}
            detalhe={`${num(e.modelo.n_treino)} casos de treino`} />
        </SimpleGrid>
      </Secao>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Bloco titulo="Por escritório" descricao="Aderência e perfil de decisão de cada banca.">
          <Table verticalSpacing={6} fz="sm">
            <Table.Thead><Table.Tr><Th>Escritório</Th><Th>Decisões</Th><Th>Aderência</Th><Th>Acordo</Th><Th>Tempo</Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {a.por_escritorio.map((l) => (
                <Table.Tr key={String(l.escritorio)}>
                  <Table.Td>{String(l.escritorio)}</Table.Td>
                  <Table.Td className="numero">{num(l.total)}</Table.Td>
                  <Table.Td><Aderencia valor={l.pct_aderente} /></Table.Td>
                  <Table.Td className="numero">{pct(l.pct_acordo)}</Table.Td>
                  <Table.Td className="numero">{duracao(l.tempo_medio_s)}</Table.Td>
                </Table.Tr>
              ))}
              {a.por_escritorio.length === 0 && <Vazio colunas={5} texto="Sem decisões ainda." />}
            </Table.Tbody>
          </Table>
        </Bloco>
        <Bloco titulo="Por advogado" descricao="Quem segue a política e quem desvia.">
          <Table verticalSpacing={6} fz="sm">
            <Table.Thead><Table.Tr><Th>Advogado</Th><Th>Decisões</Th><Th>Aderência</Th><Th>Tempo</Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {a.por_advogado.map((l) => (
                <Table.Tr key={`${l.advogado}-${l.escritorio}`}>
                  <Table.Td>{String(l.advogado)} <Text span size="xs" c="dimmed">{String(l.escritorio)}</Text></Table.Td>
                  <Table.Td className="numero">{num(l.total)}</Table.Td>
                  <Table.Td><Aderencia valor={l.pct_aderente} /></Table.Td>
                  <Table.Td className="numero">{duracao(l.tempo_medio_s)}</Table.Td>
                </Table.Tr>
              ))}
              {a.por_advogado.length === 0 && <Vazio colunas={4} texto="Sem decisões ainda." />}
            </Table.Tbody>
          </Table>
        </Bloco>
      </SimpleGrid>

      <Bloco titulo="Últimos desvios justificados" descricao="Decisões que divergiram da recomendação e o que o advogado escreveu.">
        <Table.ScrollContainer minWidth={720}>
          <Table verticalSpacing={6} fz="sm">
            <Table.Thead><Table.Tr><Th>Quando</Th><Th>Processo</Th><Th>Advogado</Th><Th>Recomendado</Th><Th>Decidiu</Th><Th>Justificativa</Th><Th>Situação</Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {a.justificativas.map((j) => (
                <Table.Tr key={j.decisao_id}>
                  <Table.Td><Text size="xs" c="dimmed" className="numero">{dataHora(j.created_at)}</Text></Table.Td>
                  <Table.Td><Anchor component={Link} to={`/casos/${j.processo_id}`} size="sm" fw={500} c="tinta.6" className="numero">{j.numero}</Anchor></Table.Td>
                  <Table.Td>{j.advogado} <Text span size="xs" c="dimmed">{j.escritorio}</Text></Table.Td>
                  <Table.Td><TipoBadge tipo={j.rec_tipo} size="xs" /> {j.valor_sugerido != null && <Text span size="xs" className="numero">{brl(j.valor_sugerido)}</Text>}</Table.Td>
                  <Table.Td><TipoBadge tipo={j.tipo} size="xs" /> {j.valor_proposto != null && <Text span size="xs" className="numero">{brl(j.valor_proposto)}</Text>}</Table.Td>
                  <Table.Td><Text size="xs" lineClamp={2} maw={320}>{j.justificativa}</Text></Table.Td>
                  <Table.Td><StatusBadge status={j.status} size="sm" /></Table.Td>
                </Table.Tr>
              ))}
              {a.justificativas.length === 0 && <Vazio colunas={7} texto="Nenhum desvio registrado." />}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Bloco>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Bloco titulo="Aderência por semana" descricao="Evolução desde a publicação da política.">
          <Table verticalSpacing={4} fz="sm">
            <Table.Tbody>
              {a.por_semana.map((l) => (
                <Table.Tr key={String(l.semana)}>
                  <Table.Td className="numero">{String(l.semana)}</Table.Td>
                  <Table.Td className="numero">{num(l.total)} decisões</Table.Td>
                  <Table.Td><Aderencia valor={l.pct_aderente} /></Table.Td>
                </Table.Tr>
              ))}
              {a.por_semana.length === 0 && <Vazio colunas={3} texto="Sem decisões ainda." />}
            </Table.Tbody>
          </Table>
        </Bloco>
        <Bloco titulo="Resultados das negociações" descricao="O que a parte respondeu às propostas.">
          <Table verticalSpacing={4} fz="sm">
            <Table.Tbody>
              {Object.entries(e.por_resultado).map(([k, v]) => (
                <Table.Tr key={k}><Table.Td>{ROTULO_RESULTADO[k] ?? k.replaceAll("_", " ")}</Table.Td><Table.Td className="numero" ta="right">{num(v)}</Table.Td></Table.Tr>
              ))}
              <Table.Tr>
                <Table.Td><Text size="sm" c="dimmed">sem resultado ainda</Text></Table.Td>
                <Table.Td className="numero" ta="right"><Text size="sm" c="dimmed">{num(semResultado)}</Text></Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>
        </Bloco>
      </SimpleGrid>
    </Stack>
  );
}

function Secao({ titulo, descricao, children }: { titulo: string; descricao?: string; children: ReactNode }) {
  return (
    <Stack gap="sm">
      <div>
        <Text className="serif" fz="xl">{titulo}</Text>
        {descricao && <Text size="xs" c="dimmed">{descricao}</Text>}
      </div>
      {children}
    </Stack>
  );
}

function Bloco({ titulo, descricao, children }: { titulo: string; descricao?: string; children: ReactNode }) {
  return (
    <Card>
      <Text fw={500}>{titulo}</Text>
      {descricao && <Text size="xs" c="dimmed" mb="sm">{descricao}</Text>}
      {children}
    </Card>
  );
}

function Th({ children }: { children: string }) {
  return <Table.Th><Text size="xs" fw={500} tt="uppercase" lts=".06em" c="dimmed">{children}</Text></Table.Th>;
}

function Vazio({ colunas, texto }: { colunas: number; texto: string }) {
  return <Table.Tr><Table.Td colSpan={colunas}><Text c="dimmed" size="sm" ta="center" py="sm">{texto}</Text></Table.Td></Table.Tr>;
}

/** Percentual com uma barra curta ao lado: verde a partir de 80%, laranja abaixo. */
function Aderencia({ valor }: { valor: number | null | undefined }) {
  if (valor == null) return <Text size="sm" c="dimmed">—</Text>;
  return (
    <Group gap={8} wrap="nowrap">
      <Progress value={valor * 100} color={valor >= 0.8 ? "verde" : "laranja"} size="sm" w={64} radius="xl" transitionDuration={600} />
      <Text size="sm" className="numero">{pct(valor)}</Text>
    </Group>
  );
}

function Carregando() {
  return (
    <Stack gap="xl">
      <Skeleton height={44} width={320} radius="sm" />
      <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} spacing="sm">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={96} radius={12} />)}</SimpleGrid>
      <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} spacing="sm">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={96} radius={12} />)}</SimpleGrid>
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md"><Skeleton height={180} radius={12} /><Skeleton height={180} radius={12} /></SimpleGrid>
    </Stack>
  );
}
