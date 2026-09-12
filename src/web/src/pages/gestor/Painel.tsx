import {
  Alert, Anchor, Badge, Box, Button, Card, Collapse, Divider, Grid, Group, Paper, Progress, SimpleGrid,
  Skeleton, Stack, Table, Text, ThemeIcon, Title,
} from "@mantine/core";
import { BarChart, DonutChart, LineChart } from "@mantine/charts";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";

import { api, type Justificativa, type ParecerIA } from "../../api/client";
import { StatusBadge, TipoBadge } from "../../components/Badges";
import { IcoCheck, IcoSeta } from "../../components/Icones";
import { brl, brlCompacto, dataHora, duracao, num, pct } from "../../lib/format";

const POLL = 5000;

export default function Painel() {
  const ader = useQuery({ queryKey: ["aderencia"], queryFn: () => api.aderencia(), refetchInterval: POLL });
  const efet = useQuery({ queryKey: ["efetividade"], queryFn: () => api.efetividade(), refetchInterval: POLL });

  if (ader.isLoading || efet.isLoading) return <Carregando />;
  if (ader.error || efet.error) {
    return <Alert color="vermelho" variant="light">{((ader.error ?? efet.error) as Error).message}</Alert>;
  }

  const a = ader.data!;
  const e = efet.data!;
  const potencial = e.backtest_potencial;

  return (
    <Stack gap={32}>
      <Group justify="space-between" align="end" wrap="wrap" gap="md">
        <div>
          <Text size="xs" fw={600} tt="uppercase" lts=".1em" c="laranja.8">Monitoramento</Text>
          <Title order={1} className="serif" fw={500}>Política de acordos</Title>
          <Text c="dimmed" size="sm" mt={4}>
            {e.politica ? `Política ativa v${e.politica.versao} · ${e.politica.nome}` : "Nenhuma política ativa"}
          </Text>
        </div>
        <Group gap="sm">
          <Group gap={6}>
            <Box w={8} h={8} bg="verde.6" style={{ borderRadius: 999 }} className="pulsar" />
            <Text size="xs" c="dimmed">ao vivo</Text>
          </Group>
          {a.pendentes_aprovacao > 0 && (
            <Button component={Link} to="/gestor/aprovacoes" color="laranja" variant="light" size="sm">
              {num(a.pendentes_aprovacao)} pendente(s)
            </Button>
          )}
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <RespostaAderencia total={a.total} percentual={a.pct_aderente} />
        <RespostaEconomia potencial={potencial} />
      </SimpleGrid>

      <Secao numero="01" titulo="A política está sendo seguida?" subtitulo="Aderência">
        <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
          <GraficoEscritorios linhas={a.por_escritorio} />
          <GraficoTendencia aderencia={a.por_semana} efetividade={e.por_semana} />
        </SimpleGrid>
        <FilaDesvios justificativas={a.justificativas} />
        <DetalhesAderencia a={a} />
      </Secao>

      <Secao numero="02" titulo="A política está gerando resultado?" subtitulo="Efetividade">
        <Grid gutter="md">
          <Grid.Col span={{ base: 12, lg: 7 }}><Potencial potencial={potencial} /></Grid.Col>
          <Grid.Col span={{ base: 12, lg: 5 }}><Operacao e={e} /></Grid.Col>
        </Grid>
      </Secao>
    </Stack>
  );
}

