import { Alert, Box, Card, Divider, Group, List, Paper, SimpleGrid, Skeleton, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";

import type { ProcessoDetalhe, Recomendacao } from "../../../../api/client";
import { OrigemBadge } from "../../../../components/Badges";
import { brl, ROTULO_TIPO } from "../../../../lib/format";
import { NOMES_SUBSIDIOS } from "../caso.const";
import { AnelProbabilidade } from "./AnelProbabilidade";
import { BandaOferta } from "./BandaOferta";
import { MiniMetrica } from "./MiniMetrica";

export function CardRecomendacao({ p, rec, carregando, erro }: {
  p: ProcessoDetalhe; rec?: Recomendacao; carregando: boolean; erro: Error | null;
}) {
  if (carregando) return <Skeleton height={420} radius={12} />;
  if (erro) return <Alert color="vermelho" variant="light" title="Sem recomendação">{erro.message}</Alert>;
  if (!rec) return null;
  const s = rec.scores_snapshot;
  const defesa = rec.tipo === "defesa";
  const instruir = rec.tipo === "instruir";
  // "instruir" é um acordo já dimensionado que espera os subsídios: tem oferta e banda como o acordo.
  const temOferta = rec.valor_sugerido != null;
  return (
    <Card p={{ base: "lg", sm: 32 }} bg="tinta.6" c="white" pos="relative"
      style={{ overflow: "hidden", borderColor: "rgba(255,255,255,.1)" }}>
      {/* Halo atrás do anel e um arco frio na base: só profundidade, sem borda que dispute com o medidor. */}
      <Box pos="absolute" w={360} h={360} right={-110} top={-160}
        style={{ borderRadius: 999, background: "radial-gradient(circle, rgba(255,174,53,.1), rgba(255,174,53,0) 68%)" }} />
      <Box pos="absolute" w={300} h={300} left={-140} bottom={-170}
        style={{ borderRadius: 999, border: "1px solid rgba(255,255,255,.07)" }} />

      <Stack gap="lg" pos="relative">
        <Group justify="space-between" align="flex-start" wrap="wrap" gap="xl">
          <Stack gap="sm" style={{ flex: "1 1 300px" }}>
            <Group gap={8}>
              <Box w={7} h={7} bg="laranja.5" style={{ borderRadius: 999 }} className="pulsar" />
              <Text size="xs" fw={600} tt="uppercase" lts=".1em" c="laranja.5">A política recomenda</Text>
            </Group>
            <div>
              <Title order={1} className="serif subir" fz={{ base: 46, sm: 62 }} lh={1} fw={600} lts="-.01em" c={defesa ? undefined : "laranja.4"}>
                {ROTULO_TIPO[rec.tipo] ?? rec.tipo}
              </Title>
              {temOferta && !instruir && (
                <Text className="serif numero" fz={{ base: 26, sm: 34 }} lh={1.1} mt={10}>{brl(rec.valor_sugerido)}</Text>
              )}
            </div>
            <Text size="sm" c="rgba(255,255,255,.6)" className="numero">
              Se perder, condenação estimada entre {brl(s.condenacao_p20)} e {brl(s.condenacao_p80)} (mediana {brl(s.condenacao_p50)})
            </Text>
          </Stack>
          <Stack gap={8} align="center" style={{ flex: "0 0 auto" }}>
            <AnelProbabilidade valor={s.p_exito_defesa} />
            <Group gap={6}>
              <Text size="xs" c="rgba(255,255,255,.55)" tt="uppercase" lts=".08em">Êxito na defesa</Text>
              <OrigemBadge origem={s.origem} rotulo="score stub" />
            </Group>
          </Stack>
        </Group>

        {instruir && (
          <Aviso>
            Solicitar ao banco: {rec.docs_a_solicitar.map((d) => NOMES_SUBSIDIOS[d] ?? d).join(", ")}.
            {temOferta && ` Se o banco não localizar, propor o acordo de ${brl(rec.valor_sugerido)}.`}
          </Aviso>
        )}
        {rec.exige_aprovacao_valor_causa && (
          <Aviso>Valor da causa acima do teto: acordo exige aprovação do gestor.</Aviso>
        )}

        {temOferta && rec.valor_min != null && rec.valor_max != null && rec.valor_sugerido != null && (
          <BandaOferta min={rec.valor_min} sugerido={rec.valor_sugerido} max={rec.valor_max} causa={p.valor_causa} />
        )}

        <SimpleGrid cols={{ base: 1, xs: 3 }} spacing="sm">
          <MiniMetrica rotulo="Custo esperado da defesa" valor={brl(rec.custo_esperado_defesa)} />
          <MiniMetrica rotulo="Custo esperado do acordo" valor={brl(rec.custo_esperado_acordo)} />
          <MiniMetrica rotulo="Economia com acordo" valor={brl(rec.economia_esperada)} cor={rec.economia_esperada > 0 ? "verde.4" : "vermelho.4"} />
        </SimpleGrid>

        <div>
          <Divider color="rgba(255,255,255,.13)" mb="md" />
          <List spacing={10} size="md" c="rgba(255,255,255,.8)"
            icon={<Box w={7} h={7} mt={9} bg="laranja.5" style={{ borderRadius: 999 }} />}>
            {rec.motivos.map((m, i) => <List.Item key={i}>{m}</List.Item>)}
          </List>
        </div>
      </Stack>
    </Card>
  );
}

/** Aviso dentro do cartão escuro: faixa âmbar translúcida no lugar do Alert claro do Mantine. */
function Aviso({ children }: { children: ReactNode }) {
  return (
    <Paper p="sm" radius={10} bg="rgba(255,174,53,.12)" style={{ border: "1px solid rgba(255,174,53,.28)" }}>
      <Group gap={10} align="flex-start" wrap="nowrap">
        <Box w={6} h={6} mt={7} bg="laranja.5" style={{ borderRadius: 999, flex: "0 0 auto" }} />
        <Text size="sm" c="rgba(255,255,255,.86)">{children}</Text>
      </Group>
    </Paper>
  );
}
