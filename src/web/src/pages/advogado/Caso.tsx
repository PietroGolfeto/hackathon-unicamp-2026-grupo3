import {
  Alert, Anchor, Box, Button, Card, Collapse, CopyButton, Group, NumberInput, Paper,
  SegmentedControl, Select, SimpleGrid, Skeleton, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router";

import {
  api, type Decisao, type DecisaoRegistrada, type Minutas, type Pessoa, type ProcessoDetalhe,
  type Recomendacao, type Resultado, type TipoDecisao,
} from "../../api/client";
import { AderenciaBadge, OrigemBadge, StatusBadge, TipoBadge } from "../../components/Badges";
import { IcoAcordo, IcoCheck, IcoCopiar, IcoEscudo, IcoRelogio } from "../../components/Icones";
import { ROTULO_RESULTADO, brl, dataHora, duracao } from "../../lib/format";
import { CabecalhoCaso } from "./caso/components/CabecalhoCaso";
import { CardAnalise } from "./caso/components/CardAnalise";
import { CardDocumentos } from "./caso/components/CardDocumentos";
import { CardRecomendacao } from "./caso/components/CardRecomendacao";

export default function Caso() {
  const { id } = useParams();
  const pid = Number(id);
  const qc = useQueryClient();
  const processo = useQuery({ queryKey: ["processo", pid], queryFn: () => api.processo(pid), enabled: !!pid });
  const rec = useQuery({ queryKey: ["recomendacao", pid], queryFn: () => api.recomendacao(pid), enabled: !!pid });
  const [registrada, setRegistrada] = useState<DecisaoRegistrada | null>(null);
  const [novaDecisao, setNovaDecisao] = useState(false);
  const [abertos, setAbertos] = useState<Set<string>>(new Set());
  const inicio = useRef(Date.now());

  if (processo.isLoading) return <Stack gap="md"><Skeleton height={140} radius={12} /><Skeleton height={360} radius={12} /><Skeleton height={120} radius={12} /></Stack>;
  if (processo.error) return <Alert color="vermelho" variant="light">{(processo.error as Error).message}</Alert>;
  const p = processo.data!;
  const decisaoAtual = registrada?.decisao ?? p.decisao_atual;
  const mostrarForm = !decisaoAtual || novaDecisao;
  const invalidar = () => { qc.invalidateQueries({ queryKey: ["processo", pid] }); qc.invalidateQueries({ queryKey: ["processos"] }); };

  return (
    <Stack gap="md" className="escalonado">
      <CabecalhoCaso p={p} />
      <CardRecomendacao p={p} rec={rec.data} carregando={rec.isLoading} erro={rec.error as Error | null} />
      <CardAnalise p={p} />
      <CardDocumentos p={p} abertos={abertos} onAbrir={(a) => setAbertos((s) => new Set(s).add(a))} />
      {decisaoAtual && !novaDecisao && (
        <CardDecisaoAtual d={decisaoAtual} registrada={registrada} p={p} onNova={() => setNovaDecisao(true)} onResultado={invalidar} />
      )}
      {mostrarForm && rec.data && (
        <FormDecisao pid={pid} rec={rec.data} abertos={abertos} inicio={inicio.current}
          onOk={(r) => {
            setRegistrada(r); setNovaDecisao(false); invalidar();
            notifications.show({ title: "Decisão registrada", message: r.mensagem, color: r.decisao.aderente ? "verde" : "laranja" });
          }} />
      )}
    </Stack>
  );
}

function FormDecisao({ pid, rec, abertos, inicio, onOk }: { pid: number; rec: Recomendacao; abertos: Set<string>; inicio: number; onOk: (r: DecisaoRegistrada) => void }) {
  const [tipo, setTipo] = useState<TipoDecisao>(rec.tipo);
  const [valor, setValor] = useState<number | null>(rec.valor_sugerido);
  const [justificativa, setJustificativa] = useState("");
  const [segundos, setSegundos] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSegundos(Math.floor((Date.now() - inicio) / 1000)), 1000);
    return () => clearInterval(t);
  }, [inicio]);

  const foraDaBanda = tipo === "acordo" && rec.tipo === "acordo" && valor != null &&
    rec.valor_min != null && rec.valor_max != null && (valor < rec.valor_min || valor > rec.valor_max);
  const diverge = tipo !== rec.tipo || foraDaBanda;
  const mutation = useMutation({
    mutationFn: () => api.decidir(pid, {
      tipo, valor_proposto: tipo === "acordo" ? valor : null, justificativa: justificativa || null,
      tempo_analise_s: Math.floor((Date.now() - inicio) / 1000), documentos_abertos: [...abertos],
    }),
    onSuccess: onOk,
  });

  return (
    <Card>
      <Group justify="space-between">
        <Text fw={500}>Sua decisão</Text>
        <Group gap={6} c="dimmed">
          <Box w={6} h={6} bg="laranja.6" className="pulsar" style={{ borderRadius: 999 }} />
          <IcoRelogio size={14} />
          <Text size="xs" className="numero">{duracao(segundos)}</Text>
        </Group>
      </Group>
      <form onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <Stack gap="md" mt="md">
          <SegmentedControl fullWidth size="md" radius={8} color="tinta" value={tipo} onChange={(v) => setTipo(v as TipoDecisao)}
            data={[
              { value: "acordo", label: <Group gap={6} justify="center" wrap="nowrap"><IcoAcordo size={16} /><span>Propor acordo</span></Group> },
              { value: "defesa", label: <Group gap={6} justify="center" wrap="nowrap"><IcoEscudo size={16} /><span>Defender</span></Group> },
            ]} />
          <Collapse in={tipo === "acordo"}>
            <NumberInput label="Valor proposto" value={valor ?? ""} onChange={(v) => setValor(typeof v === "number" ? v : v === "" ? null : Number(v))}
              min={0} step={50} thousandSeparator="." decimalSeparator="," prefix="R$ " decimalScale={2} fixedDecimalScale inputMode="decimal" size="md"
              description={rec.tipo === "acordo" ? `Banda da política: ${brl(rec.valor_min)} a ${brl(rec.valor_max)}` : "A política recomendou defesa: acordo vai para aprovação do gestor."}
              error={foraDaBanda ? "Fora da banda: exige justificativa e aprovação do gestor" : undefined} />
          </Collapse>
          <Collapse in={diverge}>
            <Textarea label="Justificativa" autosize minRows={2} value={justificativa}
              onChange={(e) => setJustificativa(e.currentTarget.value)}
              description="Sua decisão diverge da recomendação. Explique em uma ou duas frases; o gestor vê isso no painel." />
          </Collapse>
          {!diverge && (
            <Group gap={6} c="verde.7">
              <IcoCheck size={14} />
              <Text size="xs" fw={500}>Aderente à política.</Text>
            </Group>
          )}
          {mutation.isError && <Alert color="vermelho" variant="light">{(mutation.error as Error).message}</Alert>}
          <Button type="submit" loading={mutation.isPending} size="md">
            Registrar decisão
          </Button>
        </Stack>
      </form>
    </Card>
  );
}

