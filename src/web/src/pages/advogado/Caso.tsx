import {
  Alert, Anchor, Badge, Box, Button, Card, Collapse, CopyButton, Divider, Group, List, NumberInput, Paper,
  SegmentedControl, Select, SimpleGrid, Skeleton, Stack, Text, Textarea, ThemeIcon, Title, UnstyledButton,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router";

import {
  api, type Decisao, type DecisaoRegistrada, type Minutas, type Pessoa, type ProcessoDetalhe,
  type Recomendacao, type Resultado, type TipoDecisao,
} from "../../api/client";
import { AderenciaBadge, OrigemBadge, SinalChip, StatusBadge, TipoBadge } from "../../components/Badges";
import { IcoAcordo, IcoCheck, IcoCopiar, IcoDoc, IcoEscudo, IcoExterno, IcoRelogio, IcoVoltar } from "../../components/Icones";
import { useMontado } from "../../lib/animacao";
import { ROTULO_RESULTADO, brl, dataHora, duracao, pct } from "../../lib/format";

const NOMES_SUBSIDIOS: Record<string, string> = {
  contrato: "Contrato", extrato: "Extrato", comprovante_credito: "Comprovante de crédito", dossie: "Dossiê",
  demonstrativo_divida: "Demonstrativo da dívida", laudo_referenciado: "Laudo referenciado",
};

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
      <Cabecalho p={p} />
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

function Cabecalho({ p }: { p: ProcessoDetalhe }) {
  const autor = p.dados_extraidos?.autor;
  const copiar = useMutation({
    mutationFn: () => api.resumoTxt(p.id).then((t) => navigator.clipboard.writeText(t)),
    onSuccess: () => notifications.show({ message: "Resumo copiado. Cole no WhatsApp ou no e-mail.", color: "verde" }),
    onError: (e) => notifications.show({ message: (e as Error).message, color: "vermelho" }),
  });
  return (
    <Paper withBorder p="lg">
      <Group justify="space-between" align="start" wrap="wrap" gap="md">
        <div>
          <Anchor component={Link} to="/casos" size="xs" c="dimmed" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <IcoVoltar size={12} /> Casos
          </Anchor>
          <Title order={2} className="numero" mt={4} style={{ wordBreak: "break-all" }}>{p.numero}</Title>
          <Group gap={6} mt="xs" wrap="wrap">
            <Badge variant="default">{p.uf}</Badge>
            {p.sub_assunto && <Badge variant="default">{p.sub_assunto}</Badge>}
            <StatusBadge status={p.status} />
            {p.origem === "exemplo" && <Badge color="tinta" variant="light">autos reais</Badge>}
            <OrigemBadge origem={p.dados_extraidos?.origem} rotulo="extração stub" />
          </Group>
          {autor?.nome && (
            <Text mt="sm" size="sm">
              <b>{autor.nome}</b>
              {autor.idade ? ` · ${autor.idade} anos` : ""}{autor.cpf_mascarado ? ` · CPF ${autor.cpf_mascarado}` : ""}
              {p.dados_extraidos?.comarca ? ` · ${p.dados_extraidos.comarca}` : ""}
            </Text>
          )}
          <Group gap="lg" mt={autor?.nome ? 4 : "sm"}>
            <div>
              <Text size="xs" c="dimmed" tt="uppercase" lts=".06em" fw={500}>Valor da causa</Text>
              <Text className="numero" fz="lg">{brl(p.valor_causa, true)}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed" tt="uppercase" lts=".06em" fw={500}>Escritório</Text>
              <Text fz="sm" mt={2}>{p.escritorio}</Text>
            </div>
          </Group>
          {p.sinais.length > 0 && (
            <Group gap={4} mt="sm" wrap="wrap">{p.sinais.map((s) => <SinalChip key={s.codigo} sinal={s} />)}</Group>
          )}
        </div>
        <Button variant="default" size="sm" leftSection={<IcoCopiar size={15} />} onClick={() => copiar.mutate()} loading={copiar.isPending}>
          Copiar resumo
        </Button>
      </Group>
    </Paper>
  );
}

function CardRecomendacao({ p, rec, carregando, erro }: { p: ProcessoDetalhe; rec?: Recomendacao; carregando: boolean; erro: Error | null }) {
  if (carregando) return <Skeleton height={360} radius={12} />;
  if (erro) return <Alert color="vermelho" variant="light" title="Sem recomendação">{erro.message}</Alert>;
  if (!rec) return null;
  const s = rec.scores_snapshot;
  const acordo = rec.tipo === "acordo";
  return (
    <Card style={{ borderColor: acordo ? "var(--enter-laranja)" : "var(--enter-tinta)", borderWidth: 2 }}>
      <Text size="xs" c="dimmed" tt="uppercase" lts=".06em" fw={500}>A política recomenda</Text>
      <Group justify="space-between" align="flex-start" wrap="wrap" gap="xl" mt={4}>
        <div style={{ flex: "1 1 280px" }}>
          <Group gap="sm" align="baseline">
            <Title order={1} c={acordo ? "laranja.8" : "tinta.6"} className="subir">{acordo ? "Acordo" : "Defesa"}</Title>
            {acordo && <Text className="numero" fz={{ base: 26, sm: 32 }} lh={1}>{brl(rec.valor_sugerido)}</Text>}
          </Group>
          {acordo && rec.valor_min != null && rec.valor_max != null && rec.valor_sugerido != null && (
            <Box mt="md"><Banda min={rec.valor_min} sugerido={rec.valor_sugerido} max={rec.valor_max} causa={p.valor_causa} /></Box>
          )}
          <Box mt="lg">
            <Group justify="space-between" align="baseline">
              <Text size="xs" c="dimmed" tt="uppercase" lts=".06em" fw={500}>Probabilidade de êxito na defesa</Text>
              <Group gap={6}>
                <Text className="numero" fz={26} lh={1}>{pct(s.p_exito_defesa)}</Text>
                <OrigemBadge origem={s.origem} rotulo="score stub" />
              </Group>
            </Group>
            <Box mt={8}><Medidor valor={s.p_exito_defesa} /></Box>
            <Text size="xs" c="dimmed" mt={6} className="numero">
              Se perder, condenação estimada entre {brl(s.condenacao_p20)} e {brl(s.condenacao_p80)} (mediana {brl(s.condenacao_p50)})
            </Text>
          </Box>
          {rec.exige_aprovacao_valor_causa && (
            <Alert color="laranja" variant="light" mt="sm" p="xs">Valor da causa acima do teto: acordo exige aprovação do gestor.</Alert>
          )}
        </div>
        <Stack gap="xs" style={{ flex: "0 0 auto", minWidth: 200 }}>
          <Mini rotulo="Custo esperado da defesa" valor={brl(rec.custo_esperado_defesa)} />
          <Mini rotulo="Custo esperado do acordo" valor={brl(rec.custo_esperado_acordo)} />
          <Mini rotulo="Economia com acordo" valor={brl(rec.economia_esperada)} cor={rec.economia_esperada > 0 ? "verde.7" : "vermelho.6"} />
        </Stack>
      </Group>

      <Divider my="md" />
      <List spacing={6} size="sm" icon={<Box w={6} h={6} mt={7} bg="laranja.6" style={{ borderRadius: 999 }} />}>
        {rec.motivos.map((m, i) => <List.Item key={i}>{m}</List.Item>)}
      </List>
    </Card>
  );
}

/** Faixa de oferta em relação ao valor da causa: banda em laranja claro, marcador no valor sugerido. */
function Banda({ min, sugerido, max, causa }: { min: number; sugerido: number; max: number; causa: number }) {
  const pronto = useMontado();
  const pos = (v: number) => Math.min(100, Math.max(0, (v / causa) * 100));
  return (
    <div>
      <Box pos="relative" h={10} bg="gray.1" style={{ borderRadius: 5 }}>
        <Box pos="absolute" top={0} bottom={0} bg="laranja.3" className="preencher"
          style={{ left: `${pos(min)}%`, width: pronto ? `${pos(max) - pos(min)}%` : 0, borderRadius: 5 }} />
        {pronto && (
          <Box pos="absolute" top={-5} w={4} h={20} bg="laranja.7" className="pingar" style={{ left: `${pos(sugerido)}%`, borderRadius: 2 }} />
        )}
      </Box>
      <Group justify="space-between" mt={6}>
        <Text size="xs" c="dimmed" className="numero">banda {brl(min)} a {brl(max)}</Text>
        <Text size="xs" c="dimmed" className="numero">causa {brl(causa)}</Text>
      </Group>
    </div>
  );
}

function Medidor({ valor }: { valor: number }) {
  const pronto = useMontado();
  return (
    <Box h={10} bg="gray.1" style={{ borderRadius: 5, overflow: "hidden" }}>
      <Box h="100%" bg="tinta.6" className="preencher" style={{ width: pronto ? `${valor * 100}%` : 0, borderRadius: 5 }} />
    </Box>
  );
}

function Mini({ rotulo, valor, cor }: { rotulo: string; valor: string; cor?: string }) {
  return (
    <Paper p="sm" radius={8} bg="gray.0">
      <Text size="xs" c="dimmed">{rotulo}</Text>
      <Text fw={500} className="numero" c={cor}>{valor}</Text>
    </Paper>
  );
}

function CardAnalise({ p }: { p: ProcessoDetalhe }) {
  const a = p.analise;
  const d = p.dados_extraidos;
  if (!a && !d) return null;
  return (
    <Card>
      <Group justify="space-between">
        <Text fw={500}>Análise do caso</Text>
        <OrigemBadge origem={a?.origem} rotulo="análise stub" />
      </Group>
      {d?.resumo_fatos && <Text size="sm" mt="xs" c="dimmed" lineClamp={4}>{d.resumo_fatos}</Text>}
      {a?.texto && <Text size="sm" mt="xs">{a.texto}</Text>}
      <SimpleGrid cols={{ base: 1, sm: 2 }} mt="sm" spacing="md">
        {a && a.pontos_fortes_banco.length > 0 && (
          <div><Text size="xs" fw={500} c="verde.7" tt="uppercase" lts=".06em">Pontos fortes do banco</Text>
            <List size="sm" mt={4}>{a.pontos_fortes_banco.map((x, i) => <List.Item key={i}>{x}</List.Item>)}</List></div>
        )}
        {a && a.pontos_fracos_banco.length > 0 && (
          <div><Text size="xs" fw={500} c="vermelho.6" tt="uppercase" lts=".06em">Pontos fracos do banco</Text>
            <List size="sm" mt={4}>{a.pontos_fracos_banco.map((x, i) => <List.Item key={i}>{x}</List.Item>)}</List></div>
        )}
      </SimpleGrid>
      {d && d.pedidos.length > 0 && <Text size="xs" mt="sm" c="dimmed">Pedidos: {d.pedidos.join("; ")}</Text>}
    </Card>
  );
}

function CardDocumentos({ p, abertos, onAbrir }: { p: ProcessoDetalhe; abertos: Set<string>; onAbrir: (a: string) => void }) {
  const presentes = Object.entries(p.subsidios).filter(([, v]) => v).map(([k]) => NOMES_SUBSIDIOS[k] ?? k);
  const ausentes = Object.entries(p.subsidios).filter(([, v]) => !v).map(([k]) => NOMES_SUBSIDIOS[k] ?? k);
  const subsidios = (
    <Group gap={6} mt="md" wrap="wrap">
      <Text size="xs" c="dimmed" mr={4}>Subsídios</Text>
      {presentes.map((n) => (
        <Badge key={n} color="tinta" variant="light" size="sm" leftSection={<IcoCheck size={11} />}>{n}</Badge>
      ))}
      {ausentes.map((n) => <Badge key={n} color="gray" variant="outline" size="sm" td="line-through">{n}</Badge>)}
    </Group>
  );
  if (p.documentos.length === 0) {
    return (
      <Card>
        <Text fw={500}>Documentos</Text>
        <Text size="sm" c="dimmed" mt={4}>Processo sem PDFs anexados (caso sintético).</Text>
        {subsidios}
      </Card>
    );
  }
  const grupos = [["autos", "Autos"], ["subsidios", "Subsídios do banco"]] as const;
  return (
    <Card>
      <Text fw={500}>Documentos</Text>
      <Text size="xs" c="dimmed" mb="sm">Abrem em nova aba. Os que você abriu ficam marcados.</Text>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        {grupos.map(([tipo, rotulo]) => {
          const docs = p.documentos.filter((d) => d.tipo === tipo);
          return (
            <div key={tipo}>
              <Text size="xs" fw={500} c="dimmed" tt="uppercase" lts=".06em" mb={4}>{rotulo}</Text>
              <Stack gap={2}>
                {docs.map((d) => {
                  const aberto = abertos.has(d.arquivo);
                  return (
                    <UnstyledButton key={d.arquivo} component="a" href={d.url} target="_blank" rel="noopener" className="linha-link"
                      onClick={() => onAbrir(d.arquivo)} p={6} style={{ borderRadius: 8, display: "flex", alignItems: "center", gap: 10 }}>
                      <ThemeIcon size={26} radius="sm" variant="light" color={aberto ? "verde" : "tinta"}>
                        {aberto ? <IcoCheck size={14} /> : <IcoDoc size={14} />}
                      </ThemeIcon>
                      <Text size="sm" c={aberto ? "dimmed" : undefined} truncate style={{ flex: 1 }}>{d.arquivo}</Text>
                      <IcoExterno size={13} style={{ color: "var(--mantine-color-dimmed)" }} />
                    </UnstyledButton>
                  );
                })}
                {docs.length === 0 && <Text size="xs" c="dimmed">nenhum</Text>}
              </Stack>
            </div>
          );
        })}
      </SimpleGrid>
      {subsidios}
    </Card>
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
