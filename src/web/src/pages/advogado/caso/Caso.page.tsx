import { Alert, Skeleton, Stack } from "@mantine/core";

import { CabecalhoCaso } from "./components/CabecalhoCaso";
import { CardAnalise } from "./components/CardAnalise";
import { CardDecisaoAtual } from "./components/CardDecisaoAtual";
import { CardDocumentos } from "./components/CardDocumentos";
import { CardRecomendacao } from "./components/CardRecomendacao";
import { FormDecisao } from "./components/FormDecisao";
import { useCaso } from "./hooks/useCaso";

export default function Caso() {
  const {
    pid, processo, recomendacao, registrada, decisaoAtual, mostrarForm, mostrarDecisaoAtual,
    abertos, abrirDocumento, inicio, aoRegistrarDecisao, pedirNovaDecisao, invalidar,
  } = useCaso();

  if (processo.isLoading) return <Stack gap="md"><Skeleton height={140} radius={12} /><Skeleton height={360} radius={12} /><Skeleton height={120} radius={12} /></Stack>;
  if (processo.error) return <Alert color="vermelho" variant="light">{(processo.error as Error).message}</Alert>;
  const p = processo.data!;

  return (
    <Stack gap="md" className="escalonado">
      <CabecalhoCaso p={p} />
      <CardRecomendacao p={p} rec={recomendacao.data} carregando={recomendacao.isLoading} erro={recomendacao.error as Error | null} />
      <CardAnalise p={p} />
      <CardDocumentos p={p} abertos={abertos} onAbrir={abrirDocumento} />
      {mostrarDecisaoAtual && decisaoAtual && (
        <CardDecisaoAtual d={decisaoAtual} registrada={registrada} p={p} onNova={pedirNovaDecisao} onResultado={invalidar} />
      )}
      {mostrarForm && recomendacao.data && (
        <FormDecisao pid={pid} rec={recomendacao.data} abertos={abertos} inicio={inicio} onOk={aoRegistrarDecisao} />
      )}
    </Stack>
  );
}
