import { Alert, Box, Button, Card, Collapse, Group, NumberInput, SegmentedControl, Stack, Text, Textarea } from "@mantine/core";

import type { DecisaoRegistrada, Recomendacao, TipoDecisao } from "../../../../api/client";
import { IcoAcordo, IcoCheck, IcoEscudo, IcoRelogio } from "../../../../components/Icones";
import { brl, duracao } from "../../../../lib/format";
import type { DocumentosAbertos } from "../caso.types";
import { useFormDecisao } from "../hooks/useFormDecisao";

export function FormDecisao({ pid, rec, abertos, inicio, onOk }: {
  pid: number; rec: Recomendacao; abertos: DocumentosAbertos; inicio: number; onOk: (r: DecisaoRegistrada) => void;
}) {
  const {
    tipo, setTipo, valor, setValor, justificativa, setJustificativa, segundos, foraDaBanda, diverge, registrar,
  } = useFormDecisao({ pid, rec, abertos, inicio, onOk });

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
      <form onSubmit={(e) => { e.preventDefault(); registrar.mutate(); }}>
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
          {registrar.isError && <Alert color="vermelho" variant="light">{(registrar.error as Error).message}</Alert>}
          <Button type="submit" loading={registrar.isPending} size="md">
            Registrar decisão
          </Button>
        </Stack>
      </form>
    </Card>
  );
}
