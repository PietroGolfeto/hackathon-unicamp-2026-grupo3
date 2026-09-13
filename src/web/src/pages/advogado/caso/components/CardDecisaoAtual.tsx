import { Alert, Button, Card, Group, Text } from "@mantine/core";

import type { Decisao, DecisaoRegistrada } from "../../../../api/client";
import { AderenciaBadge, StatusBadge, TipoBadge } from "../../../../components/Badges";
import { ROTULO_RESULTADO, brl, dataHora, duracao } from "../../../../lib/format";
import type { ProcessoProps } from "../caso.types";
import { ContatoAdverso } from "./ContatoAdverso";
import { FormResultado } from "./FormResultado";
import { MinutasView } from "./MinutasView";

export function CardDecisaoAtual({ d, registrada, p, onNova, onResultado }: ProcessoProps & {
  d: Decisao; registrada: DecisaoRegistrada | null; onNova: () => void; onResultado: () => void;
}) {
  const minutas = registrada?.minutas ?? null;
  const contato = registrada?.contato_adverso ?? p.dados_extraidos?.advogado_autor ?? null;
  return (
    <Card>
      <Group justify="space-between" wrap="wrap" gap="sm">
        <Group gap="sm" wrap="wrap">
          <Text fw={600}>Decisão registrada</Text>
          <TipoBadge tipo={d.tipo} size="sm" />
          {d.tipo === "acordo" && <Text className="serif numero" fz="lg">{brl(d.valor_proposto)}</Text>}
          <StatusBadge status={d.status} size="sm" />
          <AderenciaBadge aderente={d.aderente} tipoDesvio={d.tipo_desvio} size="sm" />
        </Group>
        <Text size="xs" c="dimmed" className="numero">{d.usuario_nome} · {dataHora(d.created_at)} · {duracao(d.tempo_analise_s)}</Text>
      </Group>
      {d.justificativa && <Text size="sm" mt="sm"><b>Justificativa:</b> {d.justificativa}</Text>}
      {d.status === "pendente_aprovacao" && <Alert color="laranja" variant="light" mt="sm" p="xs">Aguardando aprovação do gestor antes de propor à parte.</Alert>}
      {d.status === "rejeitada" && <Alert color="vermelho" variant="light" mt="sm" p="xs">Acordo rejeitado pelo gestor{d.comentario_aprovacao ? `: ${d.comentario_aprovacao}` : "."}</Alert>}

      {d.tipo === "acordo" && contato && <ContatoAdverso c={contato} />}
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
