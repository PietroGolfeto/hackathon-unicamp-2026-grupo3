import { Alert, Box, Card, Divider, Group, List, Skeleton, Stack, Text, Title } from "@mantine/core";

import type { ProcessoDetalhe, Recomendacao } from "../../../../api/client";
import { OrigemBadge } from "../../../../components/Badges";
import { brl, pct, ROTULO_TIPO } from "../../../../lib/format";
import { NOMES_SUBSIDIOS } from "../caso.const";
import { BandaOferta } from "./BandaOferta";
import { MedidorProbabilidade } from "./MedidorProbabilidade";
import { MiniMetrica } from "./MiniMetrica";

export function CardRecomendacao({ p, rec, carregando, erro }: {
  p: ProcessoDetalhe; rec?: Recomendacao; carregando: boolean; erro: Error | null;
}) {
  if (carregando) return <Skeleton height={360} radius={12} />;
  if (erro) return <Alert color="vermelho" variant="light" title="Sem recomendação">{erro.message}</Alert>;
  if (!rec) return null;
  const s = rec.scores_snapshot;
  const defesa = rec.tipo === "defesa";
  const instruir = rec.tipo === "instruir";
  // "instruir" é um acordo já dimensionado que espera os subsídios: tem oferta e banda como o acordo.
  const temOferta = rec.valor_sugerido != null;
  return (
    <Card style={{ borderColor: defesa ? "var(--enter-tinta)" : "var(--enter-laranja)", borderWidth: 2 }}>
      <Text size="xs" c="dimmed" tt="uppercase" lts=".06em" fw={500}>A política recomenda</Text>
      <Group justify="space-between" align="flex-start" wrap="wrap" gap="xl" mt={4}>
        <div style={{ flex: "1 1 280px" }}>
          <Group gap="sm" align="baseline">
            <Title order={1} c={defesa ? "tinta.6" : "laranja.8"} className="serif subir" fw={500}>{ROTULO_TIPO[rec.tipo] ?? rec.tipo}</Title>
            {temOferta && !instruir && <Text className="serif numero" fz={{ base: 26, sm: 32 }} lh={1}>{brl(rec.valor_sugerido)}</Text>}
          </Group>
          {instruir && (
            <Alert color="laranja" variant="light" mt="sm" p="xs">
              Solicitar ao banco: {rec.docs_a_solicitar.map((d) => NOMES_SUBSIDIOS[d] ?? d).join(", ")}.
              {temOferta && ` Se o banco não localizar, propor o acordo de ${brl(rec.valor_sugerido)}.`}
            </Alert>
          )}
          {temOferta && rec.valor_min != null && rec.valor_max != null && rec.valor_sugerido != null && (
            <Box mt="md"><BandaOferta min={rec.valor_min} sugerido={rec.valor_sugerido} max={rec.valor_max} causa={p.valor_causa} /></Box>
          )}
          <Box mt="lg">
            <Group justify="space-between" align="baseline">
              <Text size="xs" c="dimmed" tt="uppercase" lts=".06em" fw={500}>Probabilidade de êxito na defesa</Text>
              <Group gap={6}>
                <Text className="serif numero" fz={26} lh={1}>{pct(s.p_exito_defesa)}</Text>
                <OrigemBadge origem={s.origem} rotulo="score stub" />
              </Group>
            </Group>
            <Box mt={8}><MedidorProbabilidade valor={s.p_exito_defesa} /></Box>
            <Text size="xs" c="dimmed" mt={6} className="numero">
              Se perder, condenação estimada entre {brl(s.condenacao_p20)} e {brl(s.condenacao_p80)} (mediana {brl(s.condenacao_p50)})
            </Text>
          </Box>
          {rec.exige_aprovacao_valor_causa && (
            <Alert color="laranja" variant="light" mt="sm" p="xs">Valor da causa acima do teto: acordo exige aprovação do gestor.</Alert>
          )}
        </div>
        <Stack gap="xs" style={{ flex: "0 0 auto", minWidth: 200 }}>
          <MiniMetrica rotulo="Custo esperado da defesa" valor={brl(rec.custo_esperado_defesa)} />
          <MiniMetrica rotulo="Custo esperado do acordo" valor={brl(rec.custo_esperado_acordo)} />
          <MiniMetrica rotulo="Economia com acordo" valor={brl(rec.economia_esperada)} cor={rec.economia_esperada > 0 ? "verde.7" : "vermelho.6"} />
        </Stack>
      </Group>

      <Divider my="md" />
      <List spacing={6} size="sm" icon={<Box w={6} h={6} mt={7} bg="laranja.6" style={{ borderRadius: 999 }} />}>
        {rec.motivos.map((m, i) => <List.Item key={i}>{m}</List.Item>)}
      </List>
    </Card>
  );
}