function RespostaAderencia({ total, percentual }: { total: number; percentual: number | null }) {
  const valor = percentual ?? 0;
  return (
    <Card p="xl" style={{ borderTop: "3px solid var(--enter-tinta)" }}>
      <Text size="xs" fw={600} tt="uppercase" lts=".08em" c="dimmed">Aderência operacional</Text>
      <Group justify="space-between" align="end" mt="lg" wrap="nowrap">
        <div>
          <Text className="serif numero" fz={{ base: 44, sm: 58 }} lh={0.9}>{percentual == null ? "—" : pct(percentual)}</Text>
          <Text size="sm" c="dimmed" mt="sm">{num(total)} decisões registradas</Text>
        </div>
        <Badge color={valor >= 0.8 ? "verde" : "laranja"} variant="light" size="lg">
          {percentual == null ? "sem dados" : valor >= 0.8 ? "saudável" : "atenção"}
        </Badge>
      </Group>
      <Progress value={valor * 100} color={valor >= 0.8 ? "verde" : "laranja"} mt="xl" size="sm" radius="xl" />
    </Card>
  );
}

function RespostaEconomia({ potencial }: { potencial: ReturnTypePotencial }) {
  return (
    <Card p="xl" bg="tinta.6" c="white">
      <Text size="xs" fw={600} tt="uppercase" lts=".08em" c="rgba(255,255,255,.62)">Economia potencial</Text>
      <Group justify="space-between" align="end" mt="lg" wrap="nowrap">
        <div>
          <Text className="serif numero" fz={{ base: 44, sm: 58 }} lh={0.9}>
            {potencial ? pct(potencial.economia_pct) : "—"}
          </Text>
          <Text size="sm" c="rgba(255,255,255,.64)" mt="sm">
            {potencial ? `${brlCompacto(potencial.economia_vs_defender)} vs defender tudo` : "backtest indisponível"}
          </Text>
        </div>
        {potencial && <Badge color="laranja" variant="filled" size="lg">{num(potencial.n_casos)} casos</Badge>}
      </Group>
      <Text size="xs" c="rgba(255,255,255,.5)" mt="xl">
        Simulação histórica com resultados judiciais reais e premissas declaradas.
      </Text>
    </Card>
  );
}

type ReturnTypePotencial = Awaited<ReturnType<typeof api.efetividade>>["backtest_potencial"];
type LinhaGrupo = { [k: string]: unknown; total?: number; pct_aderente?: number; taxa_aceite?: number };

function Secao({ numero, titulo, subtitulo, children }: {
  numero: string; titulo: string; subtitulo: string; children: React.ReactNode;
}) {
  return (
    <Stack gap="md">
      <Group gap="md" align="start">
        <Text className="serif numero" fz="xl" c="laranja.8">{numero}</Text>
        <div>
          <Text size="xs" fw={600} tt="uppercase" lts=".08em" c="dimmed">{subtitulo}</Text>
          <Text className="serif" fz={{ base: 24, sm: 30 }} lh={1.1}>{titulo}</Text>
        </div>
      </Group>
      {children}
    </Stack>
  );
}

function GraficoEscritorios({ linhas }: { linhas: LinhaGrupo[] }) {
  const dados = linhas
    .map((l) => ({ escritorio: String(l.escritorio), aderencia: Number(l.pct_aderente) * 100, decisoes: l.total }))
    .sort((x, y) => x.aderencia - y.aderencia);
  return (
    <Card>
      <CabecalhoCard titulo="Aderência por escritório" detalhe="Pior desempenho primeiro" />
      {dados.length ? (
        <BarChart h={230} data={dados} dataKey="escritorio" orientation="vertical"
          series={[{ name: "aderencia", label: "Aderência", color: "laranja.6" }]}
          valueFormatter={(v) => `${Number(v).toFixed(0)}%`} gridAxis="x" xAxisProps={{ domain: [0, 100] }} />
      ) : <Vazio texto="As bancas aparecem depois da primeira decisão." />}
    </Card>
  );
}

