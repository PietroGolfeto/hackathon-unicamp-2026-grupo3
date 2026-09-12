import {
  Alert, Anchor, Badge, Button, Card, CopyButton, Divider, Group, List, Loader, NumberInput, Paper, Radio,
  Select, SimpleGrid, Stack, Text, Textarea, Title, Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router";

import {
  api, type Decisao, type DecisaoRegistrada, type Minutas, type Pessoa, type ProcessoDetalhe, type Recomendacao,
  type Resultado, type TipoDecisao,
} from "../../api/client";
import { OrigemBadge, SinalChip, StatusBadge, TipoBadge } from "../../components/Badges";
import { ROTULO_REGRA, ROTULO_RESULTADO, ROTULO_STATUS, brl, dataHora, duracao, pct } from "../../lib/format";

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

  if (processo.isLoading) return <Loader />;
  if (processo.error) return <Alert color="red">{(processo.error as Error).message}</Alert>;
  const p = processo.data!;
  const decisaoAtual = registrada?.decisao ?? p.decisao_atual;
  const mostrarForm = !decisaoAtual || novaDecisao;

  return (
    <Stack gap="md">
      <Cabecalho p={p} />
      <CardRecomendacao p={p} rec={rec.data} carregando={rec.isLoading} erro={rec.error as Error | null} />
      <CardAnalise p={p} />
      <CardDocumentos p={p} abertos={abertos} onAbrir={(a) => setAbertos((s) => new Set(s).add(a))} />
      {decisaoAtual && !novaDecisao && (
        <CardDecisaoAtual d={decisaoAtual} registrada={registrada} p={p}
          onNova={() => setNovaDecisao(true)}
          onResultado={() => { qc.invalidateQueries({ queryKey: ["processo", pid] }); qc.invalidateQueries({ queryKey: ["processos"] }); }} />
      )}
      {mostrarForm && rec.data && (
        <FormDecisao pid={pid} rec={rec.data} abertos={abertos} inicio={inicio.current}
          onOk={(r) => {
            setRegistrada(r); setNovaDecisao(false);
            qc.invalidateQueries({ queryKey: ["processo", pid] });
            qc.invalidateQueries({ queryKey: ["processos"] });
            notifications.show({ title: "Decisão registrada", message: r.mensagem, color: r.decisao.aderente ? "teal" : "orange" });
          }} />
      )}
    </Stack>
  );
}

function Cabecalho({ p }: { p: ProcessoDetalhe }) {
  const autor = p.dados_extraidos?.autor;
  const copiar = useMutation({
    mutationFn: () => api.resumoTxt(p.id).then((t) => navigator.clipboard.writeText(t)),
    onSuccess: () => notifications.show({ message: "Resumo copiado. Cole no WhatsApp ou no e-mail.", color: "teal" }),
    onError: (e) => notifications.show({ message: (e as Error).message, color: "red" }),
  });
  return (
    <Paper withBorder p="md" radius="md">
      <Group justify="space-between" align="start" wrap="wrap">
        <div>
          <Anchor component={Link} to="/casos" size="xs" c="dimmed">← casos</Anchor>
          <Title order={3} style={{ wordBreak: "break-all" }}>{p.numero}</Title>
          <Group gap={6} mt={4} wrap="wrap">
            <Badge variant="default">{p.uf}</Badge>
            {p.sub_assunto && <Badge variant="default">{p.sub_assunto}</Badge>}
            <StatusBadge status={p.status} />
            {p.origem === "exemplo" && <Badge color="grape" variant="light">autos reais</Badge>}
            <OrigemBadge origem={p.dados_extraidos?.origem} rotulo="extração stub" />
          </Group>
          {autor?.nome && (
            <Text mt="xs" size="sm">
              <b>{autor.nome}</b>
              {autor.idade ? ` · ${autor.idade} anos` : ""}{autor.cpf_mascarado ? ` · CPF ${autor.cpf_mascarado}` : ""}
              {p.dados_extraidos?.comarca ? ` · ${p.dados_extraidos.comarca}` : ""}
            </Text>
          )}
          <Text size="sm" mt={autor?.nome ? 0 : "xs"}>Valor da causa: <b>{brl(p.valor_causa, true)}</b> · Escritório: {p.escritorio}</Text>
          {p.sinais.length > 0 && (
            <Group gap={4} mt="xs" wrap="wrap">{p.sinais.map((s) => <SinalChip key={s.codigo} sinal={s} />)}</Group>
          )}
        </div>
        <Button variant="light" size="xs" onClick={() => copiar.mutate()} loading={copiar.isPending}>Copiar resumo</Button>
      </Group>
    </Paper>
  );
}

