import {
  Alert, Anchor, Badge, Box, Button, Card, Divider, Grid, Group, Paper, Progress, SimpleGrid,
  Skeleton, Stack, Table, Text, ThemeIcon, Title, Tooltip,
} from "@mantine/core";
import { AreaChart, DonutChart } from "@mantine/charts";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";

import { api, type Justificativa } from "../../api/client";
import { StatusBadge, TipoBadge } from "../../components/Badges";
import { IcoBaixo, IcoCheck } from "../../components/Icones";
import { useContagem, useMontado } from "../../lib/animacao";
import { brl, brlCompacto, dataHora, num, pct } from "../../lib/format";

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
          <Title order={1} className="serif">Política de acordos</Title>
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

      <ResumoExecutivo a={a} potencial={potencial} />

      <Secao numero="01" titulo="A política está sendo seguida?" subtitulo="Aderência">
        <PainelAderencia a={a} />
        <FilaDesvios justificativas={a.justificativas} />
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

function ResumoExecutivo({ a, potencial }: {
  a: Awaited<ReturnType<typeof api.aderencia>>;
  potencial: ReturnTypePotencial;
}) {
  const economia = useContagem(potencial?.economia_vs_defender);
  const economiaPct = useContagem(potencial?.economia_pct);
  const acordos = useContagem(potencial?.pct_acordo);
  const aderencia = useContagem(a.pct_aderente);

  return (
    <Grid gutter="md" className="escalonado">
      <Grid.Col span={{ base: 12, lg: 7 }}>
        <Card p={{ base: "lg", sm: 32 }} bg="tinta.6" c="white" h="100%" pos="relative" style={{ overflow: "hidden" }}>
          <Box pos="absolute" w={240} h={240} right={-70} top={-110}
            style={{ borderRadius: 999, background: "rgba(255,174,53,.13)" }} />
          <Text size="xs" fw={600} tt="uppercase" lts=".1em" c="laranja.5">Impacto financeiro potencial</Text>
          <Text className="serif numero" fz={{ base: 50, sm: 72 }} lh={0.95} mt="lg">
            {potencial ? brlCompacto(economia) : "—"}
          </Text>
          <Group gap="sm" mt="md">
            <Badge color="laranja" variant="filled" size="lg">{potencial ? `${pct(economiaPct)} de economia` : "backtest indisponível"}</Badge>
            {potencial && <Text size="sm" c="rgba(255,255,255,.68)">em {num(potencial.n_casos)} decisões históricas</Text>}
          </Group>
          <Divider color="rgba(255,255,255,.13)" my="xl" />
          <Group justify="space-between" gap="xl" align="end">
            <div>
              <Text size="xs" c="rgba(255,255,255,.55)">Custo com a política</Text>
              <Text className="serif numero" fz="xl">{potencial ? brlCompacto(potencial.politica) : "—"}</Text>
            </div>
            <div>
              <Text size="xs" c="rgba(255,255,255,.55)">Custo defendendo tudo</Text>
              <Text className="serif numero" fz="xl" c="rgba(255,255,255,.72)">{potencial ? brlCompacto(potencial.defender_tudo) : "—"}</Text>
            </div>
          </Group>
        </Card>
      </Grid.Col>
      <Grid.Col span={{ base: 12, sm: 6, lg: 2.5 }}>
        <Card p="xl" h="100%" style={{ borderTop: "3px solid var(--enter-laranja)" }}>
          <Text size="xs" fw={600} tt="uppercase" lts=".08em" c="dimmed">Casos em acordo</Text>
          <Text className="serif numero" fz={{ base: 44, sm: 52 }} lh={1} mt="xl">
            {potencial ? pct(acordos) : "—"}
          </Text>
          <Text size="sm" c="dimmed" mt="sm">selecionados pela política econômica</Text>
        </Card>
      </Grid.Col>
      <Grid.Col span={{ base: 12, sm: 6, lg: 2.5 }}>
        <Card p="xl" h="100%" style={{ borderTop: "3px solid var(--enter-tinta)" }}>
          <Text size="xs" fw={600} tt="uppercase" lts=".08em" c="dimmed">Aderência agora</Text>
          <Text className="serif numero" fz={{ base: 44, sm: 52 }} lh={1} mt="xl">
            {a.pct_aderente == null ? "—" : pct(aderencia)}
          </Text>
          <Text size="sm" c="dimmed" mt="sm">{num(a.total)} decisões operacionais</Text>
        </Card>
      </Grid.Col>
    </Grid>
  );
}