function GraficoTendencia({ aderencia, efetividade }: { aderencia: LinhaGrupo[]; efetividade: LinhaGrupo[] }) {
  const aceite = new Map(efetividade.map((l) => [String(l.semana), Number(l.taxa_aceite) * 100]));
  const dados = aderencia.map((l) => ({
    semana: String(l.semana).slice(5),
    aderencia: Number(l.pct_aderente) * 100,
    aceite: aceite.get(String(l.semana)),
  }));
  return (
    <Card>
      <CabecalhoCard titulo="Evolução semanal" detalhe="Aderência e aceite real" />
      {dados.length ? (
        <LineChart h={230} data={dados} dataKey="semana" curveType="monotone"
          series={[
            { name: "aderencia", label: "Aderência", color: "tinta.6" },
            { name: "aceite", label: "Aceite", color: "laranja.6" },
          ]}
          valueFormatter={(v) => `${Number(v).toFixed(0)}%`} yAxisProps={{ domain: [0, 100] }} />
      ) : <Vazio texto="A evolução aparece conforme as decisões são registradas." />}
    </Card>
  );
}

function FilaDesvios({ justificativas }: { justificativas: Justificativa[] }) {
  const qc = useQueryClient();
  const parecer = useMutation({
    mutationFn: (id: number) => api.gerarParecer(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["aderencia"] }),
    onError: (erro) => notifications.show({ message: (erro as Error).message, color: "vermelho" }),
  });
  return (
    <Card>
      <CabecalhoCard titulo="Desvios que pedem atenção" detalhe="A decisão é objetiva; a IA ajuda a triar a justificativa" />
      <Table.ScrollContainer minWidth={920}>
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead><Table.Tr>
            <Th>Processo</Th><Th>Advogado</Th><Th>Recomendado</Th><Th>Decidiu</Th><Th>Justificativa</Th><Th>Análise assistida</Th><Th>Situação</Th>
          </Table.Tr></Table.Thead>
          <Table.Tbody>
            {justificativas.slice(0, 10).map((j) => (
              <Table.Tr key={j.decisao_id}>
                <Table.Td>
                  <Anchor component={Link} to={`/casos/${j.processo_id}`} c="tinta.6" fw={600} size="sm" className="numero">{j.numero}</Anchor>
                  <Text size="xs" c="dimmed">{dataHora(j.created_at)}</Text>
                </Table.Td>
                <Table.Td><Text size="sm">{j.advogado}</Text><Text size="xs" c="dimmed">{j.escritorio}</Text></Table.Td>
                <Table.Td><Decisao tipo={j.rec_tipo} valor={j.valor_sugerido} /></Table.Td>
                <Table.Td><Decisao tipo={j.tipo} valor={j.valor_proposto} /></Table.Td>
                <Table.Td><Text size="xs" maw={250} lineClamp={3}>{j.justificativa}</Text></Table.Td>
                <Table.Td>
                  {j.parecer_ia
                    ? <Parecer parecer={j.parecer_ia} />
                    : <Button size="compact-xs" variant="light" color="tinta" loading={parecer.isPending && parecer.variables === j.decisao_id}
                        onClick={() => parecer.mutate(j.decisao_id)}>Analisar com IA</Button>}
                </Table.Td>
                <Table.Td><StatusBadge status={j.status} size="sm" /></Table.Td>
              </Table.Tr>
            ))}
            {!justificativas.length && <Table.Tr><Table.Td colSpan={7}><Vazio texto="Nenhum desvio registrado." /></Table.Td></Table.Tr>}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Card>
  );
}

function Parecer({ parecer }: { parecer: ParecerIA }) {
  const cores = { fundamentada: "verde", generica: "laranja", contradiz_evidencias: "vermelho" };
  const nomes = { fundamentada: "Fundamentada", generica: "Genérica", contradiz_evidencias: "Contradiz evidências" };
  return (
    <Stack gap={3} maw={220}>
      <Badge size="xs" variant="light" color={cores[parecer.classificacao]}>{nomes[parecer.classificacao]}</Badge>
      <Text size="xs" lineClamp={3}>{parecer.resumo}</Text>
      <Text size="10px" c="dimmed">IA · confiança {pct(parecer.confianca)}</Text>
    </Stack>
  );
}