function CardRecomendacao({ p, rec, carregando, erro }: { p: ProcessoDetalhe; rec?: Recomendacao; carregando: boolean; erro: Error | null }) {
  if (carregando) return <Card withBorder><Loader size="sm" /></Card>;
  if (erro) return <Alert color="red" title="Sem recomendação">{erro.message}</Alert>;
  if (!rec) return null;
  const s = rec.scores_snapshot;
  const presentes = Object.entries(p.subsidios).filter(([, v]) => v).map(([k]) => NOMES_SUBSIDIOS[k] ?? k);
  const ausentes = Object.entries(p.subsidios).filter(([, v]) => !v).map(([k]) => NOMES_SUBSIDIOS[k] ?? k);
  return (
    <Card withBorder radius="md" style={{ borderColor: rec.tipo === "acordo" ? "var(--mantine-color-teal-5)" : "var(--mantine-color-indigo-5)", borderWidth: 2 }}>
      <Group justify="space-between" align="start" wrap="wrap">
        <Group gap="sm">
          <TipoBadge tipo={rec.tipo} size="xl" />
          {rec.tipo === "acordo" && (
            <div>
              <Text fw={700} size="xl">{brl(rec.valor_sugerido)}</Text>
              <Text size="xs" c="dimmed">banda {brl(rec.valor_min)} a {brl(rec.valor_max)}</Text>
            </div>
          )}
        </Group>
        <Stack gap={0} align="end">
          <Text size="xs" c="dimmed">política v{rec.politica_versao} · {ROTULO_REGRA[rec.regra] ?? rec.regra}</Text>
          <Group gap={4}>
            <Text size="xs" c="dimmed">P(êxito) {pct(s.p_exito_defesa)} · {s.modelo_versao}</Text>
            <OrigemBadge origem={s.origem} rotulo="score stub" />
          </Group>
        </Stack>
      </Group>
      <SimpleGrid cols={{ base: 1, sm: 3 }} mt="md" spacing="xs">
        <Mini rotulo="Custo esperado da defesa" valor={brl(rec.custo_esperado_defesa)} />
        <Mini rotulo="Custo esperado do acordo" valor={brl(rec.custo_esperado_acordo)} />
        <Mini rotulo="Economia esperada com acordo" valor={brl(rec.economia_esperada)} cor={rec.economia_esperada > 0 ? "teal" : "red"} />
      </SimpleGrid>
      <List size="sm" mt="md" spacing={4}>
        {rec.motivos.map((m, i) => <List.Item key={i}>{m}</List.Item>)}
      </List>
      {rec.exige_aprovacao_valor_causa && (
        <Alert color="orange" variant="light" mt="sm" p="xs">Valor da causa acima do teto: acordo exige aprovação do gestor.</Alert>
      )}
      <Divider my="sm" />
      <Group gap="xs" wrap="wrap">
        <Text size="xs" c="dimmed">Subsídios:</Text>
        {presentes.map((n) => <Badge key={n} color="teal" variant="light" size="sm">{n}</Badge>)}
        {ausentes.map((n) => <Badge key={n} color="gray" variant="outline" size="sm" td="line-through">{n}</Badge>)}
      </Group>
      {s.contribuicoes?.length > 0 && (
        <Group gap={4} mt="xs" wrap="wrap">
          <Text size="xs" c="dimmed">Fatores:</Text>
          {s.contribuicoes.slice(0, 5).map((c) => (
            <Tooltip key={c.feature} label={c.descricao ?? c.feature}>
              <Badge size="xs" variant="dot" color={c.contribuicao >= 0 ? "teal" : "red"}>
                {c.feature.replaceAll("_", " ")} {c.contribuicao >= 0 ? "+" : ""}{(c.contribuicao * 100).toFixed(0)}
              </Badge>
            </Tooltip>
          ))}
        </Group>
      )}
    </Card>
  );
}

function Mini({ rotulo, valor, cor }: { rotulo: string; valor: string; cor?: string }) {
  return (
    <Paper p="xs" radius="sm" bg="var(--mantine-color-gray-0)">
      <Text size="xs" c="dimmed">{rotulo}</Text>
      <Text fw={600} c={cor}>{valor}</Text>
    </Paper>
  );
}