function PainelAderencia({ a }: { a: Awaited<ReturnType<typeof api.aderencia>> }) {
  const desvios = Math.max(0, a.total - a.aderentes);
  const valor = a.pct_aderente ?? 0;
  const saudavel = valor >= 0.8;
  const tendencia = a.por_semana.map((s) => ({
    semana: rotuloSemana(s.semana ?? ""),
    aderencia: Math.round((s.pct_aderente ?? 0) * 100),
  }));

  return (
    <Card>
      <Group justify="space-between" align="start">
        <CabecalhoCard titulo="Pulso operacional" detalhe="Aderência das decisões registradas no portal" />
        <Badge color={saudavel ? "verde" : "laranja"} variant="light" size="lg">
          {a.pct_aderente == null ? "sem dados" : saudavel ? "saudável" : "atenção"}
        </Badge>
      </Group>
      <Grid gutter="xl" mt="lg" align="center">
        <Grid.Col span={{ base: 12, sm: 4 }}>
          <Text className="serif numero" fz={{ base: 52, sm: 64 }} lh={1} c={saudavel ? "verde.7" : "laranja.7"}>
            {a.pct_aderente == null ? "—" : pct(valor)}
          </Text>
          <Text size="sm" c="dimmed" mt={6}>aderência atual · {num(a.total)} decisões</Text>
          <Group gap="xl" mt="xl">
            <MiniKpi rotulo="Aderentes" valor={num(a.aderentes)} cor="verde.7" />
            <MiniKpi rotulo="Desvios" valor={num(desvios)} cor="laranja.7" />
          </Group>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 8 }}>
          {tendencia.length > 1 ? (
            <>
              <Text size="xs" c="dimmed" mb="xs">Aderência por semana</Text>
              <AreaChart
                h={196} data={tendencia} dataKey="semana"
                series={[{ name: "aderencia", label: "Aderência", color: saudavel ? "verde.6" : "laranja.6" }]}
                valueFormatter={(v) => `${v}%`} yAxisProps={{ domain: [0, 100], width: 34 }}
                curveType="monotone" withDots withGradient gridAxis="xy"
              />
            </>
          ) : (
            <Vazio texto="Ainda não há semanas suficientes para a tendência." />
          )}
        </Grid.Col>
      </Grid>
    </Card>
  );
}

function MiniKpi({ rotulo, valor, cor }: { rotulo: string; valor: string; cor?: string }) {
  return (
    <div>
      <Text size="xs" c="dimmed">{rotulo}</Text>
      <Text className="serif numero" fz={30} c={cor}>{valor}</Text>
    </div>
  );
}

