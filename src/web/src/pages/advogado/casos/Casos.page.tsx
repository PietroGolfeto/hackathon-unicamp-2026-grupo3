import { Alert, Group, SegmentedControl, Stack, Text, TextInput, Title } from "@mantine/core";

import { IcoBusca } from "../../../components/Icones";
import { num } from "../../../lib/format";
import { OPCOES_SITUACAO } from "./casos.const";
import type { Situacao } from "./casos.types";
import { TabelaCasos } from "./components/TabelaCasos";
import { useCasos } from "./hooks/useCasos";

export default function Casos() {
  const {
    busca, setBusca, situacao, setSituacao, usuario, gestor,
    processos, filtrados, pendentes, temAutor, colunas, isLoading, error,
  } = useCasos();

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end" wrap="wrap" gap="md">
        <div>
          <Title order={2}>Casos</Title>
          <Text c="dimmed" size="sm" mt={4}>
            {gestor ? "Todos os escritórios" : usuario?.escritorio_nome}
            {processos ? ` · ${num(processos.length)} processos · ${num(pendentes)} pendentes` : ""}
          </Text>
        </div>
        <Group gap="sm" wrap="wrap">
          <SegmentedControl size="sm" radius={8} value={situacao} onChange={(v) => setSituacao(v as Situacao)}
            data={OPCOES_SITUACAO} />
          <TextInput placeholder={temAutor ? "Buscar por número ou autor" : "Buscar por número"} value={busca}
            onChange={(e) => setBusca(e.currentTarget.value)} w={{ base: "100%", sm: 300 }} leftSection={<IcoBusca size={16} />} />
        </Group>
      </Group>

      {error && <Alert color="vermelho" variant="light">{error.message}</Alert>}

      <TabelaCasos casos={filtrados} gestor={!!gestor} temAutor={temAutor} colunas={colunas} carregando={isLoading} />
    </Stack>
  );
}
