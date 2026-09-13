import { Paper, Skeleton, Table, Text } from "@mantine/core";
import { useNavigate } from "react-router";

import type { ProcessoResumo } from "../../../../api/client";
import { LARGURA_COLUNA as L } from "../casos.const";
import { CabecalhoColuna } from "./CabecalhoColuna";
import { LinhaCaso } from "./LinhaCaso";

export function TabelaCasos({ casos, gestor, temAutor, colunas, carregando }: {
  casos: ProcessoResumo[]; gestor: boolean; temAutor: boolean; colunas: number; carregando: boolean;
}) {
  const navigate = useNavigate();
  // Só as colunas visíveis entram na largura mínima; acima dela o navegador divide a sobra na proporção.
  const minima = L.processo + L.valor + L.subsidios + L.recomendacao + L.situacao
    + (temAutor ? L.autor : 0) + (gestor ? L.escritorio : 0);
  return (
    <Paper withBorder style={{ overflow: "hidden" }}>
      <Table.ScrollContainer minWidth={minima}>
        <Table verticalSpacing="sm" horizontalSpacing="md" highlightOnHover layout="fixed"
          styles={{ td: { verticalAlign: "middle" }, th: { verticalAlign: "middle" } }}>
          <Table.Thead>
            <Table.Tr>
              <CabecalhoColuna largura={L.processo}>Processo</CabecalhoColuna>
              {temAutor && <CabecalhoColuna largura={L.autor}>Autor</CabecalhoColuna>}
              <CabecalhoColuna largura={L.valor}>Valor da causa</CabecalhoColuna>
              <CabecalhoColuna largura={L.subsidios}>Subsídios</CabecalhoColuna>
              <CabecalhoColuna largura={L.recomendacao}>Recomendação</CabecalhoColuna>
              <CabecalhoColuna largura={L.situacao}>Situação</CabecalhoColuna>
              {gestor && <CabecalhoColuna largura={L.escritorio}>Escritório</CabecalhoColuna>}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody className={carregando ? undefined : "escalonado"}>
            {carregando && Array.from({ length: 8 }).map((_, i) => (
              <Table.Tr key={i}>
                <Table.Td colSpan={colunas}><Skeleton height={34} radius="sm" /></Table.Td>
              </Table.Tr>
            ))}
            {casos.map((p) => (
              <LinhaCaso key={p.id} p={p} gestor={gestor} temAutor={temAutor} onSelecionar={(id) => navigate(`/casos/${id}`)} />
            ))}
            {!carregando && casos.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={colunas}>
                  <Text className="serif" fw={400} c="dimmed" ta="center" py="xl" fz="lg">Nenhum processo encontrado.</Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Paper>
  );
}
