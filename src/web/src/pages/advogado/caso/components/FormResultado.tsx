import { Alert, Button, NumberInput, Paper, Select, SimpleGrid, Text, Textarea } from "@mantine/core";

import type { Decisao, Resultado } from "../../../../api/client";
import { useFormResultado } from "../hooks/useFormResultado";

export function FormResultado({ d, onOk }: { d: Decisao; onOk: () => void }) {
  const {
    opcoes, resultado, setResultado, valorFinal, setValorFinal, obs, setObs, precisaValor, registrar,
  } = useFormResultado({ d, onOk });

  return (
    <Paper withBorder p="md" mt="md" radius={8}>
      <Text fw={500} size="sm">Resultado da negociação</Text>
      <Text size="xs" c="dimmed" mb="sm">É isso que alimenta a efetividade da política. Registre assim que souber.</Text>
      <form onSubmit={(e) => { e.preventDefault(); registrar.mutate(); }}>
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
          <Select label="Resultado" data={opcoes} value={resultado} onChange={(v) => setResultado(v as Resultado | null)} required />
          {precisaValor && (
            <NumberInput label="Valor final" value={valorFinal ?? ""} onChange={(v) => setValorFinal(typeof v === "number" ? v : v === "" ? null : Number(v))}
              min={0} thousandSeparator="." decimalSeparator="," prefix="R$ " required />
          )}
          <Textarea label="Observação" value={obs} onChange={(e) => setObs(e.currentTarget.value)} autosize minRows={1} />
        </SimpleGrid>
        {registrar.isError && <Alert color="vermelho" variant="light" mt="xs">{(registrar.error as Error).message}</Alert>}
        <Button type="submit" mt="sm" size="sm" loading={registrar.isPending} disabled={!resultado || (precisaValor && valorFinal == null)}>Registrar resultado</Button>
      </form>
    </Paper>
  );
}