function CardDecisaoAtual({ d, registrada, p, onNova, onResultado }: {
  d: Decisao; registrada: DecisaoRegistrada | null; p: ProcessoDetalhe; onNova: () => void; onResultado: () => void;
}) {
  const minutas = registrada?.minutas ?? null;
  const contato = registrada?.contato_adverso ?? p.dados_extraidos?.advogado_autor ?? null;
  return (
    <Card>
      <Group justify="space-between" wrap="wrap" gap="sm">
        <Group gap="sm" wrap="wrap">
          <Text fw={500}>Decisão registrada</Text>
          <TipoBadge tipo={d.tipo} size="sm" />
          {d.tipo === "acordo" && <Text className="numero" fz="lg">{brl(d.valor_proposto)}</Text>}
          <StatusBadge status={d.status} size="sm" />
          <AderenciaBadge aderente={d.aderente} tipoDesvio={d.tipo_desvio} size="sm" />
        </Group>
        <Text size="xs" c="dimmed" className="numero">{d.usuario_nome} · {dataHora(d.created_at)} · {duracao(d.tempo_analise_s)}</Text>
      </Group>
      {d.justificativa && <Text size="sm" mt="sm"><b>Justificativa:</b> {d.justificativa}</Text>}
      {d.status === "pendente_aprovacao" && <Alert color="laranja" variant="light" mt="sm" p="xs">Aguardando aprovação do gestor antes de propor à parte.</Alert>}
      {d.status === "rejeitada" && <Alert color="vermelho" variant="light" mt="sm" p="xs">Acordo rejeitado pelo gestor{d.comentario_aprovacao ? `: ${d.comentario_aprovacao}` : "."}</Alert>}

      {d.tipo === "acordo" && contato && <Contato c={contato} />}
      {minutas && <MinutasView m={minutas} />}

      {d.resultado ? (
        <Alert color="verde" variant="light" mt="md" title={ROTULO_RESULTADO[d.resultado] ?? d.resultado}>
          {d.valor_final != null && <>Valor final: <b>{brl(d.valor_final, true)}</b> · </>}
          {dataHora(d.resultado_em)}{d.observacao ? ` · ${d.observacao}` : ""}
        </Alert>
      ) : (
        d.status !== "pendente_aprovacao" && d.status !== "rejeitada" && <FormResultado d={d} onOk={onResultado} />
      )}
      <Group mt="md" gap="sm">
        <Button variant="subtle" size="xs" color="tinta" onClick={onNova}>Registrar nova decisão</Button>
        <Text size="xs" c="dimmed">Decisões são append-only; a mais recente vale.</Text>
      </Group>
    </Card>
  );
}