function Decisao({ tipo, valor }: { tipo: string; valor: number | null }) {
  return <Stack gap={2}><TipoBadge tipo={tipo} size="xs" />{valor != null && <Text size="xs" className="numero">{brl(valor)}</Text>}</Stack>;
}

function DetalhesAderencia({ a }: { a: Awaited<ReturnType<typeof api.aderencia>> }) {
  const [aberto, { toggle }] = useDisclosure(false);
  return (
    <Paper withBorder p="md">
      <Group justify="space-between">
        <Text size="sm" fw={500}>Detalhes operacionais</Text>
        <Button variant="subtle" color="tinta" size="compact-sm" onClick={toggle} rightSection={<IcoSeta size={14} />}>
          {aberto ? "Ocultar" : "Ver detalhes"}
        </Button>
      </Group>
      <Collapse in={aberto}>
        <SimpleGrid cols={{ base: 2, sm: 4 }} mt="md">
          <Mini rotulo="Desvio de tipo" valor={pct(a.pct_desvio_tipo)} />
          <Mini rotulo="Desvio de valor" valor={pct(a.pct_desvio_valor)} />
          <Mini rotulo="Tempo médio" valor={duracao(a.tempo_medio_s)} />
          <Mini rotulo="Sem ver recomendação" valor={pct(a.pct_sem_ver_recomendacao)} />
        </SimpleGrid>
      </Collapse>
    </Paper>
  );
}

function Potencial({ potencial }: { potencial: ReturnTypePotencial }) {
  if (!potencial) return <Card><Vazio texto="Backtest do engine indisponível." /></Card>;
  const dados = [
    { cenario: "Defender tudo", custo: potencial.defender_tudo },
    { cenario: "Acordar tudo", custo: potencial.acordar_tudo },
    { cenario: "Nossa política", custo: potencial.politica },
  ];
  return (
    <Card h="100%">
      <Group justify="space-between" align="start">
        <CabecalhoCard titulo="Potencial nos 60 mil casos" detalhe="Replay histórico · não é resultado operacional" />
        <Button component={Link} to="/gestor/politica" variant="subtle" color="tinta" size="compact-sm">Ver política</Button>
      </Group>
      <SimpleGrid cols={{ base: 1, sm: 3 }} my="md">
        {dados.map((d) => <Mini key={d.cenario} rotulo={d.cenario} valor={brlCompacto(d.custo)}
          destaque={d.cenario === "Nossa política"} />)}
      </SimpleGrid>
      <BarChart h={210} data={dados} dataKey="cenario"
        series={[{ name: "custo", label: "Custo total", color: "laranja.6" }]}
        valueFormatter={(v) => brlCompacto(Number(v))} gridAxis="y" />
      <Divider my="md" />
      <Group justify="space-between" gap="md">
        <div><Text size="xs" c="dimmed">Economia vs defender tudo</Text><Text className="serif numero" fz="xl">{brlCompacto(potencial.economia_vs_defender)} · {pct(potencial.economia_pct)}</Text></div>
        <div><Text size="xs" c="dimmed">Casos em acordo</Text><Text className="serif numero" fz="xl">{pct(potencial.pct_acordo)}</Text></div>
      </Group>
      <Text size="10px" c="dimmed" mt="md">
        Política {potencial.politica_versao} · modelo {potencial.modelo_versao} · defesa usa desfechos reais; acordos usam curva estimada de aceite.
      </Text>
    </Card>
  );
}