function CardAnalise({ p }: { p: ProcessoDetalhe }) {
  const a = p.analise;
  const d = p.dados_extraidos;
  if (!a && !d) return null;
  return (
    <Card withBorder radius="md">
      <Group justify="space-between">
        <Text fw={600}>Análise do caso</Text>
        <OrigemBadge origem={a?.origem} rotulo="análise stub" />
      </Group>
      {d?.resumo_fatos && <Text size="sm" mt="xs" c="dimmed" lineClamp={4}>{d.resumo_fatos}</Text>}
      {a?.texto && <Text size="sm" mt="xs">{a.texto}</Text>}
      <SimpleGrid cols={{ base: 1, sm: 2 }} mt="sm" spacing="xs">
        {a && a.pontos_fortes_banco.length > 0 && (
          <div><Text size="xs" fw={600} c="teal">Pontos fortes do banco</Text>
            <List size="xs">{a.pontos_fortes_banco.map((x, i) => <List.Item key={i}>{x}</List.Item>)}</List></div>
        )}
        {a && a.pontos_fracos_banco.length > 0 && (
          <div><Text size="xs" fw={600} c="red">Pontos fracos do banco</Text>
            <List size="xs">{a.pontos_fracos_banco.map((x, i) => <List.Item key={i}>{x}</List.Item>)}</List></div>
        )}
      </SimpleGrid>
      {d && d.pedidos.length > 0 && <Text size="xs" mt="xs" c="dimmed">Pedidos: {d.pedidos.join("; ")}</Text>}
    </Card>
  );
}

function CardDocumentos({ p, abertos, onAbrir }: { p: ProcessoDetalhe; abertos: Set<string>; onAbrir: (a: string) => void }) {
  if (p.documentos.length === 0) {
    return <Card withBorder radius="md"><Text fw={600}>Documentos</Text><Text size="sm" c="dimmed">Processo sem PDFs anexados (caso sintético).</Text></Card>;
  }
  const grupos = [["autos", "Autos"], ["subsidios", "Subsídios do banco"]] as const;
  return (
    <Card withBorder radius="md">
      <Text fw={600}>Documentos</Text>
      <Text size="xs" c="dimmed" mb="xs">Abrem em nova aba. Os que você abriu ficam marcados.</Text>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs">
        {grupos.map(([tipo, rotulo]) => (
          <div key={tipo}>
            <Text size="xs" fw={600} c="dimmed" tt="uppercase">{rotulo}</Text>
            <Stack gap={4} mt={4}>
              {p.documentos.filter((d) => d.tipo === tipo).map((d) => (
                <Anchor key={d.arquivo} href={d.url} target="_blank" rel="noopener" size="sm"
                  onClick={() => onAbrir(d.arquivo)} c={abertos.has(d.arquivo) ? "dimmed" : undefined}>
                  {abertos.has(d.arquivo) ? "✓ " : "📄 "}{d.arquivo}
                </Anchor>
              ))}
              {p.documentos.filter((d) => d.tipo === tipo).length === 0 && <Text size="xs" c="dimmed">nenhum</Text>}
            </Stack>
          </div>
        ))}
      </SimpleGrid>
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
    <Card withBorder radius="md">
      <Group justify="space-between">
        <Text fw={600}>Sua decisão</Text>
        <Text size="xs" c="dimmed">⏱ {duracao(segundos)}</Text>
      </Group>
      <form onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <Stack gap="sm" mt="xs">
          <Radio.Group value={tipo} onChange={(v) => setTipo(v as TipoDecisao)}>
            <Group>
              <Radio value="acordo" label="Propor acordo" />
              <Radio value="defesa" label="Defender" />
            </Group>
          </Radio.Group>
          {tipo === "acordo" && (
            <NumberInput label="Valor proposto" value={valor ?? ""} onChange={(v) => setValor(typeof v === "number" ? v : v === "" ? null : Number(v))}
              min={0} step={50} thousandSeparator="." decimalSeparator="," prefix="R$ " inputMode="decimal"
              description={rec.tipo === "acordo" ? `Banda da política: ${brl(rec.valor_min)} a ${brl(rec.valor_max)}` : "A política recomendou defesa: acordo vai para aprovação do gestor."}
              error={foraDaBanda ? "Fora da banda: exige justificativa e aprovação do gestor" : undefined} />
          )}
          {diverge && (
            <Textarea label="Justificativa" required autosize minRows={2} value={justificativa}
              onChange={(e) => setJustificativa(e.currentTarget.value)}
              description="Sua decisão diverge da recomendação. Explique em uma ou duas frases; o gestor vê isso no painel." />
          )}
          {!diverge && <Text size="xs" c="teal">Aderente à política.</Text>}
          {mutation.isError && <Alert color="red" variant="light">{(mutation.error as Error).message}</Alert>}
          <Button type="submit" loading={mutation.isPending} disabled={diverge && !justificativa.trim()} size="md">
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
    <Card withBorder radius="md">
      <Group justify="space-between" wrap="wrap">
        <Group gap="sm">
          <Text fw={600}>Decisão registrada</Text>
          <TipoBadge tipo={d.tipo} size="sm" />
          {d.tipo === "acordo" && <Text fw={600}>{brl(d.valor_proposto)}</Text>}
          <StatusBadge status={d.status} />
          <Badge color={d.aderente ? "teal" : "orange"} variant="light">{d.aderente ? "aderente" : `desvio de ${d.tipo_desvio}`}</Badge>
        </Group>
        <Text size="xs" c="dimmed">{d.usuario_nome} · {dataHora(d.created_at)} · {duracao(d.tempo_analise_s)}</Text>
      </Group>
      {d.justificativa && <Text size="sm" mt="xs"><b>Justificativa:</b> {d.justificativa}</Text>}
      {d.status === "pendente_aprovacao" && <Alert color="orange" variant="light" mt="xs" p="xs">Aguardando aprovação do gestor antes de propor à parte.</Alert>}
      {d.status === "rejeitada" && <Alert color="red" variant="light" mt="xs" p="xs">Acordo rejeitado pelo gestor{d.comentario_aprovacao ? `: ${d.comentario_aprovacao}` : "."}</Alert>}

      {d.tipo === "acordo" && contato && <Contato c={contato} />}
      {minutas && <MinutasView m={minutas} />}

      {d.resultado ? (
        <Alert color="green" variant="light" mt="md" title={ROTULO_RESULTADO[d.resultado] ?? d.resultado}>
          {d.valor_final != null && <>Valor final: <b>{brl(d.valor_final, true)}</b> · </>}
          {dataHora(d.resultado_em)}{d.observacao ? ` · ${d.observacao}` : ""}
        </Alert>
      ) : (
        d.status !== "pendente_aprovacao" && d.status !== "rejeitada" && <FormResultado d={d} onOk={onResultado} />
      )}
      <Group mt="md">
        <Button variant="subtle" size="xs" onClick={onNova}>Registrar nova decisão</Button>
        <Text size="xs" c="dimmed">Decisões são append-only; a mais recente vale. {ROTULO_STATUS[d.status] ? "" : ""}</Text>
      </Group>
    </Card>
  );
}

