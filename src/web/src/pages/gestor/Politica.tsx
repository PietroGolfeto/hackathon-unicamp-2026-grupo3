import {
  Alert, Badge, Box, Button, Card, Group, Indicator, Modal, MultiSelect, NumberInput, SimpleGrid, Skeleton, Stack, Switch,
  Table, Text, TextInput, Title,
} from "@mantine/core";
import { useDebouncedValue, useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { ApiError, api, type Backtest, type Politica as PoliticaT, type PoliticaParams } from "../../api/client";
import { IcoSeta } from "../../components/Icones";
import { Stat } from "../../components/Stat";
import { useMontado } from "../../lib/animacao";
import { brl, brlCompacto, dataHora, num, pct } from "../../lib/format";

const SINAIS = ["IDOSO", "CREDITO_CONTA_TERCEIRO", "BOLETIM_OCORRENCIA", "RECLAMACAO_BACEN", "SEM_CONTRATO", "ASSINATURA_DIVERGENTE", "CANAL_DIGITAL_SEM_PERFIL"];

type Campo = { chave: keyof PoliticaParams; rotulo: string; tipo: "brl" | "pct" | "num"; min?: number; max?: number; step?: number; ajuda?: string };
const CAMPOS: { grupo: string; campos: Campo[] }[] = [
  { grupo: "Custo de defender", campos: [
    { chave: "custas_fixas_defesa", rotulo: "Custas fixas", tipo: "brl", step: 100 },
    { chave: "honorarios_defesa_pct", rotulo: "Honorários (% da causa)", tipo: "pct", max: 1 },
    { chave: "sucumbencia_pct", rotulo: "Sucumbência (% da condenação)", tipo: "pct", max: 1 },
  ] },
  { grupo: "Custo de acordar", campos: [
    { chave: "custo_operacional_acordo", rotulo: "Custo operacional", tipo: "brl", step: 50 },
    { chave: "taxa_aceite_esperada", rotulo: "Taxa de aceite esperada", tipo: "pct", max: 1, ajuda: "Hipótese. A efetividade substitui por dado real." },
  ] },
  { grupo: "Oferta", campos: [
    { chave: "fator_oferta", rotulo: "Fator da oferta (× prejuízo esperado)", tipo: "pct", max: 2 },
    { chave: "piso_oferta_pct_causa", rotulo: "Piso (% da causa)", tipo: "pct", max: 1 },
    { chave: "teto_oferta_pct_causa", rotulo: "Teto (% da causa)", tipo: "pct", max: 1 },
    { chave: "margem_banda_pct", rotulo: "Banda (±%)", tipo: "pct", max: 1 },
    { chave: "arredondamento", rotulo: "Arredondamento", tipo: "brl", min: 1, step: 10 },
  ] },
  { grupo: "Regra de decisão", campos: [
    { chave: "limiar_defesa_forte", rotulo: "Defesa forte se P(êxito) ≥", tipo: "pct", max: 1 },
    { chave: "limiar_acordo_forte", rotulo: "Acordo forte se P(êxito) ≤", tipo: "pct", max: 1 },
    { chave: "valor_causa_max_sem_aprovacao", rotulo: "Causa máx. sem aprovação", tipo: "brl", step: 5000 },
  ] },
];

export default function Politica() {
  const qc = useQueryClient();
  const ativa = useQuery({ queryKey: ["politica-ativa"], queryFn: api.politicaAtiva });
  const versoes = useQuery({ queryKey: ["politicas"], queryFn: api.politicas });
  const [params, setParams] = useState<PoliticaParams | null>(null);
  const [nome, setNome] = useState("");
  const [debounced] = useDebouncedValue(params, 300);
  const [modal, { open, close }] = useDisclosure(false);

  useEffect(() => { if (ativa.data && !params) setParams(ativa.data.params); }, [ativa.data, params]);

  const sim = useQuery({
    queryKey: ["simular", debounced], queryFn: () => api.simular(debounced!), enabled: !!debounced, retry: false,
    placeholderData: (prev) => prev,
  });
  const publicar = useMutation({
    mutationFn: async () => {
      const nova = await api.criarPolitica(nome.trim() || `Versão ${(versoes.data?.length ?? 0) + 1}`, params!);
      return api.ativarPolitica(nova.id);
    },
    onSuccess: (p) => {
      close(); setNome("");
      qc.invalidateQueries({ queryKey: ["politica-ativa"] }); qc.invalidateQueries({ queryKey: ["politicas"] });
      qc.invalidateQueries({ queryKey: ["efetividade"] });
      notifications.show({ title: `Política v${p.versao} publicada`, message: "Novos casos já recebem a recomendação da nova versão.", color: "verde" });
    },
    onError: (e) => notifications.show({ message: (e as Error).message, color: "vermelho" }),
  });
  const ativar = useMutation({
    mutationFn: (id: number) => api.ativarPolitica(id),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["politica-ativa"] }); qc.invalidateQueries({ queryKey: ["politicas"] });
      setParams(p.params);
      notifications.show({ message: `Política v${p.versao} ativada.`, color: "verde" });
    },
  });

  if (ativa.error) return <Alert color="vermelho" variant="light">{(ativa.error as Error).message}</Alert>;
  if (ativa.isLoading || !params) {
    return <Stack gap="lg"><Skeleton height={44} width={360} radius="sm" /><SimpleGrid cols={{ base: 1, lg: 2 }}><Skeleton height={520} radius={12} /><Skeleton height={520} radius={12} /></SimpleGrid></Stack>;
  }
  const base = ativa.data!;
  const diff = diferencas(base.params, params);
  const set = (k: keyof PoliticaParams, v: unknown) => setParams((p) => ({ ...p!, [k]: v }));
  const semHistorico = sim.error instanceof ApiError && sim.error.status === 503;

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end" wrap="wrap" gap="md">
        <div>
          <Title order={2}>Política de acordos</Title>
          <Text c="dimmed" size="sm" mt={4}>Ativa: v{base.versao} · {base.nome} · publicada {dataHora(base.publicada_em)}</Text>
        </div>
        <Group>
          <Button variant="default" onClick={() => setParams(base.params)} disabled={diff.length === 0}>Descartar mudanças</Button>
          <Indicator color="laranja" label={diff.length} size={18} disabled={diff.length === 0} offset={4}>
            <Button onClick={open} disabled={diff.length === 0} rightSection={<IcoSeta size={16} />}>Publicar nova versão</Button>
          </Indicator>
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
        <Card>
          <Group justify="space-between" mb="md">
            <div>
              <Text fw={500}>Parâmetros</Text>
              <Text size="xs" c="dimmed">Cada ajuste é simulado nos 60 mil casos reais ao lado.</Text>
            </div>
            {diff.length > 0 && <Badge color="laranja" variant="light">{diff.length} alterado(s)</Badge>}
          </Group>
          <Stack gap="lg">
            {CAMPOS.map((g) => (
              <div key={g.grupo}>
                <Group gap={8} mb="xs">
                  <Box w={16} h={2} bg="laranja.6" style={{ borderRadius: 2 }} />
                  <Text size="xs" fw={500} tt="uppercase" lts=".06em" c="dimmed">{g.grupo}</Text>
                </Group>
                <SimpleGrid cols={{ base: 1, xs: 2, md: 3 }} spacing="sm">
                  {g.campos.map((c) => <CampoInput key={c.chave} c={c} params={params} base={base.params} onChange={set} />)}
                </SimpleGrid>
              </div>
            ))}
            <MultiSelect label="Sinais nos autos que forçam acordo" data={SINAIS} value={params.sinais_forcam_acordo}
              onChange={(v) => set("sinais_forcam_acordo", v)} searchable size="sm"
              description="Extraídos dos PDFs pela extração de documentos. Entram pela política, não pelo modelo." />
            <Switch label="Incluir processos extintos no backtest (23% da base, condenação zero)" size="sm" color="tinta"
              checked={params.incluir_extincao_no_backtest} onChange={(e) => set("incluir_extincao_no_backtest", e.currentTarget.checked)} />
          </Stack>
        </Card>

        <Stack gap="md">
          <Card style={{ borderColor: "var(--enter-tinta)" }}>
            <Group justify="space-between" align="start" wrap="wrap">
              <div>
                <Text fw={500}>Simulação nos 60 mil casos reais</Text>
                <Text size="xs" c="dimmed">Custo real de cada processo com o resultado que de fato teve.</Text>
              </div>
              {sim.data && (
                <Badge variant="light" color="tinta" className="numero">
                  {num(sim.data.n)} casos · {sim.data.tempo_ms} ms
                </Badge>
              )}
            </Group>
            {semHistorico && <Alert color="laranja" variant="light" mt="md">{(sim.error as Error).message}</Alert>}
            {sim.error && !semHistorico && <Alert color="vermelho" variant="light" mt="md">{(sim.error as Error).message}</Alert>}
            {sim.isLoading && <Skeleton height={220} mt="md" radius="sm" />}
            {sim.data && (
              <Box mt="md" style={{ opacity: sim.isFetching ? 0.55 : 1, transition: "opacity .2s" }}>
                <ResultadoSim b={sim.data} />
              </Box>
            )}
          </Card>

          <Card>
            <Text fw={500} mb="sm">Versões</Text>
            <Table fz="sm" verticalSpacing={6}>
              <Table.Thead><Table.Tr><Th>v</Th><Th>Nome</Th><Th>Publicada</Th><Th>Backtest</Th><Table.Th /></Table.Tr></Table.Thead>
              <Table.Tbody>
                {(versoes.data ?? []).map((v: PoliticaT) => (
                  <Table.Tr key={v.id}>
                    <Table.Td className="numero">{v.versao}{v.ativa && <Badge ml={6} size="xs" color="verde" variant="light">ativa</Badge>}</Table.Td>
                    <Table.Td>{v.nome}</Table.Td>
                    <Table.Td><Text size="xs" c="dimmed" className="numero">{dataHora(v.publicada_em)}</Text></Table.Td>
                    <Table.Td className="numero">
                      {v.resumo_backtest ? `${pct(v.resumo_backtest.economia_vs_defender.pct)} · ${pct(v.resumo_backtest.pct_acordo)} acordo` : "—"}
                    </Table.Td>
                    <Table.Td>
                      <Group gap={4} wrap="nowrap" justify="end">
                        {!v.ativa && <Button size="compact-xs" variant="light" onClick={() => ativar.mutate(v.id)} loading={ativar.isPending}>Ativar</Button>}
                        <Button size="compact-xs" variant="subtle" onClick={() => setParams(v.params)}>Carregar</Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Stack>
      </SimpleGrid>

      <Modal opened={modal} onClose={close} title={`Publicar v${(versoes.data?.length ?? 0) + 1} e ativar`} size="lg">
        <Stack>
          <TextInput label="Nome da versão" placeholder="ex.: Oferta 70% com teto 50%" value={nome} onChange={(e) => setNome(e.currentTarget.value)} />
          <Text size="sm" fw={500}>O que muda em relação à v{base.versao}</Text>
          <Table fz="sm" verticalSpacing={4}>
            <Table.Tbody>
              {diff.map((d) => (
                <Table.Tr key={d.chave}>
                  <Table.Td>{d.rotulo}</Table.Td>
                  <Table.Td c="dimmed" className="numero">{d.antes}</Table.Td>
                  <Table.Td w={24}><IcoSeta size={14} style={{ color: "var(--enter-laranja)" }} /></Table.Td>
                  <Table.Td fw={500} className="numero">{d.depois}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          {sim.data && (
            <Alert variant="light" color="tinta">
              Backtest: {pct(sim.data.pct_acordo)} de acordos, economia de {brlCompacto(sim.data.economia_vs_defender.valor)} ({pct(sim.data.economia_vs_defender.pct)}) vs defender tudo.
              Recomendações já gravadas não mudam; casos abertos a partir de agora usam a nova versão.
            </Alert>
          )}
          <Group justify="end">
            <Button variant="default" onClick={close}>Cancelar</Button>
            <Button onClick={() => publicar.mutate()} loading={publicar.isPending}>Publicar e ativar</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}

function Th({ children }: { children: string }) {
  return <Table.Th><Text size="xs" fw={500} tt="uppercase" lts=".06em" c="dimmed">{children}</Text></Table.Th>;
}

function CampoInput({ c, params, base, onChange }: { c: Campo; params: PoliticaParams; base: PoliticaParams; onChange: (k: keyof PoliticaParams, v: unknown) => void }) {
  const v = params[c.chave] as number | null;
  const mudou = base[c.chave] !== params[c.chave];
  const comum = {
    label: c.rotulo, size: "sm" as const, description: c.ajuda,
    styles: mudou ? { input: { borderColor: "var(--enter-laranja)", boxShadow: "0 0 0 2px rgba(255,174,53,.25)" } } : undefined,
  };
  if (c.tipo === "pct") {
    return <NumberInput {...comum} value={v == null ? "" : Math.round(v * 1000) / 10} suffix="%" min={0} max={(c.max ?? 1) * 100} step={1} decimalScale={1}
      onChange={(x) => onChange(c.chave, typeof x === "number" ? x / 100 : Number(x) / 100)} />;
  }
  return <NumberInput {...comum} value={v ?? ""} prefix={c.tipo === "brl" ? "R$ " : undefined} min={c.min ?? 0} step={c.step ?? 1}
    thousandSeparator="." decimalSeparator="," allowNegative={false}
    onChange={(x) => onChange(c.chave, x === "" ? null : typeof x === "number" ? x : Number(x))} />;
}

function ResultadoSim({ b }: { b: Backtest }) {
  const t = b.totais;
  const max = Math.max(t.politica, t.defender_tudo, t.acordar_tudo);
  return (
    <Stack gap="md">
      <SimpleGrid cols={{ base: 1, xs: 3 }} spacing="sm">
        <Stat rotulo="Política" destaque numero={t.politica} formatar={brlCompacto} detalhe={`${pct(b.pct_acordo)} acordos · oferta média ${brl(b.oferta_media)}`} />
        <Stat rotulo="Defender tudo" numero={t.defender_tudo} formatar={brlCompacto} detalhe={`economia de ${pct(b.economia_vs_defender.pct)} = ${brlCompacto(b.economia_vs_defender.valor)}`} />
        <Stat rotulo="Acordar tudo" numero={t.acordar_tudo} formatar={brlCompacto} detalhe={`diferença ${pct(b.economia_vs_acordar.pct)}`} />
      </SimpleGrid>
      <Stack gap={8}>
        <Barra rotulo="Política" valor={t.politica} max={max} cor="laranja.6" />
        <Barra rotulo="Defender tudo" valor={t.defender_tudo} max={max} cor="tinta.6" />
        <Barra rotulo="Acordar tudo" valor={t.acordar_tudo} max={max} cor="gray.4" />
      </Stack>
      <Text size="xs" c="dimmed">
        Custo real por processo {brl(b.custo_medio_por_processo)} · regras: {Object.entries(b.por_regra).map(([k, v]) => `${k} ${num(v)}`).join(" · ")} ·
        hipótese de aceite {pct(b.hipoteses.taxa_aceite_esperada)}{b.incluir_extincao ? "" : " · sem Extinção"}
      </Text>
      <Table fz="xs" verticalSpacing={2}>
        <Table.Thead><Table.Tr><Th>Subsídios</Th><Th>Casos</Th><Th>Acordo</Th><Th>Política</Th><Th>Defender</Th><Th>Economia</Th></Table.Tr></Table.Thead>
        <Table.Tbody className="numero">
          {b.por_n_docs.map((l) => (
            <Table.Tr key={String(l.n_docs)}>
              <Table.Td>{String(l.n_docs)}/6</Table.Td><Table.Td>{num(l.n)}</Table.Td><Table.Td>{pct(l.pct_acordo)}</Table.Td>
              <Table.Td>{brlCompacto(l.politica)}</Table.Td><Table.Td>{brlCompacto(l.defender_tudo)}</Table.Td>
              <Table.Td c={l.economia_vs_defender >= 0 ? "verde.7" : "vermelho.6"}>{brlCompacto(l.economia_vs_defender)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  );
}

/** Barra horizontal proporcional ao maior dos três totais; cresce a partir de zero ao montar e desliza quando o valor muda. */
function Barra({ rotulo, valor, max, cor }: { rotulo: string; valor: number; max: number; cor: string }) {
  const pronto = useMontado();
  const largura = pronto && max > 0 ? Math.max(1.5, (valor / max) * 100) : 0;
  return (
    <Group gap="sm" wrap="nowrap">
      <Text size="xs" w={96} c="dimmed" style={{ flex: "none" }}>{rotulo}</Text>
      <Box h={10} bg="gray.1" style={{ flex: 1, borderRadius: 5, overflow: "hidden" }}>
        <Box h="100%" bg={cor} className="preencher" style={{ width: `${largura}%`, borderRadius: 5 }} />
      </Box>
      <Text size="xs" fw={500} w={72} ta="right" className="numero" style={{ flex: "none" }}>{brlCompacto(valor)}</Text>
    </Group>
  );
}

function fmt(c: Campo | undefined, v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.join(", ") || "nenhum";
  if (typeof v === "boolean") return v ? "sim" : "não";
  if (typeof v === "number") return c?.tipo === "pct" ? pct(v, 1) : c?.tipo === "brl" ? brl(v) : String(v);
  return String(v);
}

function diferencas(a: PoliticaParams, b: PoliticaParams) {
  const todos = CAMPOS.flatMap((g) => g.campos);
  return (Object.keys(b) as (keyof PoliticaParams)[])
    .filter((k) => JSON.stringify(a[k]) !== JSON.stringify(b[k]))
    .map((k) => {
      const c = todos.find((x) => x.chave === k);
      const rotulo = c?.rotulo ?? (k === "sinais_forcam_acordo" ? "Sinais que forçam acordo" : k === "incluir_extincao_no_backtest" ? "Incluir Extinção no backtest" : k);
      return { chave: k, rotulo, antes: fmt(c, a[k]), depois: fmt(c, b[k]) };
    });
}