function Operacao({ e }: { e: Awaited<ReturnType<typeof api.efetividade>> }) {
  const resultados = [
    { name: "Aceito", value: e.por_resultado.aceito ?? 0, color: "verde.6" },
    { name: "Contraproposta", value: e.por_resultado.contraproposta_aceita ?? 0, color: "laranja.6" },
    { name: "Recusado", value: e.por_resultado.recusado ?? 0, color: "vermelho.6" },
    { name: "Sem resposta", value: e.por_resultado.sem_resposta ?? 0, color: "gray.4" },
  ].filter((r) => r.value > 0);
  return (
    <Card h="100%">
      <CabecalhoCard titulo="Resultado operacional" detalhe="Somente negociações registradas no portal" />
      <Group justify="space-between" align="end" mt="lg">
        <div>
          <Text size="xs" c="dimmed">Taxa de aceite real</Text>
          <Text className="serif numero" fz={38} lh={1}>{pct(e.taxa_aceite_real)}</Text>
          <Text size="xs" c="dimmed" mt={4}>hipótese da política {pct(e.taxa_aceite_esperada)}</Text>
        </div>
        {e.taxa_aceite_preliminar && <Badge color="laranja" variant="light">preliminar</Badge>}
      </Group>
      <Box my="lg">
        <Group justify="space-between" mb={6}>
          <Text size="xs" c="dimmed">Cobertura dos resultados</Text>
          <Text size="xs" fw={600} className="numero">{pct(e.cobertura_resultados)}</Text>
        </Group>
        <Progress value={(e.cobertura_resultados ?? 0) * 100} color="tinta" size="sm" />
        <Text size="10px" c="dimmed" mt={4}>{num(e.n_com_resultado)} concluídos · {num(e.n_sem_resultado)} aguardando desfecho</Text>
      </Box>
      {resultados.length ? (
        <Group justify="center" gap="xl">
          <DonutChart data={resultados} size={142} thickness={18} withTooltip />
          <Stack gap={5}>
            {resultados.map((r) => <Group key={r.name} gap={6}><Box w={8} h={8} bg={r.color} style={{ borderRadius: 2 }} /><Text size="xs">{r.name}</Text><Text size="xs" fw={600} className="numero">{num(r.value)}</Text></Group>)}
          </Stack>
        </Group>
      ) : <Vazio texto="Nenhuma negociação concluída." />}
      <Paper p="sm" mt="lg" bg="gray.0">
        <Text size="xs" c="dimmed">Economia estimada nos acordos concluídos</Text>
        <Text className="serif numero" fz="xl">{brlCompacto(e.economia_realizada)}</Text>
      </Paper>
    </Card>
  );
}

function CabecalhoCard({ titulo, detalhe }: { titulo: string; detalhe: string }) {
  return <div><Text fw={600}>{titulo}</Text><Text size="xs" c="dimmed">{detalhe}</Text></div>;
}

function Mini({ rotulo, valor, destaque }: { rotulo: string; valor: string; destaque?: boolean }) {
  return (
    <Paper p="sm" bg={destaque ? "laranja.1" : "gray.0"} style={destaque ? { border: "1px solid var(--enter-laranja)" } : undefined}>
      <Text size="xs" c="dimmed">{rotulo}</Text>
      <Text className="serif numero" fz="lg" fw={500}>{valor}</Text>
    </Paper>
  );
}

function Th({ children }: { children: string }) {
  return <Table.Th><Text size="xs" fw={600} tt="uppercase" lts=".06em" c="dimmed">{children}</Text></Table.Th>;
}

function Vazio({ texto }: { texto: string }) {
  return (
    <Stack align="center" justify="center" mih={130} gap="xs">
      <ThemeIcon color="gray" variant="light" radius="xl"><IcoCheck size={14} /></ThemeIcon>
      <Text size="sm" c="dimmed" ta="center">{texto}</Text>
    </Stack>
  );
}

function Carregando() {
  return (
    <Stack gap="xl">
      <Skeleton height={58} width={360} radius="sm" />
      <SimpleGrid cols={{ base: 1, md: 2 }}><Skeleton height={210} radius={12} /><Skeleton height={210} radius={12} /></SimpleGrid>
      <SimpleGrid cols={{ base: 1, md: 2 }}><Skeleton height={310} radius={12} /><Skeleton height={310} radius={12} /></SimpleGrid>
    </Stack>
  );
}