function Contato({ c }: { c: Pessoa }) {
  const partes = [c.nome, c.oab ? `OAB ${c.oab}` : null, c.email, c.telefone].filter(Boolean);
  if (partes.length === 0) return null;
  return (
    <Paper p="sm" mt="sm" radius={8} bg="gray.0">
      <Text size="xs" c="dimmed" fw={500} tt="uppercase" lts=".06em">Advogado(a) da parte autora</Text>
      <Group gap="xs" wrap="wrap" mt={2}>
        <Text size="sm">{partes.join(" · ")}</Text>
        {c.email && <Anchor href={`mailto:${c.email}`} size="sm">e-mail</Anchor>}
        {c.telefone && <Anchor href={`https://wa.me/55${c.telefone.replace(/\D/g, "")}`} target="_blank" size="sm">WhatsApp</Anchor>}
      </Group>
    </Paper>
  );
}

function MinutasView({ m }: { m: Minutas }) {
  const itens = [
    ["Proposta de acordo", m.proposta_acordo], ["Mensagem de contato", m.mensagem_contato], ["Roteiro de defesa", m.roteiro_defesa],
  ].filter(([, t]) => t);
  return (
    <Stack gap="xs" mt="md">
      <Group gap="xs"><Text fw={500} size="sm">Minutas</Text><OrigemBadge origem={m.origem} rotulo="minuta stub" /></Group>
      {itens.map(([titulo, texto]) => (
        <div key={titulo}>
          <Group justify="space-between" mb={2}>
            <Text size="xs" c="dimmed">{titulo}</Text>
            <CopyButton value={texto}>
              {({ copied, copy }) => (
                <Button size="compact-xs" variant="light" color={copied ? "verde" : "tinta"} onClick={copy} leftSection={copied ? <IcoCheck size={12} /> : <IcoCopiar size={12} />}>
                  {copied ? "Copiado" : "Copiar"}
                </Button>
              )}
            </CopyButton>
          </Group>
          <Textarea value={texto} readOnly autosize minRows={3} maxRows={10} styles={{ input: { fontSize: 13 } }} />
        </div>
      ))}
    </Stack>
  );
}

function FormResultado({ d, onOk }: { d: Decisao; onOk: () => void }) {
  const opcoes = useMemo(() => d.tipo === "defesa"
    ? [{ value: "seguiu_defesa", label: ROTULO_RESULTADO.seguiu_defesa }]
    : ["aceito", "contraproposta_aceita", "recusado", "sem_resposta"].map((v) => ({ value: v, label: ROTULO_RESULTADO[v] })), [d.tipo]);
  const [resultado, setResultado] = useState<Resultado | null>(d.tipo === "defesa" ? "seguiu_defesa" : null);
  const [valorFinal, setValorFinal] = useState<number | null>(d.valor_proposto);
  const [obs, setObs] = useState("");
  const precisaValor = resultado === "aceito" || resultado === "contraproposta_aceita";
  const m = useMutation({
    mutationFn: () => api.resultado(d.id, { resultado: resultado!, valor_final: precisaValor ? valorFinal : null, observacao: obs || null }),
    onSuccess: () => { notifications.show({ message: "Resultado registrado.", color: "verde" }); onOk(); },
  });
  return (
    <Paper withBorder p="md" mt="md" radius={8}>
      <Text fw={500} size="sm">Resultado da negociação</Text>
      <Text size="xs" c="dimmed" mb="sm">É isso que alimenta a efetividade da política. Registre assim que souber.</Text>
      <form onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
          <Select label="Resultado" data={opcoes} value={resultado} onChange={(v) => setResultado(v as Resultado | null)} required />
          {precisaValor && (
            <NumberInput label="Valor final" value={valorFinal ?? ""} onChange={(v) => setValorFinal(typeof v === "number" ? v : v === "" ? null : Number(v))}
              min={0} thousandSeparator="." decimalSeparator="," prefix="R$ " required />
          )}
          <Textarea label="Observação" value={obs} onChange={(e) => setObs(e.currentTarget.value)} autosize minRows={1} />
        </SimpleGrid>
        {m.isError && <Alert color="vermelho" variant="light" mt="xs">{(m.error as Error).message}</Alert>}
        <Button type="submit" mt="sm" size="sm" loading={m.isPending} disabled={!resultado || (precisaValor && valorFinal == null)}>Registrar resultado</Button>
      </form>
    </Paper>
  );
}