function rotuloSemana(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

type ReturnTypePotencial = Awaited<ReturnType<typeof api.efetividade>>["backtest_potencial"];

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

function FilaDesvios({ justificativas }: { justificativas: Justificativa[] }) {
  const [expandido, setExpandido] = useState(false);
  const LIMITE = 3;
  const visiveis = expandido ? justificativas : justificativas.slice(0, LIMITE);
  const restantes = justificativas.length - LIMITE;
  return (
    <Card>
      <Group justify="space-between" align="start">
        <CabecalhoCard titulo="Monitoramento de aderência"
          detalhe="Decisões que divergiram da recomendação e a justificativa que o advogado registrou" />
        {justificativas.length > 0 && (
          <Badge color="laranja" variant="light" size="lg">{num(justificativas.length)} desvio(s)</Badge>
        )}
      </Group>
      <Table.ScrollContainer minWidth={920} mt="md">
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead><Table.Tr>
            <Th>Processo</Th><Th>Advogado</Th><Th>Recomendado</Th><Th>Decidiu</Th><Th>Justificativa</Th><Th>Situação</Th>
          </Table.Tr></Table.Thead>
          <Table.Tbody>
            {visiveis.map((j) => (
              <Table.Tr key={j.decisao_id}>
                <Table.Td>
                  <Anchor component={Link} to={`/casos/${j.processo_id}`} c="tinta.6" fw={600} size="sm" className="numero">{j.numero}</Anchor>
                  <Text size="xs" c="dimmed">{dataHora(j.created_at)}</Text>
                </Table.Td>
                <Table.Td><Text size="sm">{j.advogado}</Text><Text size="xs" c="dimmed">{j.escritorio}</Text></Table.Td>
                <Table.Td><Decisao tipo={j.rec_tipo} valor={j.valor_sugerido} /></Table.Td>
                <Table.Td><Decisao tipo={j.tipo} valor={j.valor_proposto} /></Table.Td>
                <Table.Td><Text size="xs" maw={340} lineClamp={3}>{j.justificativa}</Text></Table.Td>
                <Table.Td><StatusBadge status={j.status} size="sm" /></Table.Td>
              </Table.Tr>
            ))}
            {!justificativas.length && <Table.Tr><Table.Td colSpan={6}><Vazio texto="Nenhum desvio registrado." /></Table.Td></Table.Tr>}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      {restantes > 0 && (
        <Group justify="center" mt="sm">
          <Button variant="subtle" color="tinta" size="compact-sm" onClick={() => setExpandido((v) => !v)}
            rightSection={<IcoBaixo size={14} style={{ transform: expandido ? "rotate(180deg)" : undefined, transition: "transform .2s" }} />}>
            {expandido ? "Mostrar menos" : `Ver mais ${restantes} desvio${restantes > 1 ? "s" : ""}`}
          </Button>
        </Group>
      )}
    </Card>
  );
}

function Decisao({ tipo, valor }: { tipo: string; valor: number | null }) {
  return <Stack gap={2}><TipoBadge tipo={tipo} size="xs" />{valor != null && <Text size="xs" className="numero">{brl(valor)}</Text>}</Stack>;
}

// Grade compartilhada pelo cabeçalho e pelas linhas do comparativo: cenário · barra · custo · variação.
const COLUNAS_CENARIO = "minmax(96px,148px) minmax(48px,1fr) minmax(104px,122px) 52px";

function Potencial({ potencial }: { potencial: ReturnTypePotencial }) {
  const pronto = useMontado();
  const economia = useContagem(potencial?.economia_vs_defender);
  if (!potencial) return <Card><Vazio texto="Backtest do engine indisponível." /></Card>;

  // Defender tudo é a régua: cada barra vai de zero até o custo do cenário, na mesma escala.
  const base = potencial.defender_tudo;
  const cenarios = [
    { nome: "Defender tudo", nota: "nenhum acordo proposto", custo: potencial.defender_tudo },
    { nome: "Acordar tudo", nota: "acordo em todos os casos", custo: potencial.acordar_tudo },
    { nome: "Nossa política", nota: `acordo em ${pct(potencial.pct_acordo)} dos casos`, custo: potencial.politica, destaque: true },
  ];

  return (
    <Card h="100%" pos="relative" style={{ overflow: "hidden" }}>
      <Box pos="absolute" w={320} h={320} right={-160} top={-190}
        style={{ pointerEvents: "none", borderRadius: 999, background: "radial-gradient(circle, rgba(255,174,53,.14), transparent 70%)" }} />
      <CabecalhoCard titulo="Potencial nos 60 mil casos" detalhe="Replay histórico · não é resultado operacional" />

      <Box mt="xl" px={12} style={{ display: "grid", gridTemplateColumns: COLUNAS_CENARIO, columnGap: 12, alignItems: "end" }}>
        <Rotulo>Cenário</Rotulo>
        <span />
        <Rotulo alinharDireita>Custo total</Rotulo>
        <Rotulo alinharDireita>vs. base</Rotulo>
      </Box>
      <Divider my={8} />
      <Stack gap={2}>
        {cenarios.map((c, i) => (
          <Cenario key={c.nome} {...c} base={base} pronto={pronto} atraso={i * 120} />
        ))}
      </Stack>

      <Divider my="lg" />
      <Group justify="space-between" align="end" gap="xl" wrap="wrap">
        <div>
          <Text size="xs" c="dimmed">Economia potencial vs. defender tudo</Text>
          <Group align="baseline" gap="sm" mt={4}>
            <Text className="serif numero" fz={{ base: 30, sm: 36 }} lh={1}>{brlCompacto(economia)}</Text>
            <Badge color="verde" variant="light" size="lg">{pct(potencial.economia_pct)} menor</Badge>
          </Group>
        </div>
        <Box miw={210} style={{ flex: 1, maxWidth: 300 }}>
          <Group justify="space-between" mb={6}>
            <Text size="xs" c="dimmed">Composição da política</Text>
            <Text size="xs" c="dimmed" className="numero">{num(potencial.n_casos)} casos</Text>
          </Group>
          <Box h={8} bg="gray.2" style={{ display: "flex", borderRadius: 999, overflow: "hidden" }}>
            <Box bg="laranja.6" className="preencher" style={{ width: pronto ? `${potencial.pct_acordo * 100}%` : 0 }} />
            <Box flex={1} bg="tinta.3" />
          </Box>
          <Group gap="lg" mt={8}>
            <Legenda cor="laranja.6" rotulo="Acordo" valor={pct(potencial.pct_acordo)} />
            <Legenda cor="tinta.3" rotulo="Defesa" valor={pct(1 - potencial.pct_acordo)} />
          </Group>
        </Box>
      </Group>
      <Text size="10px" c="dimmed" mt="lg">
        Política {potencial.politica_versao} · modelo {potencial.modelo_versao} · defesa usa desfechos reais; acordos usam curva estimada de aceite.
      </Text>
    </Card>
  );
}

function Cenario({ nome, nota, custo, base, destaque, pronto, atraso }: {
  nome: string; nota: string; custo: number; base: number; destaque?: boolean; pronto: boolean; atraso: number;
}) {
  const largura = base > 0 ? Math.min(100, (custo / base) * 100) : 0;
  const delta = base > 0 ? (custo - base) / base : 0;
  return (
    <Tooltip label={`${nome} · ${brl(custo)}`} withArrow position="top" openDelay={150}>
      <Box px={12} py={12} style={{
        display: "grid", gridTemplateColumns: COLUNAS_CENARIO, columnGap: 12, alignItems: "center",
        borderRadius: 10,
        background: destaque ? "var(--mantine-color-laranja-0)" : undefined,
        boxShadow: destaque ? "inset 3px 0 0 var(--mantine-color-laranja-6)" : undefined,
      }}>
        <div>
          <Text size="sm" fw={destaque ? 600 : 500} lh={1.25}>{nome}</Text>
          <Text size="10px" c="dimmed" lh={1.4}>{nota}</Text>
        </div>
        <Box h={10} bg={destaque ? "rgba(255,174,53,.28)" : "gray.2"} style={{ borderRadius: 999, overflow: "hidden" }}>
          <Box h="100%" className="preencher" style={{
            width: pronto ? `${largura}%` : 0,
            transitionDelay: `${atraso}ms`,
            borderRadius: 999,
            background: destaque
              ? "linear-gradient(90deg, var(--mantine-color-laranja-5), var(--mantine-color-laranja-7))"
              : "var(--mantine-color-gray-4)",
          }} />
        </Box>
        <Text className="serif numero" fz={{ base: 18, sm: 21 }} ta="right" style={{ whiteSpace: "nowrap" }}>
          {brlCompacto(custo)}
        </Text>
        <Text size="xs" fw={600} className="numero" ta="right" c={delta < 0 ? "verde.7" : "dimmed"}>
          {delta < 0 ? pct(delta) : "base"}
        </Text>
      </Box>
    </Tooltip>
  );
}

function Rotulo({ children, alinharDireita }: { children: string; alinharDireita?: boolean }) {
  return (
    <Text size="10px" fw={600} tt="uppercase" lts=".08em" c="dimmed" ta={alinharDireita ? "right" : undefined}>
      {children}
    </Text>
  );
}

function Legenda({ cor, rotulo, valor }: { cor: string; rotulo: string; valor: string }) {
  return (
    <Group gap={6}>
      <Box w={8} h={8} bg={cor} style={{ borderRadius: 2 }} />
      <Text size="xs" c="dimmed">{rotulo}</Text>
      <Text size="xs" fw={600} className="numero">{valor}</Text>
    </Group>
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
