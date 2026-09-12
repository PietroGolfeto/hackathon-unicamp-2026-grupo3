import {
  Alert, Badge, Button, Card, Group, Loader, Modal, MultiSelect, NumberInput, SimpleGrid, Stack, Switch, Table, Text,
  TextInput, Title,
} from "@mantine/core";
import { useDebouncedValue, useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { ApiError, api, type Backtest, type Politica as PoliticaT, type PoliticaParams } from "../../api/client";
import { Stat } from "../../components/Stat";
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
      notifications.show({ title: `Política v${p.versao} publicada`, message: "Novos casos já recebem a recomendação da nova versão.", color: "teal" });
    },
    onError: (e) => notifications.show({ message: (e as Error).message, color: "red" }),
  });
  const ativar = useMutation({
    mutationFn: (id: number) => api.ativarPolitica(id),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["politica-ativa"] }); qc.invalidateQueries({ queryKey: ["politicas"] });
      setParams(p.params);
      notifications.show({ message: `Política v${p.versao} ativada.`, color: "teal" });
    },
  });

  if (ativa.isLoading || !params) return <Loader />;
  if (ativa.error) return <Alert color="red">{(ativa.error as Error).message}</Alert>;
  const base = ativa.data!;
  const diff = diferencas(base.params, params);
  const set = (k: keyof PoliticaParams, v: unknown) => setParams((p) => ({ ...p!, [k]: v }));
  const semHistorico = sim.error instanceof ApiError && sim.error.status === 503;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="end" wrap="wrap">
        <div>
          <Title order={3}>Política de acordos</Title>
          <Text c="dimmed" size="sm">Ativa: v{base.versao} · {base.nome} · publicada {dataHora(base.publicada_em)}</Text>
        </div>
        <Group>
          <Button variant="default" onClick={() => setParams(base.params)} disabled={diff.length === 0}>Descartar mudanças</Button>
          <Button onClick={open} disabled={diff.length === 0}>Publicar nova versão…</Button>
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
        <Card withBorder radius="md">
          <Text fw={600} mb="xs">Parâmetros {diff.length > 0 && <Badge color="orange" variant="light" ml="xs">{diff.length} alterado(s)</Badge>}</Text>
          <Stack gap="sm">
            {CAMPOS.map((g) => (
              <div key={g.grupo}>
                <Text size="xs" fw={600} c="dimmed" tt="uppercase" mb={4}>{g.grupo}</Text>
                <SimpleGrid cols={{ base: 1, xs: 2, md: 3 }} spacing="xs">
                  {g.campos.map((c) => <CampoInput key={c.chave} c={c} params={params} base={base.params} onChange={set} />)}
                </SimpleGrid>
              </div>
            ))}
            <MultiSelect label="Sinais nos autos que forçam acordo" data={SINAIS} value={params.sinais_forcam_acordo}
              onChange={(v) => set("sinais_forcam_acordo", v)} searchable size="xs"
              description="Extraídos dos PDFs por P3. Entram pela política, não pelo modelo." />
            <Switch label="Incluir processos extintos no backtest (23% da base, condenação zero)" size="xs"
              checked={params.incluir_extincao_no_backtest} onChange={(e) => set("incluir_extincao_no_backtest", e.currentTarget.checked)} />
          </Stack>
        </Card>

        <Stack gap="sm">
          <Card withBorder radius="md">
            <Group justify="space-between">
              <Text fw={600}>Simulação nos 60 mil casos reais</Text>
              {sim.data && <Text size="xs" c="dimmed">{num(sim.data.n)} casos · {sim.data.tempo_ms} ms · scores {sim.data.scores_origem}</Text>}
            </Group>
            {semHistorico && <Alert color="yellow" variant="light" mt="xs">{(sim.error as Error).message}</Alert>}
            {sim.error && !semHistorico && <Alert color="red" variant="light" mt="xs">{(sim.error as Error).message}</Alert>}
            {sim.isLoading && <Loader size="sm" mt="xs" />}
            {sim.data && <ResultadoSim b={sim.data} />}
          </Card>
          <Card withBorder radius="md">
            <Text fw={600} mb="xs">Versões</Text>
            <Table fz="sm" verticalSpacing={4}>
              <Table.Thead><Table.Tr><Table.Th>v</Table.Th><Table.Th>Nome</Table.Th><Table.Th>Publicada</Table.Th><Table.Th>Backtest</Table.Th><Table.Th /></Table.Tr></Table.Thead>
              <Table.Tbody>
                {(versoes.data ?? []).map((v: PoliticaT) => (
                  <Table.Tr key={v.id}>
                    <Table.Td>{v.versao}{v.ativa && <Badge ml={4} size="xs" color="teal">ativa</Badge>}</Table.Td>
                    <Table.Td>{v.nome}</Table.Td>
                    <Table.Td>{dataHora(v.publicada_em)}</Table.Td>
                    <Table.Td>{v.resumo_backtest ? `${pct(v.resumo_backtest.economia_vs_defender.pct)} · ${pct(v.resumo_backtest.pct_acordo)} acordo` : "—"}</Table.Td>
                    <Table.Td>
                      {!v.ativa && <Button size="compact-xs" variant="light" onClick={() => ativar.mutate(v.id)} loading={ativar.isPending}>Ativar</Button>}
                      <Button size="compact-xs" variant="subtle" ml={4} onClick={() => setParams(v.params)}>Carregar</Button>
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
          <Text size="sm" fw={600}>O que muda em relação à v{base.versao}</Text>
          <Table fz="sm" verticalSpacing={2}>
            <Table.Tbody>
              {diff.map((d) => (
                <Table.Tr key={d.chave}><Table.Td>{d.rotulo}</Table.Td><Table.Td c="dimmed">{d.antes}</Table.Td><Table.Td>→</Table.Td><Table.Td fw={600}>{d.depois}</Table.Td></Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          {sim.data && (
            <Alert variant="light" color="indigo">
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

function CampoInput({ c, params, base, onChange }: { c: Campo; params: PoliticaParams; base: PoliticaParams; onChange: (k: keyof PoliticaParams, v: unknown) => void }) {
  const v = params[c.chave] as number | null;
  const mudou = base[c.chave] !== params[c.chave];
  const comum = { label: c.rotulo, size: "xs" as const, description: c.ajuda, styles: mudou ? { input: { borderColor: "var(--mantine-color-orange-5)" } } : undefined };
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
  return (
    <Stack gap="xs" mt="xs">
      <SimpleGrid cols={3} spacing="xs">
        <Stat rotulo="Política" valor={brlCompacto(t.politica)} detalhe={`${pct(b.pct_acordo)} acordos · oferta média ${brl(b.oferta_media)}`} cor="indigo" />
        <Stat rotulo="Defender tudo" valor={brlCompacto(t.defender_tudo)} detalhe={`economia ${pct(b.economia_vs_defender.pct)} = ${brlCompacto(b.economia_vs_defender.valor)}`} />
        <Stat rotulo="Acordar tudo" valor={brlCompacto(t.acordar_tudo)} detalhe={`diferença ${pct(b.economia_vs_acordar.pct)}`} />
      </SimpleGrid>
      <Text size="xs" c="dimmed">
        Custo real por processo: {brl(b.custo_medio_por_processo)} · regras: {Object.entries(b.por_regra).map(([k, v]) => `${k} ${num(v)}`).join(" · ")} ·
        hipótese de aceite {pct(b.hipoteses.taxa_aceite_esperada)}{b.incluir_extincao ? "" : " · sem Extinção"}
      </Text>
      <Table fz="xs" verticalSpacing={1}>
        <Table.Thead><Table.Tr><Table.Th>Subsídios</Table.Th><Table.Th>Casos</Table.Th><Table.Th>Acordo</Table.Th><Table.Th>Política</Table.Th><Table.Th>Defender</Table.Th><Table.Th>Economia</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>
          {b.por_n_docs.map((l) => (
            <Table.Tr key={String(l.n_docs)}>
              <Table.Td>{String(l.n_docs)}/6</Table.Td><Table.Td>{num(l.n)}</Table.Td><Table.Td>{pct(l.pct_acordo)}</Table.Td>
              <Table.Td>{brlCompacto(l.politica)}</Table.Td><Table.Td>{brlCompacto(l.defender_tudo)}</Table.Td>
              <Table.Td c={l.economia_vs_defender >= 0 ? "teal" : "red"}>{brlCompacto(l.economia_vs_defender)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
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