function Contato({ c }: { c: Pessoa }) {
  const partes = [c.nome, c.oab ? `OAB ${c.oab}` : null, c.email, c.telefone].filter(Boolean);
  if (partes.length === 0) return null;
  return (
    <Paper p="xs" mt="sm" radius="sm" bg="var(--mantine-color-gray-0)">
      <Text size="xs" c="dimmed" fw={600}>Advogado(a) da parte autora</Text>
      <Group gap="xs" wrap="wrap">
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
    <Stack gap="xs" mt="sm">
      <Group gap="xs"><Text fw={600} size="sm">Minutas</Text><OrigemBadge origem={m.origem} rotulo="minuta stub" /></Group>
      {itens.map(([titulo, texto]) => (
        <div key={titulo}>
          <Group justify="space-between" mb={2}>
            <Text size="xs" c="dimmed">{titulo}</Text>
            <CopyButton value={texto}>{({ copied, copy }) => <Button size="compact-xs" variant="light" onClick={copy}>{copied ? "Copiado" : "Copiar"}</Button>}</CopyButton>
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
    onSuccess: () => { notifications.show({ message: "Resultado registrado.", color: "teal" }); onOk(); },
  });
  return (
    <Paper withBorder p="sm" mt="md" radius="sm">
      <Text fw={600} size="sm">Resultado da negociação</Text>
      <Text size="xs" c="dimmed" mb="xs">É isso que alimenta a efetividade da política. Registre assim que souber.</Text>
      <form onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="xs">
          <Select label="Resultado" data={opcoes} value={resultado} onChange={(v) => setResultado(v as Resultado | null)} required />
          {precisaValor && (
            <NumberInput label="Valor final" value={valorFinal ?? ""} onChange={(v) => setValorFinal(typeof v === "number" ? v : v === "" ? null : Number(v))}
              min={0} thousandSeparator="." decimalSeparator="," prefix="R$ " required />
          )}
          <Textarea label="Observação" value={obs} onChange={(e) => setObs(e.currentTarget.value)} autosize minRows={1} />
        </SimpleGrid>
        {m.isError && <Alert color="red" variant="light" mt="xs">{(m.error as Error).message}</Alert>}
        <Button type="submit" mt="sm" size="sm" loading={m.isPending} disabled={!resultado || (precisaValor && valorFinal == null)}>Registrar resultado</Button>
      </form>
    </Paper>
  );
}
